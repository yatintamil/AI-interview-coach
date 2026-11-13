"""
Semantic Section Chunker for Resume Text RAG Indexing.
Adheres to rag.md standards (metadata preservation, section-aware splitting).
"""

import re
from typing import List, Dict, Any
from ai.config import ai_settings

class ResumeSectionChunker:
    """
    Splits resume text into semantic chunks tagged with section metadata
    for vector search and LLM context retrieval.
    """

    def chunk_text(self, resume_text: str, candidate_id: str, resume_id: str) -> List[Dict[str, Any]]:
        if not resume_text:
            return []

        sections = self._split_into_sections(resume_text)
        chunks: List[Dict[str, Any]] = []
        global_chunk_idx = 0

        for section_name, section_content in sections.items():
            words = section_content.split()
            if not words:
                continue

            # Sliding token / word window
            max_words = ai_settings.chunk_max_tokens
            overlap_words = ai_settings.chunk_overlap_tokens

            i = 0
            while i < len(words):
                chunk_words = words[i : i + max_words]
                chunk_str = " ".join(chunk_words)

                chunks.append({
                    "candidate_id": candidate_id,
                    "resume_id": resume_id,
                    "section_name": section_name,
                    "chunk_index": global_chunk_idx,
                    "content": f"[{section_name.upper()}]\n{chunk_str}",
                    "chunk_metadata": {
                        "word_count": len(chunk_words),
                        "section": section_name,
                        "candidate_id": candidate_id,
                        "resume_id": resume_id
                    }
                })
                global_chunk_idx += 1

                if i + max_words >= len(words):
                    break
                i += max_words - overlap_words

        return chunks

    def _split_into_sections(self, text: str) -> Dict[str, str]:
        """
        Splits resume into logical sections based on headers.
        """
        section_headers = [
            "EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT", "PROJECTS", "EDUCATION",
            "SKILLS", "TECHNICAL SKILLS", "CERTIFICATIONS", "ACHIEVEMENTS", "SUMMARY", "PUBLICATIONS"
        ]
        
        sections: Dict[str, str] = {}
        current_header = "General"

        for line in text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            # Check if line matches a section header
            matched_header = None
            header_end_idx = 0
            for header in section_headers:
                m = re.match(r"^(" + re.escape(header) + r")(:|\b)", line_str, re.IGNORECASE)
                if m:
                    matched_header = header
                    header_end_idx = m.end()
                    break

            if matched_header:
                current_header = matched_header.title()
                remainder = line_str[header_end_idx:].strip()
                if current_header not in sections:
                    sections[current_header] = remainder if remainder else ""
                elif remainder:
                    sections[current_header] += "\n" + remainder
            else:
                if current_header not in sections:
                    sections[current_header] = line_str
                else:
                    sections[current_header] += "\n" + line_str

        # If no explicit sections were found, fall back to full text
        if not sections or (len(sections) == 1 and "General" in sections and not sections["General"].strip()):
            sections["General"] = text.strip()

        return sections
