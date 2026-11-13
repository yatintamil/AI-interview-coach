"""
LLM Candidate Profile Extractor implementation using AI Provider Abstraction.
Follows clean architecture (prompt isolation, structured JSON output, fallback handling).
"""

import asyncio
import json
import logging
import re
from typing import Optional, Dict, Any

from ai.config import ai_settings
from ai.prompts.resume.extraction_v1 import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT_TEMPLATE,
)
from ai.resume_engine.extractors.base import BaseExtractor
from backend.domain.ai.interfaces import LLMProvider, LLMRequest
from backend.infrastructure.ai.factory import get_llm_provider
from backend.schemas.candidate_profile import CandidateProfile

logger = logging.getLogger(__name__)


class LLMExtractor(BaseExtractor):
    """
    LLM-powered entity extractor using the decoupled LLMProvider protocol.
    """

    def __init__(self, provider: Optional[LLMProvider] = None, fallback_to_rules: bool = True):
        self.provider = provider or get_llm_provider(task="major")
        self.fallback_to_rules = fallback_to_rules

    def extract(self, resume_text: str) -> CandidateProfile:
        """
        Extract structured candidate profile using the configured LLM provider.
        Synchronous wrapper that safely executes the async generation.
        """
        if not resume_text or not resume_text.strip():
            return CandidateProfile(full_name="Unknown Candidate")

        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(resume_text=resume_text)
        request = LLMRequest(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=ai_settings.extraction_temperature,
            max_tokens=ai_settings.max_tokens,
            response_json=True,
            metadata={"task_type": "resume_intelligence"},
        )

        llm_profile: Optional[CandidateProfile] = None

        try:
            # Handle event loop if already running or create new loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Running inside existing event loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    response = pool.submit(asyncio.run, self.provider.generate(request)).result()
            else:
                response = asyncio.run(self.provider.generate(request))

            if response and response.raw_json:
                llm_profile = self._parse_json_to_profile(response.raw_json)
            elif response and response.content:
                cleaned = re.sub(r"^```json\s*", "", response.content.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                data = json.loads(cleaned)
                llm_profile = self._parse_json_to_profile(data)
        except Exception as e:
            logger.warning(f"LLM Provider extraction failed ({e}). Checking fallback...")

        # If LLM succeeded, also cross-check and enrich with RuleExtractor to ensure zero lost entities
        if llm_profile:
            try:
                from ai.resume_engine.extractors.rule_extractor import RuleExtractor
                rule_profile = RuleExtractor().extract(resume_text)
                return self._enrich_profile(llm_profile, rule_profile, resume_text=resume_text)
            except Exception as e:
                logger.debug(f"Enrichment note: {e}")
                return llm_profile

        # Fallback to Rule-based Extractor
        if self.fallback_to_rules:
            logger.info("Falling back to RuleExtractor for candidate profile generation")
            from ai.resume_engine.extractors.rule_extractor import RuleExtractor
            return RuleExtractor().extract(resume_text)

        return CandidateProfile(full_name="Candidate (Extraction Failed)")

    def _enrich_profile(self, primary: CandidateProfile, secondary: CandidateProfile, resume_text: str = "") -> CandidateProfile:
        """
        Enriches primary LLM profile only with strictly grounded evidence from secondary extractor.
        Prevents injecting duplicate or ungrounded entities.
        """
        lower_text = resume_text.lower() if resume_text else ""

        # Only fill missing contact info if found in resume text
        if not primary.location and secondary.location and (not lower_text or secondary.location.lower() in lower_text):
            primary.location = secondary.location
        if not primary.phone and secondary.phone and (not lower_text or secondary.phone.replace(" ", "") in lower_text.replace(" ", "")):
            primary.phone = secondary.phone
        if not primary.email and secondary.email and (not lower_text or secondary.email.lower() in lower_text):
            primary.email = secondary.email
        if not primary.summary and secondary.summary:
            primary.summary = secondary.summary

        # Only fallback-merge education if LLM found zero education records
        if not primary.education and secondary.education:
            primary.education = secondary.education

        # Only fallback-merge projects if LLM found zero projects
        if not primary.projects and secondary.projects:
            # Filter projects to only those with title mentioned in text
            if lower_text:
                primary.projects = [p for p in secondary.projects if p.title.lower() in lower_text]
            else:
                primary.projects = secondary.projects

        # Merge domains & soft skills safely
        if secondary.domains:
            primary.domains = sorted(list(set(primary.domains + secondary.domains)))
        if secondary.soft_skills:
            primary.soft_skills = sorted(list(set(primary.soft_skills + secondary.soft_skills)))

        # Merge skills ONLY if verified to exist in resume text
        existing_skills = {s.name.lower().strip() for s in primary.skills}
        for s in secondary.skills:
            s_name = s.name.strip()
            if s_name.lower() not in existing_skills:
                if not lower_text or s_name.lower() in lower_text:
                    primary.skills.append(s)
                    existing_skills.add(s_name.lower())

        # Sync technologies
        if not primary.technologies:
            primary.technologies = [s.name for s in primary.skills]

        return primary

    def _parse_json_to_profile(self, data: Dict[str, Any]) -> Optional[CandidateProfile]:
        try:
            if not isinstance(data, dict):
                return None
            if "full_name" not in data or not data["full_name"]:
                data["full_name"] = "Extracted Candidate"

            # Sanitize education items
            if "education" in data and isinstance(data["education"], list):
                for e in data["education"]:
                    if isinstance(e, dict):
                        if not e.get("institution"):
                            e["institution"] = "Educational Institution"
                        if not e.get("degree"):
                            e["degree"] = "Degree"
                        if not e.get("field_of_study"):
                            e["field_of_study"] = "General"

            # Sanitize project items
            if "projects" in data and isinstance(data["projects"], list):
                for p in data["projects"]:
                    if isinstance(p, dict):
                        if not p.get("title"):
                            p["title"] = "Project"
                        if not p.get("description"):
                            p["description"] = p.get("title", "Project initiative")

            # Sanitize experience items
            if "experience" in data and isinstance(data["experience"], list):
                for exp in data["experience"]:
                    if isinstance(exp, dict):
                        if not exp.get("company_name"):
                            exp["company_name"] = "Organization"
                        if not exp.get("designation"):
                            exp["designation"] = "Role"
                        if not exp.get("start_date"):
                            exp["start_date"] = "2022"

            return CandidateProfile.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON output to CandidateProfile: {str(e)}")
            return None
