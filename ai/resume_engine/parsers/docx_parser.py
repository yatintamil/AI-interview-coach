"""
DOCX Document Parser implementation.
"""

import io
from pathlib import Path
from typing import Union, BinaryIO
from ai.resume_engine.parsers.base import BaseDocumentParser

class DOCXDocumentParser(BaseDocumentParser):
    """
    Extracts text from DOCX documents using python-docx.
    """

    def parse(self, file_source: Union[str, Path, BinaryIO, bytes]) -> str:
        docx_bytes: bytes = b""

        if isinstance(file_source, (str, Path)):
            with open(file_source, "rb") as f:
                docx_bytes = f.read()
        elif isinstance(file_source, bytes):
            docx_bytes = file_source
        elif hasattr(file_source, "read"):
            docx_bytes = file_source.read()

        extracted_text = ""

        try:
            # pyrefly: ignore [missing-import]
            import docx
            doc = docx.Document(io.BytesIO(docx_bytes))
            
            # 1. Paragraph text
            for para in doc.paragraphs:
                if para.text and para.text.strip():
                    extracted_text += para.text.strip() + "\n"

            # 2. Table text (rows and cells)
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        # Deduplicate repeated text from merged cells
                        deduped = []
                        for t in row_text:
                            if not deduped or t != deduped[-1]:
                                deduped.append(t)
                        extracted_text += " | ".join(deduped) + "\n"

            # 3. Text Boxes & DrawingML (often used in modern 2-column or sidebar resume templates)
            try:
                # Search for all w:txbxContent in XML
                body_elem = doc.element.body
                txbx_paragraphs = body_elem.xpath('.//w:txbxContent//w:p')
                for p in txbx_paragraphs:
                    p_text = "".join(t.text for t in p.xpath('.//w:t') if t.text).strip()
                    if p_text and p_text not in extracted_text:
                        extracted_text += p_text + "\n"
            except Exception:
                pass

            # 4. Headers & Footers
            try:
                for section in doc.sections:
                    for hp in section.header.paragraphs:
                        if hp.text and hp.text.strip() and hp.text.strip() not in extracted_text:
                            extracted_text = hp.text.strip() + "\n" + extracted_text
            except Exception:
                pass

        except Exception as e:
            extracted_text = f"Error extracting DOCX text: {str(e)}"

        return self.clean_text(extracted_text)
