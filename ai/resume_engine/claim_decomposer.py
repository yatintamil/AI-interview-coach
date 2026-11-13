"""
Atomic Claim Decomposition Service.
Deconstructs unstructured resume text and profile entities into verifiable atomic claims.
Foundation for the Candidate Evidence Graph (CEG) and Adversarial Probing.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from backend.domain.ai.interfaces import LLMProvider, LLMRequest
from backend.infrastructure.ai.factory import get_llm_provider

logger = logging.getLogger(__name__)

CLAIM_DECOMPOSITION_PROMPT = """
You are an expert technical interviewer and verification specialist.
Your task is to decompose a candidate's resume text and profile entities into ATOMIC, FALSIFIABLE TECHNICAL CLAIMS.

Each claim must represent a specific skill, tool, architecture, or project capability that can be verified during a rigorous technical interview.

Return a JSON object with a "claims" array conforming to this exact schema:
{
  "claims": [
    {
      "skill_name": "PostgreSQL",
      "claim_text": "Engineered relational schema with composite indexes and sub-second query latency.",
      "complexity": "ADVANCED"
    },
    {
      "skill_name": "Docker",
      "claim_text": "Built containerized development and deployment workflows using multi-stage Dockerfiles.",
      "complexity": "INTERMEDIATE"
    }
  ]
}

Complexity choices: "FOUNDATIONAL", "INTERMEDIATE", "ADVANCED", "SYSTEM_LEVEL".
Do not invent claims that are not asserted or implied in the candidate's background. Generate between 4 and 10 atomic claims.
"""


class ResumeClaimDecomposer:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()

    async def decompose_claims(self, resume_text: str, profile_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Decomposes resume content into structured atomic claims.
        """
        user_content = f"Resume Summary:\n{resume_text[:2500]}"
        if profile_dict:
            skills = ", ".join(s.get("name", "") for s in profile_dict.get("skills", []))
            tech = ", ".join(profile_dict.get("technologies", []))
            user_content += f"\n\nExtracted Skills: {skills}\nTechnologies: {tech}"

        request = LLMRequest(
            system_prompt=CLAIM_DECOMPOSITION_PROMPT,
            user_prompt=user_content,
            temperature=0.2,
            max_tokens=450,
            response_json=True,
            metadata={"task_type": "candidate_evidence"},
        )

        try:
            response = await self.provider.generate(request)
            if response.raw_json and isinstance(response.raw_json, list):
                return self._sanitize_claims(response.raw_json, resume_text=resume_text)
            if response.raw_json and isinstance(response.raw_json, dict) and "claims" in response.raw_json:
                return self._sanitize_claims(response.raw_json["claims"], resume_text=resume_text)

            if response.content:
                cleaned = re.sub(r"^```json\s*", "", response.content.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return self._sanitize_claims(parsed, resume_text=resume_text)
                if isinstance(parsed, dict) and "claims" in parsed:
                    return self._sanitize_claims(parsed["claims"], resume_text=resume_text)
        except Exception as e:
            logger.warning(f"LLM claim decomposition encountered exception: {e}. Using rule-based synthesizer.")

        return self._rule_based_decomposition(resume_text, profile_dict)

    def _extract_supporting_quotes(self, skill_name: str, resume_text: str) -> List[str]:
        if not skill_name or not resume_text:
            return []
        quotes: List[str] = []
        pattern = re.compile(r"\b" + re.escape(skill_name) + r"\b", re.IGNORECASE)
        # Search lines and bullet points
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        for line in lines:
            # Skip pure headers or skill lists
            if len(line) < 15 or len(line) > 220:
                continue
            if pattern.search(line):
                # Clean bullet markers
                cleaned = re.sub(r"^[\*\-\•\·\d\.\)\s]+", "", line).strip()
                if cleaned and cleaned not in quotes:
                    quotes.append(cleaned)
                    if len(quotes) >= 2:
                        break
        return quotes

    def _sanitize_claims(self, raw_claims: List[Dict[str, Any]], resume_text: str = "") -> List[Dict[str, Any]]:
        valid = []
        for item in raw_claims:
            if not isinstance(item, dict):
                continue
            skill = str(item.get("skill_name", "")).strip()
            text = str(item.get("claim_text", "")).strip()
            if not skill or not text:
                continue

            # Eliminate any literal "None proficiency" or "None" placeholders
            text = re.sub(r"\bNone\s+proficiency\b", "applied engineering proficiency", text, flags=re.IGNORECASE)
            text = re.sub(r"\bAsserts\s+None\b", "Asserts practical", text, flags=re.IGNORECASE)

            complexity = str(item.get("complexity", "INTERMEDIATE")).upper()
            if complexity not in ["FOUNDATIONAL", "INTERMEDIATE", "ADVANCED", "SYSTEM_LEVEL"]:
                complexity = "INTERMEDIATE"

            quotes = item.get("verified_quotes", [])
            if not quotes and resume_text:
                quotes = self._extract_supporting_quotes(skill, resume_text)

            valid.append({
                "skill_name": skill,
                "claim_text": text,
                "complexity": complexity,
                "verification_status": "UNVERIFIED",
                "confidence_score": 0.5,
                "verified_quotes": quotes,
                "probe_count": 0,
            })
        return valid

    def _rule_based_decomposition(self, resume_text: str, profile_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        claims = []
        if profile_dict and "skills" in profile_dict:
            for idx, s in enumerate(profile_dict["skills"][:10]):
                name = str(s.get("name", "")).strip()
                if not name:
                    continue

                raw_prof = s.get("proficiency")
                prof_str = str(raw_prof).strip().lower() if raw_prof is not None else ""
                if "." in prof_str:
                    prof_str = prof_str.split(".")[-1]
                if prof_str in ("none", "null", ""):
                    prof_str = None

                quotes = self._extract_supporting_quotes(name, resume_text)
                if prof_str:
                    claim_text = f"Asserts demonstrated {prof_str} proficiency in {name} with applied technical experience."
                elif quotes:
                    claim_text = f"Cites applied engineering experience in {name} based on resume project evidence."
                else:
                    claim_text = f"Cites technical competency and applied background in {name}."

                claims.append({
                    "skill_name": name,
                    "claim_text": claim_text,
                    "complexity": "ADVANCED" if idx > 4 else "INTERMEDIATE",
                    "verification_status": "UNVERIFIED",
                    "confidence_score": 0.5,
                    "verified_quotes": quotes,
                    "probe_count": 0,
                })

        # Also incorporate project achievements if skills are sparse
        if profile_dict and "projects" in profile_dict and len(claims) < 4:
            for proj in profile_dict["projects"][:3]:
                title = proj.get("title", "Project")
                techs = proj.get("technologies_used", [])
                tech_str = ", ".join(techs) if techs else "software engineering systems"
                desc = proj.get("description", "")
                quotes = [desc[:160].strip()] if desc else []
                claims.append({
                    "skill_name": techs[0] if techs else title,
                    "claim_text": f"Engineered '{title}' utilizing {tech_str}.",
                    "complexity": "INTERMEDIATE",
                    "verification_status": "UNVERIFIED",
                    "confidence_score": 0.5,
                    "verified_quotes": quotes,
                    "probe_count": 0,
                })

        if not claims:
            claims.append({
                "skill_name": "Software Engineering Fundamentals",
                "claim_text": "Asserts foundational software engineering competency and applied system problem-solving.",
                "complexity": "FOUNDATIONAL",
                "verification_status": "UNVERIFIED",
                "confidence_score": 0.5,
                "verified_quotes": [],
                "probe_count": 0,
            })

        return claims
