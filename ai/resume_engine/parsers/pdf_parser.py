"""
PDF Document Parser implementation.
"""

import io
from pathlib import Path
from typing import Union, BinaryIO
from ai.resume_engine.parsers.base import BaseDocumentParser

class PDFDocumentParser(BaseDocumentParser):
    """
    Extracts text from PDF documents using fitz (PyMuPDF) or pdfplumber fallback.
    """

    def parse(self, file_source: Union[str, Path, BinaryIO, bytes]) -> str:
        pdf_bytes: bytes = b""

        if isinstance(file_source, (str, Path)):
            with open(file_source, "rb") as f:
                pdf_bytes = f.read()
        elif isinstance(file_source, bytes):
            pdf_bytes = file_source
        elif hasattr(file_source, "read"):
            pdf_bytes = file_source.read()

        extracted_text = ""

        # Try fitz (PyMuPDF) first
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                extracted_text += page.get_text() + "\n"
            doc.close()
            if extracted_text.strip():
                return self.clean_text(extracted_text)
        except ImportError:
            pass
        except Exception as e:
            pass

        # Try pdfplumber as fallback
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
            if extracted_text.strip():
                return self.clean_text(extracted_text)
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback to pypdf / PyPDF2
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                extracted_text += (page.extract_text() or "") + "\n"
            if extracted_text.strip():
                return self.clean_text(extracted_text)
        except Exception:
            pass

        return self.clean_text(extracted_text)
