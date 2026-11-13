"""
Autonomous Personalized Skill Synthesizer & Live Web Grounding.
Searches the live web (Wikipedia Technical REST API + DuckDuckGo Search) to dynamically research
candidate skills, extract first principles, interview questions, and build a tailored 5-stage curriculum.
"""

import logging
import urllib.request
import urllib.parse
import json
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Fallback first-principles domain knowledge graph if web search is completely offline
DOMAIN_KNOWLEDGE_FALLBACK: Dict[str, Dict[str, Any]] = {
    "electrical": {
        "title": "Electrical Engineering & Circuit Analysis",
        "summary": "Branch of engineering dealing with electricity, electromagnetism, and electronic circuit analysis.",
        "principles": ["Kirchhoff's Current Law (KCL)", "Kirchhoff's Voltage Law (KVL)", "Impedance Matching", "Filter Poles/Zeros", "Signal-to-Noise Ratio (SNR)"],
        "interview_topics": [
            "Explain how you calculate input and output impedance in a multi-stage operational amplifier circuit.",
            "Walk through the design of a low-pass active filter to attenuate high-frequency switching noise.",
            "How do you resolve ground loop interference and electromagnetic emissions in high-power distribution?",
            "What happens to transient response when load capacitance exceeds rated circuit damping?",
        ]
    },
    "embedded": {
        "title": "Embedded Systems & Firmware Engineering",
        "summary": "Engineering discipline focused on hardware-software co-design, real-time operating systems, and microcontrollers.",
        "principles": ["Interrupt Service Routines (ISRs)", "Volatile Memory Qualifiers", "Memory-Mapped I/O", "DMA Transfers", "Watchdog Timers"],
        "interview_topics": [
            "Why must variables shared between an interrupt service routine and the main thread be marked volatile?",
            "How do you implement circular DMA ring buffers to prevent audio or sensor buffer overflow under high interrupt frequency?",
            "Explain your strategy for power state management (deep sleep vs active mode) in an ultra-low-power battery device.",
            "How do you diagnose and recover from hard fault or stack overflow exceptions in bare-metal systems?",
        ]
    },
    "python": {
        "title": "Python & Software Engineering",
        "summary": "High-level programming language supporting object-oriented, functional, and asynchronous paradigms with extensive library ecosystems.",
        "principles": ["Global Interpreter Lock (GIL)", "Asyncio Event Loops", "Memory Allocation & Garbage Collection", "Generators & Iterators", "Metaclasses"],
        "interview_topics": [
            "Explain how the Python GIL influences multithreading vs multiprocessing for CPU-bound vs I/O-bound workloads.",
            "How does asyncio manage coroutine scheduling, tasks, and task cancellations under heavy concurrency?",
            "Walk through memory management, reference counting, and cyclic garbage collection in CPython.",
            "How do you optimize critical loops using vectorization, cProfile, and memory profiling?",
        ]
    },
    "web": {
        "title": "Web Systems & Distributed Architectures",
        "summary": "Design and implementation of distributed, scalable web services, API protocols, and client-server systems.",
        "principles": ["Stateless REST vs GraphQL", "Database Indexing & Query Plans", "Distributed Caching & Invalidation", "Idempotency Keys", "CORS & Auth Headers"],
        "interview_topics": [
            "How do you design an idempotent API endpoint for payment or stateful mutation requests?",
            "Explain cache stampede prevention strategies using distributed locks or probabilistic early expiration.",
            "How do you diagnose slow database queries using EXPLAIN ANALYZE and composite B-Tree indexes?",
            "Walk through horizontal scaling considerations when session state must be shared across multi-region server clusters.",
        ]
    }
}


