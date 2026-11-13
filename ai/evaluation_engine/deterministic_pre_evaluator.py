"""
Deterministic Pre-Analysis Engine for Explainable Evaluation.
Extracts objective signals (concept presence, omissions, evidence anchors, structure, response time)
BEFORE the LLM evaluation call to reduce LLM decoding workload and anchor scoring.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

REFUSAL_PHRASES = [
    "i don't know", "i dont know", "no idea", "not sure", "idk",
    "cant answer", "can't answer", "dont know", "don't know",
    "i do not know", "have no idea", "not familiar", "unfamiliar with this",
    "no clue", "never heard of", "cannot answer", "decline to answer",
    "nothing to say", "nothing to add", "pass on this", "skip this",
    "pass this question", "prefer to skip",
]

CONCEPT_STOPWORDS = {
    "and", "or", "the", "in", "of", "for", "with", "a", "an", "to", "on", "at", "by",
    "vs", "versus", "is", "are", "strategies", "mechanisms", "patterns", "overview",
    "system", "systems", "approach", "handling", "model", "models", "level", "levels",
}

# Domain semantic equivalents and stems to prevent false omissions on valid phrasing
DOMAIN_EQUIVALENTS: Dict[str, List[str]] = {
    "ram": ["memory", "footprint", "overhead", "sram", "dram", "consumption", "bytes", "gb", "mb"],
    "footprint": ["overhead", "memory", "ram", "consumption", "size", "bytes"],
    "hnsw": ["hierarchical navigable", "graph traversal", "proximity graph", "proximity graphs", "skip connections", "skip layers", "skip layer"],
    "ivf": ["inverted file", "inverted files", "inverted list", "inverted lists", "voronoi", "nlist", "nprobe", "centroids", "coarse quantizer"],
    "quantization": ["quantize", "quantized", "pq", "sq8", "scalar quantization", "product quantization", "codebook", "codebooks"],
    "efsearch": ["ef_search", "efconstruction", "beam width", "search width", "graph search"],
    "recall": ["recall@k", "recall@10", "accuracy", "retrieval quality", "precision"],
    "latency": ["p99", "p95", "p50", "sla", "ms", "throughput", "response time"],
    "coap": ["udp", "confirmable", "con", "non", "restful iot"],
    "mqtt": ["qos", "puback", "pubrec", "broker", "keepalive", "pingreq"],
    "buffer": ["ring buffer", "circular buffer", "queue", "buffering", "backpressure"],
    "backpressure": ["rate limiting", "throttling", "load shedding", "flow control"],
    "flash": ["wear leveling", "spi flash", "storage", "non-volatile", "eeprom"],
    "battery": ["power consumption", "low power", "sleep", "deep sleep", "esleep", "current drain"],
    "bm25": ["sparse", "lexical", "keyword matching", "term frequency", "inverted index", "tfidf"],
    "dense": ["embedding", "embeddings", "vector", "bi-encoder", "semantic similarity"],
    "reranking": ["re-ranking", "reranker", "cross-encoder", "cross-attention", "rank fusion"],
    "hybrid": ["dense + bm25", "hybrid retrieval", "sparse + dense", "rrf", "reciprocal rank fusion"],
    "chunking": ["chunk boundaries", "chunk size", "semantic chunking", "overlap"],
    "stampede": ["thundering herd", "cache stampede", "herd", "stampedes", "expiration spike"],
    "mutex": ["lock", "locks", "distributed lock", "single-flight", "request coalescing", "stale-while-revalidate", "mutexes", "mutex lock"],
    "jitter": ["random ttl", "ttl jitter", "randomized expiration", "probabilistic early expiration", "xfetch", "staggered ttl"],
    "coalescing": ["single-flight", "request coalescing", "mutex", "lock", "deduplication"],
    "pagedattention": ["page attention", "virtual memory", "kv block", "block table", "non-contiguous memory", "paged attention"],
    "batching": ["continuous batching", "iteration-level batching", "dynamic batching", "in-flight batching"],
}


@dataclass
class DeterministicSignals:
    word_count: int
    char_count: int
    response_time_seconds: float
    matched_concepts: List[str]
    missing_concepts: List[str]
    coverage_ratio: float
    evidence_matches: List[Dict[str, str]]
    has_quantitative_metrics: bool
    has_tradeoff_analysis: bool
    has_code_or_syntax: bool
    is_refusal: bool
    structural_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "word_count": self.word_count,
            "char_count": self.char_count,
            "response_time_seconds": self.response_time_seconds,
            "matched_concepts": self.matched_concepts,
            "missing_concepts": self.missing_concepts,
            "coverage_ratio": self.coverage_ratio,
            "evidence_matches": self.evidence_matches,
            "has_quantitative_metrics": self.has_quantitative_metrics,
            "has_tradeoff_analysis": self.has_tradeoff_analysis,
            "has_code_or_syntax": self.has_code_or_syntax,
            "is_refusal": self.is_refusal,
            "structural_summary": self.structural_summary,
        }


class DeterministicPreEvaluator:
    """
    Extracts deterministic signals from candidate answers before LLM invocation.
    Provides verified factual context so the LLM does not need to rediscover it.
    """

    @staticmethod
    def analyze(
        candidate_answer: str,
        expected_concepts: List[str],
        topic: str = "",
        response_time_seconds: float = 0.0,
    ) -> DeterministicSignals:
        clean_ans = candidate_answer.strip()
        words = clean_ans.split()
        ans_lower = clean_ans.lower()
        word_count = len(words)
        char_count = len(clean_ans)

        # 1. Refusal & brevity detection:
        # A response is ONLY classified as a refusal if:
        # - empty or zero alphanumeric characters
        # - extremely short (<= 2 words) without technical domain terms
        # - short (<= 12 words) and contains an explicit refusal expression
        # An answer with substantive technical content (> 12 words) is NEVER a refusal.
        is_refusal = False
        if not clean_ans or word_count == 0:
            is_refusal = True
        elif word_count <= 2 and not any(w in ans_lower for w in ["yes", "true", "false", "o(1)", "o(n)", "acid", "raft", "hnsw", "mqtt", "coap", "bm25", "diskann"]):
            is_refusal = True
        elif word_count < 5 and not any(c.isalnum() for c in clean_ans):
            is_refusal = True
        elif word_count <= 12:
            clean_token = ans_lower.strip(" .!?,;:")
            if clean_token in ["skip", "pass", "nothing", "idk", "none", "no"]:
                is_refusal = True
            elif any(re.search(r"\b" + re.escape(p) + r"\b", ans_lower) for p in REFUSAL_PHRASES):
                is_refusal = True

        # 2. Concept matching & omission tracking (Grounded semantic & synonym matching)
        matched_concepts: List[str] = []
        for concept in expected_concepts:
            c_lower = concept.lower()
            clean_c = re.sub(r"[^\w\s]", " ", c_lower)
            if c_lower in ans_lower or clean_c in ans_lower:
                matched_concepts.append(concept)
                continue

            # Significant tokens excluding common generic stopwords
            c_tokens = [t for t in clean_c.split() if len(t) >= 2 and t not in CONCEPT_STOPWORDS]
            if not c_tokens:
                continue

            # Check if each token or any of its domain synonyms/stems is present in answer
            matched_count = 0
            for t in c_tokens:
                t_matched = (t in ans_lower)
                if not t_matched:
                    # Check synonym equivalents
                    synonyms = DOMAIN_EQUIVALENTS.get(t, [])
                    for s in synonyms:
                        if s in ans_lower:
                            t_matched = True
                            break
                if not t_matched and len(t) >= 5:
                    # Prefix stem match (e.g. quantiz -> quantization)
                    stem = t[:len(t) - 2]
                    if stem in ans_lower:
                        t_matched = True
                if t_matched:
                    matched_count += 1

            if len(c_tokens) == 1:
                if matched_count == 1:
                    matched_concepts.append(concept)
            elif len(c_tokens) == 2:
                if matched_count >= 1:
                    matched_concepts.append(concept)
            elif len(c_tokens) >= 3:
                if (matched_count / len(c_tokens)) >= 0.5:
                    matched_concepts.append(concept)

        missing_concepts = [c for c in expected_concepts if c not in matched_concepts]
        if expected_concepts:
            coverage_ratio = len(matched_concepts) / len(expected_concepts)
        else:
            topic_clean = re.sub(r"[^\w\s]", " ", topic.lower())
            topic_words = [w for w in topic_clean.split() if len(w) > 3 and w not in CONCEPT_STOPWORDS]
            coverage_ratio = 1.0 if (topic_words and any(tw in ans_lower for tw in topic_words)) else 0.0

        # Substantive answer safeguard: if candidate provided a deep answer (> 40 words) with
        # technical terminology or trade-offs, ensure coverage reflects substantive engagement
        if coverage_ratio == 0.0 and word_count >= 40:
            technical_domain_words = [
                "latency", "throughput", "memory", "ram", "cpu", "gpu", "index", "graph",
                "cache", "queue", "partition", "protocol", "algorithm", "sla", "p99", "vector",
                "database", "cluster", "node", "shard", "overhead", "tradeoff", "complexity"
            ]
            tech_hits = sum(1 for tw in technical_domain_words if tw in ans_lower)
            if tech_hits >= 2:
                coverage_ratio = min(0.65, round(0.20 + (tech_hits * 0.08), 2))

        # 3. Structural feature detection
        has_quantitative = bool(
            re.search(r"\b\d+(\.\d+)?(ms|s|%|k|m|gb|mb|tb|hz|qps|tps|rps)?\b", ans_lower)
            or re.search(r"O\([^\)]+\)", clean_ans)
        )
        tradeoff_markers = [
            "tradeoff", "trade-off", "versus", "vs", "drawback", "downside",
            "however", "on the other hand", "whereas", "alternative", "bottleneck",
            "compromise", "benefit", "advantage",
        ]
        has_tradeoff = any(tm in ans_lower for tm in tradeoff_markers)

        code_markers = ["->", "=>", "def ", "class ", "function", "select ", "from ", "where ", "{", "}", ";", "=="]
        has_code = any(cm in ans_lower for cm in code_markers)

        structural_parts = []
        if has_quantitative:
            structural_parts.append("Quantitative metrics present")
        if has_tradeoff:
            structural_parts.append("Trade-off analysis present")
        if has_code:
            structural_parts.append("Code/syntax markers present")
        structural_summary = "; ".join(structural_parts) if structural_parts else "Standard prose"

        # 4. Verbatim evidence extraction
        sentences = [s.strip() for s in re.split(r"[.!?\n]", clean_ans) if len(s.strip()) > 15]
        evidence_matches: List[Dict[str, str]] = []

        # Find sentences matching concepts
        for concept in matched_concepts:
            c_tokens = [t.lower() for t in re.split(r"[\s/_,-]+", concept) if len(t) > 2]
            for s in sentences:
                if any(t in s.lower() for t in c_tokens):
                    basis_snippet = f'"{s[:150]}"'
                    if not any(e["basis"] == basis_snippet for e in evidence_matches):
                        evidence_matches.append({
                            "claim": f"Addressed {concept}",
                            "basis": basis_snippet,
                        })
                    break
            if len(evidence_matches) >= 2:
                break

        # Fallback evidence if no specific concept sentence found
        if not evidence_matches:
            if sentences:
                evidence_matches.append({
                    "claim": f"Response to {topic or 'question'}",
                    "basis": f'"{sentences[0][:150]}"',
                })
            elif clean_ans:
                evidence_matches.append({
                    "claim": "Candidate submission",
                    "basis": f'"{clean_ans[:120]}"',
                })

        return DeterministicSignals(
            word_count=word_count,
            char_count=char_count,
            response_time_seconds=round(response_time_seconds, 1),
            matched_concepts=matched_concepts,
            missing_concepts=missing_concepts,
            coverage_ratio=round(coverage_ratio, 2),
            evidence_matches=evidence_matches,
            has_quantitative_metrics=has_quantitative,
            has_tradeoff_analysis=has_tradeoff,
            has_code_or_syntax=has_code,
            is_refusal=is_refusal,
            structural_summary=structural_summary,
        )
