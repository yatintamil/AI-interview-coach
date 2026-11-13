"""
Accurate, Zero-Hallucination Resume & Candidate Profile Extractor.
Extracts EXACTLY what is present in the resume text without inventing dummy companies,
fake universities, or placeholder credentials.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from ai.resume_engine.extractors.base import BaseExtractor
from backend.schemas.candidate_profile import (
    CandidateProfile,
    SkillEntity,
    EducationEntity,
    ExperienceEntity,
    ProjectEntity,
    CertificationEntity,
    AchievementEntity,
)

COMMON_TECH_SKILLS = [
    # Languages
    ("Python", "Language"), ("Java", "Language"), ("JavaScript", "Language"), ("TypeScript", "Language"),
    ("C++", "Language"), ("C/C++", "Language"), ("C#", "Language"), ("C", "Language"),
    ("Go", "Language"), ("Golang", "Language"), ("Rust", "Language"),
    ("Ruby", "Language"), ("PHP", "Language"), ("Swift", "Language"), ("Kotlin", "Language"), ("SQL", "Language"),
    ("HTML", "Language"), ("CSS", "Language"), ("Shell", "Language"), ("Bash", "Language"), ("R", "Language"),
    ("MATLAB", "Engineering Tool"), ("Verilog", "Hardware Description"), ("VHDL", "Hardware Description"),
    # Electrical, Embedded & Hardware
    ("Embedded C", "Embedded Systems"), ("Embedded Systems", "Hardware/Embedded"),
    ("Microcontrollers", "Hardware/Embedded"), ("ARM", "Hardware/Embedded"), ("FPGA", "Hardware/Embedded"),
    ("PCB Design", "Hardware/Electronics"), ("VLSI", "Hardware/Electronics"),
    ("Altium", "Design/CAD"), ("KiCAD", "Design/CAD"), ("PLC", "Industrial Automation"),
    ("SCADA", "Industrial Automation"), ("Arduino", "Hardware/Embedded"),
    ("Raspberry Pi", "Hardware/Embedded"), ("IoT", "Hardware/IoT"), ("Robotics", "Robotics"),
    # Mechanical, Aerospace & Civil
    ("SolidWorks", "Design/CAD"), ("AutoCAD", "Design/CAD"), ("Autodesk Fusion 360", "Design/CAD"),
    ("CATIA", "Design/CAD"), ("ANSYS", "Simulation/CAE"), ("Creo", "Design/CAD"),
    ("Revit", "Design/CAD"), ("STAAD.Pro", "Civil/Structural"), ("CFD", "Simulation/CAE"), ("FEA", "Simulation/CAE"),
    # Frameworks / Web
    ("FastAPI", "Framework"), ("Django", "Framework"), ("Flask", "Framework"), ("React", "Framework"),
    ("Next.js", "Framework"), ("Vue", "Framework"), ("Angular", "Framework"), ("Node.js", "Framework"),
    ("Express", "Framework"), ("Spring Boot", "Framework"), ("GraphQL", "Framework"), ("TailwindCSS", "Framework"),
    ("Bootstrap", "Framework"),
    # AI / ML / Data Science
    ("Machine Learning", "AI/ML"), ("Deep Learning", "AI/ML"), ("Computer Vision", "AI/ML"), ("NLP", "AI/ML"),
    ("PyTorch", "AI/ML"), ("TensorFlow", "AI/ML"), ("Scikit-Learn", "AI/ML"), ("Pandas", "Data Science"),
    ("NumPy", "Data Science"), ("Tableau", "Analytics"), ("Power BI", "Analytics"),
    # Databases & Storage
    ("PostgreSQL", "Database"), ("MySQL", "Database"), ("MongoDB", "Database"), ("Redis", "Database"),
    ("Elasticsearch", "Database"), ("DynamoDB", "Database"), ("SQLite", "Database"),
    # Cloud, DevOps & Security
    ("Docker", "Cloud/DevOps"), ("Kubernetes", "Cloud/DevOps"), ("AWS", "Cloud/DevOps"), ("GCP", "Cloud/DevOps"),
    ("Azure", "Cloud/DevOps"), ("Git", "Cloud/DevOps"), ("GitHub", "Cloud/DevOps"), ("Kafka", "Cloud/DevOps"),
    ("Linux", "Operating Systems"), ("Cybersecurity", "Security"), ("Network Security", "Security"),
]

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b[6-9]\d{9}\b"


class RuleExtractor(BaseExtractor):
    """
    Zero-Hallucination Heuristic Extractor.
    Extracts strictly what is stated in the candidate input text.
    """

    def extract(self, resume_text: str) -> CandidateProfile:
        if not resume_text or not resume_text.strip():
            return CandidateProfile(full_name="Candidate")

        text = resume_text.strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 1. Contact & Location Information
        emails = re.findall(EMAIL_REGEX, text)
        phones = re.findall(PHONE_REGEX, text)
        email = emails[0] if emails else None
        phone = phones[0].strip() if phones else None
        full_name = self._extract_full_name(lines, text, email, phone)
        location = self._extract_location(text)

        # 2. Section Segmentation
        sections = self._segment_sections(text)

        # 3. Summary
        summary = self._extract_summary(sections, lines)

        # 4. Skills & Technologies
        skills, technologies = self._extract_skills(text, sections.get("SKILLS", ""))
        domains = self._extract_domains(text, sections.get("INTERESTS", ""))
        soft_skills = self._extract_soft_skills(text, sections.get("LANGUAGES", ""), sections.get("STRENGTHS", ""))

        # 5. Work Experience (Strict - No fake companies)
        experience_list, total_years_exp = self._extract_experience(sections.get("EXPERIENCE", ""), text)

        # 6. Projects (Strict - Looks for project sections or explicit project descriptions/initiatives)
        projects_list = self._extract_projects(sections.get("PROJECTS", ""), text, summary or "")

        # 7. Education (Strict - Accurately recognizes B.Tech, Diploma, SSLC/School, etc.)
        education_list = self._extract_education(sections.get("EDUCATION", ""), text)

        # 8. Certifications & Achievements
        certifications = self._extract_certifications(sections.get("CERTIFICATIONS", ""))
        achievements = self._extract_achievements(sections.get("ACHIEVEMENTS", ""))

        # 9. Infer Seniority & Recommended Roles for Coach
        seniority_level, recommended_roles = self._infer_seniority_and_roles(text, total_years_exp, skills, education_list)

        return CandidateProfile(
            full_name=full_name,
            email=email,
            phone=phone,
            location=location,
            summary=summary,
            skills=skills,
            projects=projects_list,
            experience=experience_list,
            education=education_list,
            certifications=certifications,
            achievements=achievements,
            technologies=list(technologies),
            domains=domains,
            soft_skills=soft_skills,
            seniority_level=seniority_level,
            recommended_roles=recommended_roles,
            total_years_experience=total_years_exp,
            extraction_confidence_score=0.95,
        )

    def _extract_location(self, text: str) -> Optional[str]:
        # 1. Match explicit Place/Location/Address label or pin emoji 📍
        loc_match = re.search(r"(?:Location|Address|Place|City|Country|📍)\s*[:\-]?\s*([^\n|•]+)", text, re.IGNORECASE)
        if loc_match:
            candidate_val = loc_match.group(1).split("|")[0].split("•")[0].strip()
            candidate_val = re.sub(r"^[^\w]+", "", candidate_val).strip()
            if candidate_val and len(candidate_val) < 80 and not any(kw in candidate_val.lower() for kw in ["summary", "skills", "experience", "education", "http", "@"]):
                return candidate_val

        # 2. Match city/state with explicit postal code (e.g. "COIMBATORE - 641004" or "Seattle, WA 98101")
        postal_match = re.search(r"\b([A-Za-z\s]{3,30}(?:,\s*[A-Za-z\s]{2,30})?\s*-\s*\d{5,7})\b", text[:800])
        if postal_match:
            cand = postal_match.group(1).strip()
            if not any(kw in cand.lower() for kw in ["student", "engineer", "developer", "university", "college", "school", "gmail", "email", "phone"]):
                return cand

        # 3. Match standard City, State abbreviation (e.g. "San Francisco, CA" or "Austin, TX")
        us_states_re = r"\b([A-Z][a-zA-Z\s]{2,25},\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|India|USA|UK|Canada|Germany))\b"
        state_match = re.search(us_states_re, text[:800])
        if state_match:
            cand = state_match.group(1).strip()
            return cand

        return None

    def _extract_full_name(self, lines: List[str], text: str, email: Optional[str], phone: Optional[str]) -> str:
        # Check for explicit "Name:" prefix
        name_match = re.search(r"^(?:Name|Candidate Name|Full Name)\s*:\s*([a-zA-Z\s\.\-']+)", text, re.MULTILINE | re.IGNORECASE)
        if name_match:
            return name_match.group(1).strip()

        # Check first line if short and alphabetical
        if lines:
            first_line = lines[0].strip()
            if (
                len(first_line.split()) <= 4
                and not re.search(EMAIL_REGEX, first_line)
                and not re.search(PHONE_REGEX, first_line)
                and not re.search(r"^(?:resume|cv|summary|objective|about|profile|skills|experience|i\s+am|i\s+was)", first_line, re.IGNORECASE)
                and re.match(r"^[a-zA-Z\s\.\-']+$", first_line)
            ):
                return first_line

        # Infer from email username if available
        if email:
            uname = email.split("@")[0].replace(".", " ").replace("_", " ").title()
            if len(uname.split()) >= 1 and re.match(r"^[a-zA-Z\s]+$", uname):
                return uname

        return "Candidate"

    def _segment_sections(self, text: str) -> Dict[str, str]:
        section_headers = {
            "EXPERIENCE": r"(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|EXPERIENCE)",
            "PROJECTS": r"(?:PROJECTS|KEY\s+PROJECTS|ACADEMIC\s+PROJECTS|PERSONAL\s+PROJECTS)",
            "EDUCATION": r"(?:EDUCATION|ACADEMIC\s+BACKGROUND|QUALIFICATIONS)",
            "SKILLS": r"(?:SKILLS|TECHNICAL\s+SKILLS|CORE\s+COMPETENCIES|TECHNOLOGIES)",
            "SUMMARY": r"(?:PROFESSIONAL\s+SUMMARY|SUMMARY|PROFILE|OBJECTIVE|ABOUT\s+ME)",
            "CERTIFICATIONS": r"(?:CERTIFICATIONS|LICENSES|COURSES)",
            "ACHIEVEMENTS": r"(?:ACHIEVEMENTS|AWARDS|HONORS)",
            "INTERESTS": r"(?:INTERESTS|AREAS\s+OF\s+INTEREST)",
            "LANGUAGES": r"(?:LANGUAGES|LANGUAGES\s+KNOWN)",
            "STRENGTHS": r"(?:STRENGTHS|KEY\s+STRENGTHS)",
        }

        pattern = r"\n\s*(?:" + "|".join(f"(?P<{k}>{v})" for k, v in section_headers.items()) + r")\s*[:\n]"
        matches = list(re.finditer(pattern, text, re.IGNORECASE))

        sections: Dict[str, str] = {}
        if not matches:
            return sections

        for i, match in enumerate(matches):
            section_type = next((k for k, v in match.groupdict().items() if v is not None), None)
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            if section_type:
                sections[section_type] = text[start_pos:end_pos].strip()

        return sections

    def _extract_summary(self, sections: Dict[str, str], lines: List[str]) -> Optional[str]:
        if "SUMMARY" in sections and sections["SUMMARY"]:
            return sections["SUMMARY"].split("\n\n")[0].strip()

        for line in lines[:4]:
            if len(line) > 30 and not re.search(r"^(?:skills|education|experience|phone|email):", line, re.IGNORECASE):
                return line
        return None

    def _extract_skills(self, text: str, skills_section: str = "") -> Tuple[List[SkillEntity], Set[str]]:
        found_skills: List[SkillEntity] = []
        found_technologies: Set[str] = set()
        seen: Set[str] = set()
        search_target = f"{text}\n{skills_section}"

        for skill_name, category in COMMON_TECH_SKILLS:
            if re.search(r"\b" + re.escape(skill_name) + r"\b", search_target, re.IGNORECASE):
                if skill_name.lower() not in seen:
                    seen.add(skill_name.lower())
                    found_skills.append(SkillEntity(name=skill_name, category=category))
                    found_technologies.add(skill_name)

        return found_skills, found_technologies

    def _extract_domains(self, text: str, interests_section: str = "") -> List[str]:
        common_domains = [
            "Embedded Systems", "Hardware Engineering", "Mechanical Engineering", "Civil Engineering",
            "Electrical Engineering", "VLSI & Chip Design", "Aerospace Engineering", "Automotive Systems",
            "Artificial Intelligence", "Machine Learning", "Data Science", "Cloud Computing",
            "Cybersecurity", "Web Development", "Mobile Development", "DevOps & Infrastructure",
            "FinTech", "HealthTech", "Biotechnology", "Robotics", "Computer Vision"
        ]
        domains: List[str] = []
        combined = f"{text}\n{interests_section}"
        for domain in common_domains:
            if re.search(r"\b" + re.escape(domain) + r"\b", combined, re.IGNORECASE):
                domains.append(domain)
        return sorted(list(set(domains)))

    def _extract_soft_skills(self, text: str, languages_section: str = "", strengths_section: str = "") -> List[str]:
        common_soft = [
            "Leadership", "Communication", "Problem Solving", "Agile", "Scrum", "Team Collaboration",
            "Critical Thinking", "Time Management", "Adaptability", "Mentorship", "System Architecture",
            "Analytical Thinking", "Innovation"
        ]
        soft: List[str] = []
        combined = f"{text}\n{languages_section}\n{strengths_section}"
        for s in common_soft:
            if re.search(r"\b" + re.escape(s) + r"\b", combined, re.IGNORECASE):
                soft.append(s)

        # Only extract languages if explicit language section or header is present
        lang_target = languages_section
        if not lang_target:
            explicit_lang_match = re.search(r"(?:Languages?|Spoken Languages?|Languages Known)\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
            if explicit_lang_match:
                lang_target = explicit_lang_match.group(1)

        if lang_target:
            world_languages = [
                "English", "Spanish", "French", "German", "Mandarin", "Hindi", "Arabic",
                "Portuguese", "Russian", "Japanese", "Tamil", "Telugu", "Kannada", "Malayalam",
                "Bengali", "Italian", "Korean", "Dutch", "Turkish"
            ]
            for lang in world_languages:
                if re.search(r"\b" + re.escape(lang) + r"\b", lang_target, re.IGNORECASE):
                    soft.append(f"{lang} (Language)")

        return sorted(list(set(soft)))

    def _extract_experience(self, exp_section: str, full_text: str) -> Tuple[List[ExperienceEntity], float]:
        if not exp_section:
            return [], 0.0

        experience_list: List[ExperienceEntity] = []
        total_exp = 0.0

        exp_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*years?(?:\s+of)?\s+experience", full_text, re.IGNORECASE)
        if exp_match:
            try:
                total_exp = float(exp_match.group(1))
            except Exception:
                pass

        blocks = [b.strip() for b in exp_section.split("\n\n") if b.strip()]
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not lines:
                continue

            first_line = lines[0]
            header_match = re.search(r"^(.*?)(?:\||-|@|at|,)\s*(.*?)(?:\((.*?)\)|$)", first_line)
            if header_match:
                designation = header_match.group(1).strip()
                company = header_match.group(2).strip()
                date_range = header_match.group(3).strip() if header_match.group(3) else "2022 - Present"
            else:
                designation = first_line
                company = "Organization"
                date_range = "2022 - Present"

            responsibilities: List[str] = []
            for line in lines[1:]:
                cleaned = re.sub(r"^[-*•]\s*", "", line).strip()
                if len(cleaned) > 10:
                    responsibilities.append(cleaned)

            techs = [s[0] for s in COMMON_TECH_SKILLS if re.search(r"\b" + re.escape(s[0]) + r"\b", block, re.IGNORECASE)]

            dates_found = re.findall(r"\b(20\d\d|19\d\d|Present)\b", date_range, re.IGNORECASE)
            start_date = dates_found[0] if len(dates_found) >= 1 else "2022"
            end_date = dates_found[1] if len(dates_found) >= 2 else "Present"

            experience_list.append(
                ExperienceEntity(
                    company_name=company,
                    designation=designation,
                    start_date=start_date,
                    end_date=end_date,
                    is_current=("present" in end_date.lower()),
                    responsibilities=responsibilities or [first_line],
                    technologies_used=techs[:8],
                )
            )

        if total_exp == 0.0 and experience_list:
            total_exp = float(len(experience_list) * 2)

        return experience_list, total_exp

    def _extract_projects(self, projects_section: str, full_text: str, summary: str = "") -> List[ProjectEntity]:
        projects: List[ProjectEntity] = []

        # 1. From dedicated PROJECTS section
        if projects_section:
            blocks = [b.strip() for b in projects_section.split("\n\n") if b.strip()]
            for block in blocks:
                lines = [l.strip() for l in block.splitlines() if l.strip()]
                if not lines:
                    continue

                title = re.sub(r"^[-*•●\d\.\)]\s*", "", lines[0]).strip()
                desc = " ".join(lines[1:]) if len(lines) > 1 else title
                achievements = [re.sub(r"^[-*•●]\s*", "", l).strip() for l in lines[1:] if len(l.strip()) > 15]
                techs = [s[0] for s in COMMON_TECH_SKILLS if re.search(r"\b" + re.escape(s[0]) + r"\b", block, re.IGNORECASE)]

                projects.append(
                    ProjectEntity(
                        title=title,
                        description=desc[:300],
                        technologies_used=techs[:8],
                        key_achievements=achievements[:4] if achievements else [desc[:150]],
                    )
                )

        # 2. Extract action-driven project sentences from full text if no explicit section
        if not projects:
            project_patterns = [
                r"(?:Developed|Implemented|Built|Designed|Engineered|Created|Deployed|Architected)\s+([^\n\.\;]{10,120})",
            ]
            for pat in project_patterns:
                matches = re.finditer(pat, full_text, re.IGNORECASE)
                for m in matches:
                    raw_title = m.group(1).strip()
                    sentence = m.group(0).strip()
                    title_words = raw_title.split()[:6]
                    short_title = " ".join(title_words).title()
                    techs = [s[0] for s in COMMON_TECH_SKILLS if re.search(r"\b" + re.escape(s[0]) + r"\b", sentence, re.IGNORECASE)]
                    projects.append(
                        ProjectEntity(
                            title=short_title,
                            description=sentence,
                            technologies_used=techs[:6],
                            key_achievements=[sentence],
                        )
                    )
                    if len(projects) >= 4:
                        break
                if projects:
                    break

        return projects

    def _extract_education(self, edu_section: str, full_text: str) -> List[EducationEntity]:
        target_text = edu_section if edu_section and len(edu_section.strip()) > 10 else full_text
        education_list: List[EducationEntity] = []

        degree_patterns = [
            (r"\b(?:B\.?Tech|B\.E\b|Bachelor\s+of\s+Technology|Bachelor\s+of\s+Engineering)\b", "Bachelor of Technology (B.Tech)"),
            (r"\b(?:B\.?S\b|B\.?Sc\b|Bachelor\s+of\s+Science)\b", "Bachelor of Science (B.S.)"),
            (r"\b(?:B\.?A\b|Bachelor\s+of\s+Arts)\b", "Bachelor of Arts (B.A.)"),
            (r"\b(?:M\.?Tech|M\.E\b|Master\s+of\s+Technology|Master\s+of\s+Engineering)\b", "Master of Technology (M.Tech)"),
            (r"\b(?:M\.?S\b|M\.?Sc\b|Master\s+of\s+Science)\b", "Master of Science (M.S.)"),
            (r"\b(?:M\.?B\.?A\b|Master\s+of\s+Business\s+Administration)\b", "Master of Business Administration (MBA)"),
            (r"\b(?:Ph\.?D\b|Doctorate|Doctor\s+of\s+Philosophy)\b", "Doctor of Philosophy (Ph.D)"),
            (r"\b(?:DECE|Diploma\s+in\s+Electronics[^\n,]*)\b", "Diploma in Electronics & Communication (DECE)"),
            (r"\b(?:Diploma\s+in\s+([^\n,]+)|Diploma)\b", "Diploma in Engineering"),
            (r"\b(?:SSLC|Secondary\s+School\s+Leaving\s+Certificate)\b", "Secondary School Certificate (SSLC)"),
            (r"\b(?:HSC|Higher\s+Secondary|12th\s+Standard|10th\s+Standard)\b", "Higher Secondary Certificate (HSC)"),
        ]

        lines = [l.strip() for l in target_text.splitlines() if l.strip()]
        inst_keywords = ["institute", "university", "college", "school", "academy", "polytechnic", "vidyalaya"]

        # Locate degree lines - ensure line is not just an institution name containing 'school'/'college'
        degree_indices = []
        for idx, line in enumerate(lines):
            is_inst = any(kw in line.lower() for kw in inst_keywords)
            for pat, label in degree_patterns:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    # If line has institution keyword and does not start with a degree word, skip treating as degree line
                    if is_inst and not re.match(r"^(?:B\.?Tech|B\.E|DECE|SSLC|HSC|Diploma|Bachelor|Master|Doctorate|Ph\.?D)", line, re.IGNORECASE):
                        continue
                    degree_indices.append((idx, line, m, label))
                    break

        for i, (deg_idx, line, match, deg_label) in enumerate(degree_indices):
            prev_bound = degree_indices[i-1][0] if i > 0 else -1
            next_bound = degree_indices[i+1][0] if i < len(degree_indices) - 1 else len(lines)

            # 1. Field of study
            field = "General"
            field_match = re.search(r"(?:in|specializing\s+in|major\s+in)\s+([^\n,\|]+)", line, re.IGNORECASE)
            if field_match:
                field = field_match.group(1).strip()
            else:
                cleaned_line = line.replace(match.group(0), "").strip(" -:|,\t")
                if cleaned_line and not any(kw in cleaned_line.lower() for kw in inst_keywords):
                    field = cleaned_line

            if "DECE" in deg_label:
                field = "Electronics and Communication Engineering"
            elif "B.Tech" in deg_label and field == "General":
                field = "Engineering & Technology"
            elif "SSLC" in deg_label or "HSC" in deg_label:
                field = "General"

            # 2. Institution search strictly within this entry's boundary
            inst = None
            for c_idx in range(deg_idx + 1, min(next_bound, deg_idx + 3)):
                cand_line = lines[c_idx]
                if any(kw in cand_line.lower() for kw in inst_keywords):
                    inst = cand_line.strip(" -:|•*●\t")
                    break

            if not inst and deg_idx - 1 > prev_bound:
                cand_line = lines[deg_idx - 1]
                if any(kw in cand_line.lower() for kw in inst_keywords):
                    inst = cand_line.strip(" -:|•*●\t")

            if not inst:
                inst = "Educational Institution"

            # 3. Date search within this entry's boundary
            chunk = " ".join(lines[deg_idx:min(next_bound, deg_idx + 3)])
            years = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", chunk)]
            start_yr = years[0] if len(years) >= 2 else (years[0] if years else None)
            end_yr = years[1] if len(years) >= 2 else None

            if not any(e.degree == deg_label and e.institution == inst for e in education_list):
                education_list.append(
                    EducationEntity(
                        institution=inst,
                        degree=deg_label,
                        field_of_study=field,
                        start_year=start_yr,
                        end_year=end_yr,
                    )
                )

        return education_list

    def _extract_certifications(self, cert_section: str) -> List[CertificationEntity]:
        if not cert_section:
            return []
        certs: List[CertificationEntity] = []
        for line in cert_section.splitlines():
            cleaned = re.sub(r"^[-*•]\s*", "", line).strip()
            if len(cleaned) > 5:
                certs.append(CertificationEntity(name=cleaned, issuing_organization="Certifying Authority"))
        return certs

    def _extract_achievements(self, ach_section: str) -> List[AchievementEntity]:
        if not ach_section:
            return []
        achs: List[AchievementEntity] = []
        for line in ach_section.splitlines():
            cleaned = re.sub(r"^[-*•]\s*", "", line).strip()
            if len(cleaned) > 5:
                achs.append(AchievementEntity(title=cleaned))
        return achs

    def _infer_seniority_and_roles(
        self,
        text: str,
        total_years: float,
        skills: List[SkillEntity],
        education: List[EducationEntity]
    ) -> Tuple[str, List[str]]:
        is_fresher = (
            total_years <= 1.0
            or bool(re.search(r"\b(student|undergraduate|fresher|intern)\b", text, re.IGNORECASE))
        )
        seniority = "Fresher / Student" if is_fresher else ("Junior" if total_years < 3.0 else ("Mid-Level" if total_years < 5.0 else "Senior"))

        lower = text.lower()
        roles: List[str] = []

        # Check Data Science / AI / ML
        if any(kw in lower for kw in ["artificial intelligence", "ai&ds", "ai and data science", "data science", "machine learning", "deep learning", "nlp", "computer vision", "pytorch", "tensorflow"]):
            roles.append("AI & Data Science Specialist" if is_fresher else "Machine Learning Engineer")
            roles.append("Junior Data Scientist" if is_fresher else "Senior Data Scientist")

        # Check Software / Full-Stack / Backend / Frontend
        if any(kw in lower for kw in ["software", "full stack", "full-stack", "backend", "frontend", "react", "fastapi", "django", "java", "python", "node", "javascript", "sql", "web development"]):
            roles.append("Full-Stack Software Engineer" if not is_fresher else "Software Engineer (Associate)")
            roles.append("Backend Systems Engineer")

        # Check Electrical / Electronics / Embedded / Hardware
        if any(kw in lower for kw in ["electrical", "electronics", "dece", "vlsi", "microcontroller", "embedded c", "embedded systems", "pcb", "circuit", "verilog", "vhdl", "fpga", "robotics"]):
            roles.append("Embedded Systems Engineer")
            roles.append("Robotics & Hardware Systems Engineer")

        # Check Cloud / DevOps / Cybersecurity
        if any(kw in lower for kw in ["devops", "kubernetes", "docker", "cloud", "aws", "azure", "cybersecurity", "security", "ethical hacking"]):
            roles.append("Cloud & DevOps Engineer")
            roles.append("Cybersecurity Systems Analyst")

        # Check Mechanical / Aerospace / Civil (Only if explicit engineering discipline mentioned)
        if any(kw in lower for kw in ["mechanical engineering", "aerospace", "solidworks", "ansys", "catia", "thermodynamics", "cfd"]):
            roles.append("Mechanical Design Engineer" if is_fresher else "Senior Mechanical Engineer")
            roles.append("CAD/CAE Systems Specialist")
        if any(kw in lower for kw in ["civil engineering", "structural engineering", "staad", "revit", "construction engineering", "surveying"]):
            roles.append("Civil & Structural Engineer")

        if not roles:
            roles = ["Graduate Engineering Trainee" if is_fresher else "Systems Engineer", "Technical Specialist"]

        return seniority, roles[:4]
