"""
Abstract Base Class for Document Parsers.
"""

from abc import ABC, abstractmethod
from typing import Union, BinaryIO
from pathlib import Path

class BaseDocumentParser(ABC):
    """
    Interface for extracting raw clean text from various resume file formats.
    """

    @abstractmethod
    def parse(self, file_source: Union[str, Path, BinaryIO, bytes]) -> str:
        """
        Parses document file content and returns extracted plain text.

        :param file_source: File path, file-like object, or raw bytes.
        :return: Extracted plain text content.
        """
        pass

    def clean_text(self, text: str) -> str:
        """
        Utility to normalize whitespace and remove control characters.
        """
        if not text:
            return ""
        # Normalize carriage returns and line endings
        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n".join([line for line in lines if line])
        return cleaned
