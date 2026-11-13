"""
Skill taxonomy and CandidateProfile normalization module.
Deduplicates technologies, normalizes skill names, and computes aggregate metrics.
"""

from typing import List, Set
from backend.schemas.candidate_profile import CandidateProfile, SkillEntity

SYNONYM_MAP = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "reactjs": "React",
    "nextjs": "Next.js",
    "nodejs": "Node.js",
    "vuejs": "Vue",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "k8s": "Kubernetes",
    "docker": "Docker",
}

class CandidateProfileNormalizer:
    """
    Normalizes candidate entities, unifies taxonomy, and calculates aggregate metrics.
    """

    def normalize(self, profile: CandidateProfile) -> CandidateProfile:
        # 1. Normalize & Deduplicate Technologies
        tech_set: Set[str] = set()
        for tech in profile.technologies:
            normalized = SYNONYM_MAP.get(tech.lower().strip(), tech.strip())
            tech_set.add(normalized)

        # 2. Extract technologies from skills and experience
        for skill in profile.skills:
            normalized = SYNONYM_MAP.get(skill.name.lower().strip(), skill.name.strip())
            skill.name = normalized
            tech_set.add(normalized)

        for exp in profile.experience:
            for exp_tech in exp.technologies_used:
                normalized = SYNONYM_MAP.get(exp_tech.lower().strip(), exp_tech.strip())
                tech_set.add(normalized)

        profile.technologies = sorted(list(tech_set))

        # 3. Deduplicate domains and soft skills
        profile.domains = sorted(list({d.strip() for d in profile.domains if d.strip()}))
        profile.soft_skills = sorted(list({s.strip() for s in profile.soft_skills if s.strip()}))

        # 4. Calculate total experience if zero
        if profile.total_years_experience == 0.0 and profile.experience:
            profile.total_years_experience = float(len(profile.experience) * 1.5)

        return profile