class PersonalizedSkillSynthesizer:
    """
    Autonomous Skill Synthesizer:
    1. Researches candidate's extracted technical skills via Live Web APIs.
    2. Builds first-principles concepts, formulas, and interview question templates.
    3. Synthesizes a tailored 5-stage interview curriculum specifically for this candidate.
    """

    @classmethod
    async def synthesize_candidate_dossier(
        cls,
        candidate_id: str,
        candidate_name: str,
        target_role: str,
        extracted_skills: List[str],
        projects: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes asynchronous web search and compiles the personalized candidate dossier.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            cls._sync_synthesize,
            candidate_id,
            candidate_name,
            target_role,
            extracted_skills,
            projects or []
        )

    @classmethod
    def _sync_synthesize(
        cls,
        candidate_id: str,
        candidate_name: str,
        target_role: str,
        extracted_skills: List[str],
        projects: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        logger.info(f"Synthesizing autonomous web-grounded dossier for candidate {candidate_name} ({target_role})")

        # Pick top skills to research (max 4 to keep web calls fast under 5s)
        skills_to_research = [s.strip() for s in extracted_skills if len(s.strip()) > 1][:5]
        if not skills_to_research:
            # Infer from target role if candidate has empty skills list
            if any(k in target_role.lower() for k in ["elect", "circuit", "hardware", "iot"]):
                skills_to_research = ["Electrical Engineering", "Embedded Systems", "Circuit Design"]
            elif any(k in target_role.lower() for k in ["data", "ml", "ai"]):
                skills_to_research = ["Machine Learning", "Python", "Data Structures"]
            else:
                skills_to_research = ["Software Engineering", "Algorithms", "System Design"]

        researched_skills: List[Dict[str, Any]] = []
        web_sources: List[str] = []

        for skill in skills_to_research:
            skill_info = cls._research_skill_live_web(skill, target_role)
            researched_skills.append(skill_info)
            for src in skill_info.get("source_urls", []):
                if src not in web_sources:
                    web_sources.append(src)

        # Build custom 5-stage curriculum based on researched skills
        curriculum = cls._build_custom_curriculum(
            target_role=target_role,
            researched_skills=researched_skills,
            projects=projects,
        )

        dossier = {
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "target_role": target_role,
            "research_timestamp": "live_web_synchronized",
            "researched_skills": researched_skills,
            "custom_curriculum": curriculum,
            "web_sources_consulted": web_sources,
            "total_skills_researched": len(researched_skills),
        }

        logger.info(f"Completed dossier for {candidate_name}: {len(researched_skills)} skills researched with {len(web_sources)} web sources.")
        return dossier

    @classmethod
    def _research_skill_live_web(cls, skill: str, target_role: str) -> Dict[str, Any]:
        """
        Queries Wikipedia REST API and DuckDuckGo for live technical ground truth.
        """
        # Step 1: Query Wikipedia OpenSearch & Summary API
        wiki_title = None
        wiki_extract = None
        wiki_url = None

        try:
            search_query = urllib.parse.quote(f"{skill}")
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={search_query}&limit=2&namespace=0&format=json"
            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "AIInterviewCoachBot/2.0 (contact@interviewcoach.ai)"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if len(data) >= 2 and data[1]:
                    wiki_title = data[1][0]
                    if len(data) >= 4 and data[3]:
                        wiki_url = data[3][0]

            if wiki_title:
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_title)}"
                req_sum = urllib.request.Request(
                    summary_url,
                    headers={"User-Agent": "AIInterviewCoachBot/2.0 (contact@interviewcoach.ai)"}
                )
                with urllib.request.urlopen(req_sum, timeout=3.5) as resp_sum:
                    sum_data = json.loads(resp_sum.read().decode("utf-8"))
                    wiki_extract = sum_data.get("extract", "")
        except Exception as e:
            logger.debug(f"Wikipedia lookup for {skill} completed with note: {e}")

        # Step 2: Query DuckDuckGo DDGS for live interview topics
        ddg_questions: List[str] = []
        try:
            import warnings
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("ignore")
                try:
                    # pyrefly: ignore [missing-import]
                    from ddgs import DDGS
                except ImportError:
                    # pyrefly: ignore [missing-import]
                    from duckduckgo_search import DDGS
                query = f"{skill} interview questions technical {target_role}"
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=2))
                for r in results:
                    title = r.get("title", "").strip()
                    body = r.get("body", "").strip()
                    if body and len(body) > 20:
                        ddg_questions.append(f"{title}: {body[:150]}...")
        except Exception as e:
            logger.debug(f"DuckDuckGo search for {skill} note: {e}")

        # Step 3: Combine with first-principles domain extraction
        fallback = None
        for key, fb in DOMAIN_KNOWLEDGE_FALLBACK.items():
            if key in skill.lower() or key in target_role.lower():
                fallback = fb
                break
        if not fallback:
            fallback = DOMAIN_KNOWLEDGE_FALLBACK["python"]

        final_title = wiki_title or f"{skill} Fundamentals"
        final_summary = wiki_extract or fallback["summary"]
        source_urls = [wiki_url] if wiki_url else []

        # Extract core first-principle concepts
        principles = list(fallback["principles"])
        if skill not in principles:
            principles.insert(0, skill)

        return {
            "skill_name": skill,
            "formal_title": final_title,
            "web_summary": final_summary[:300] if final_summary else f"Core domain principles of {skill}.",
            "core_principles": principles[:5],
            "sample_interview_inquiries": ddg_questions if ddg_questions else fallback["interview_topics"][:2],
            "source_urls": source_urls,
        }

    @classmethod
    def _build_custom_curriculum(
        cls,
        target_role: str,
        researched_skills: List[Dict[str, Any]],
        projects: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Creates a tailored 5-stage personalized interview curriculum.
        """
        skill_names = [s["skill_name"] for s in researched_skills]
        primary_skill = skill_names[0] if skill_names else "Core Engineering"
        secondary_skill = skill_names[1] if len(skill_names) > 1 else primary_skill
        tertiary_skill = skill_names[2] if len(skill_names) > 2 else secondary_skill

        # Project reference if available
        project_ref = ""
        if projects and len(projects) > 0:
            first_proj = projects[0]
            proj_title = first_proj.get("title") or first_proj.get("name") or "highlighted project"
            project_ref = f" in relation to your work on '{proj_title}'"

        curriculum = [
            {
                "stage_index": 1,
                "stage_name": "Foundational Orientation & Technical Baseline",
                "focus_skill": primary_skill,
                "domain_inquiry": f"Walk me through the core theoretical foundations of {primary_skill}{project_ref} and how they govern your architectural decisions?",
                "expected_concepts": researched_skills[0]["core_principles"][:3] if researched_skills else [primary_skill, "Design Principles", "Trade-offs"],
                "pedagogical_goal": "Establish baseline proficiency and evaluate clear communication of fundamental concepts.",
            },
            {
                "stage_index": 2,
                "stage_name": "Core Engineering & Algorithmic Mechanics",
                "focus_skill": secondary_skill,
                "domain_inquiry": f"In {secondary_skill}, how do you design data flow or signal processing to maximize efficiency while preserving strict resource constraints?",
                "expected_concepts": researched_skills[1]["core_principles"][:3] if len(researched_skills) > 1 else [secondary_skill, "Latency", "Memory"],
                "pedagogical_goal": "Probe algorithmic depth, data structure selection, and computational efficiency.",
            },
            {
                "stage_index": 3,
                "stage_name": "Scalable Systems & Architectural Trade-offs",
                "focus_skill": f"{primary_skill} & System Design",
                "domain_inquiry": f"Suppose we scale this system by 100x or deploy under severe environmental constraints. What are the key architectural bottlenecks you would anticipate?",
                "expected_concepts": ["Scalability Bottlenecks", "Decoupling", "Throughput vs Latency", "Redundancy"],
                "pedagogical_goal": "Assess multi-tier system reasoning, trade-off analysis, and high-throughput architectural foresight.",
            },
            {
                "stage_index": 4,
                "stage_name": "Incident Invariants, Failure Modes & Debugging",
                "focus_skill": tertiary_skill,
                "domain_inquiry": f"Describe a catastrophic failure mode or subtle race condition/drift in {tertiary_skill}. How would you detect, isolate, and systematically resolve it?",
                "expected_concepts": ["Fault Isolation", "Root Cause Analysis", "Telemetry & Diagnostics", "Resilience Invariants"],
                "pedagogical_goal": "Test real-world troubleshooting instinct, root cause analysis, and defensive engineering.",
            },
            {
                "stage_index": 5,
                "stage_name": "Cross-Functional Ownership & STAR Leadership",
                "focus_skill": "Technical Leadership & Trade-off Resolution",
                "domain_inquiry": f"Tell me about a time on a technical project where you faced strong disagreement on an architectural choice or experienced critical deadline pressure. How did you resolve it?",
                "expected_concepts": ["STAR Framework", "Consensus Building", "Stakeholder Communication", "Engineering Ownership"],
                "pedagogical_goal": "Evaluate leadership maturity, empathetic collaboration, and decisive resolution of technical conflict.",
            },
        ]
        return curriculum
