"""
Plain Text Document Parser implementation.
"""

from pathlib import Path
from typing import Union, BinaryIO
from ai.resume_engine.parsers.base import BaseDocumentParser

class TextDocumentParser(BaseDocumentParser):
    """
    Extracts text from UTF-8 / plain text documents.
    """

    def parse(self, file_source: Union[str, Path, BinaryIO, bytes]) -> str:
        text = ""

        if isinstance(file_source, (str, Path)):
            with open(file_source, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif isinstance(file_source, bytes):
            text = file_source.decode("utf-8", errors="ignore")
        elif hasattr(file_source, "read"):
            content = file_source.read()
            if isinstance(content, bytes):
                text = content.decode("utf-8", errors="ignore")
            else:
                text = str(content)

        return self.clean_text(text)
