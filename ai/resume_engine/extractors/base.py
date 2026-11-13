"""
Abstract Base Class for Candidate Entity Extractors.
"""

from abc import ABC, abstractmethod
from backend.schemas.candidate_profile import CandidateProfile

class BaseExtractor(ABC):
    """
    Interface for extracting CandidateProfile from raw resume text.
    """

    @abstractmethod
    def extract(self, resume_text: str) -> CandidateProfile:
        """
        Extracts structured CandidateProfile object from plain text.

        :param resume_text: Plain text content of resume.
        :return: Validated CandidateProfile object.
        """
        pass
