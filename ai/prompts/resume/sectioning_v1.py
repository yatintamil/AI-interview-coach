"""
Prompt template version 1 for Resume Section Segmentation.
Isolated prompt definitions as per .agents/standards/llm.md guidelines.
"""

SECTIONING_SYSTEM_PROMPT = """You are a document layout analysis engine. 
Given a raw resume text, break the text down into clean, coherent structural sections (e.g. Work Experience, Education, Projects, Skills, Summary, Certifications, Awards).

Return a JSON map where keys are canonical section names and values are the exact verbatim content of that section."""

SECTIONING_USER_PROMPT_TEMPLATE = """Break down the following resume text into logical sections:

--- RESUME TEXT ---
{resume_text}
--- END RESUME TEXT ---

Return ONLY a JSON map of section names to content strings."""
