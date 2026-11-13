"""
Pydantic v2 data schemas for CandidateProfile and nested entity objects.
Adheres to backend/schemas standards.
"""

from enum import Enum
from typing import List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

class ProficiencyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class SkillEntity(BaseModel):
    name: str = Field(..., description="Name of the skill (e.g. Python, PostgreSQL, System Design)")
    category: str = Field(default="Technical", description="Category: Technical, Tool, Framework, Database, Cloud, Domain")
    proficiency: Optional[ProficiencyLevel] = Field(default=None, description="Proficiency level if specified or inferred")
    years_of_experience: Optional[float] = Field(default=None, description="Years of experience with this skill")

class ProjectEntity(BaseModel):
    title: str = Field(..., description="Project title")
    description: str = Field(..., description="Description of the project and problem solved")
    role: Optional[str] = Field(default=None, description="Role in the project")
    technologies_used: List[str] = Field(default_factory=list, description="Technologies and libraries used")
    key_achievements: List[str] = Field(default_factory=list, description="Quantifiable results and accomplishments")
    project_url: Optional[str] = Field(default=None, description="Repository or live URL")

class ExperienceEntity(BaseModel):
    company_name: str = Field(..., description="Company or Organization name")
    designation: str = Field(..., description="Job title or role")
    location: Optional[str] = Field(default=None, description="Location or Remote")
    start_date: str = Field(..., description="Start date (YYYY-MM or string)")
    end_date: Optional[str] = Field(default="Present", description="End date (YYYY-MM or Present)")
    is_current: bool = Field(default=False, description="Whether currently working in this role")
    domain: Optional[str] = Field(default=None, description="Industry domain")
    responsibilities: List[str] = Field(default_factory=list, description="Responsibilities and duties")
    key_accomplishments: List[str] = Field(default_factory=list, description="Key accomplishments")
    technologies_used: List[str] = Field(default_factory=list, description="Technologies used in this role")

class EducationEntity(BaseModel):
    institution: str = Field(..., description="University, College, or School")
    degree: str = Field(..., description="Degree title")
    field_of_study: Optional[str] = Field(default="General", description="Major or field of study")
    start_year: Optional[int] = Field(default=None, description="Start year")
    end_year: Optional[int] = Field(default=None, description="Graduation year")
    gpa_or_score: Optional[str] = Field(default=None, description="GPA or grade percentage")
    honors: List[str] = Field(default_factory=list, description="Honors or academic achievements")

class CertificationEntity(BaseModel):
    name: str = Field(..., description="Certification title")
    issuing_organization: str = Field(..., description="Issuing body")
    issue_date: Optional[str] = Field(default=None, description="Issue date")
    expiry_date: Optional[str] = Field(default=None, description="Expiration date")
    credential_id_or_url: Optional[str] = Field(default=None, description="Credential ID or URL")

class AchievementEntity(BaseModel):
    title: str = Field(..., description="Award, competition, or publication title")
    description: Optional[str] = Field(default=None, description="Description")
    date_or_year: Optional[str] = Field(default=None, description="Date or year")

class CandidateProfile(BaseModel):
    """
    Complete Canonical Structured Candidate Profile.
    """
    full_name: str = Field(..., description="Candidate full name")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="Current location")
    summary: Optional[str] = Field(default=None, description="Professional summary")
    
    # Required Extraction Core Fields
    skills: List[SkillEntity] = Field(default_factory=list, description="Skills list")
    projects: List[ProjectEntity] = Field(default_factory=list, description="Projects list")
    experience: List[ExperienceEntity] = Field(default_factory=list, description="Work experience list")
    education: List[EducationEntity] = Field(default_factory=list, description="Education list")
    certifications: List[CertificationEntity] = Field(default_factory=list, description="Certifications list")
    achievements: List[AchievementEntity] = Field(default_factory=list, description="Achievements list")
    technologies: List[str] = Field(default_factory=list, description="Aggregated technical tools & platforms")
    domains: List[str] = Field(default_factory=list, description="Identified industry/functional domains")
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills list")
    
    # Metadata & Coach Inference
    seniority_level: str = Field(default="Fresher / Student", description="Inferred seniority level (e.g. Fresher / Student, Junior, Mid-Level, Senior)")
    recommended_roles: List[str] = Field(default_factory=list, description="Tailored recommended interview roles/tracks")
    total_years_experience: Optional[float] = Field(default=0.0, description="Calculated total years of experience")
    extraction_confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    raw_text_hash: Optional[str] = Field(default=None, description="Source SHA256 checksum")
    personalized_dossier: Optional[dict] = Field(default=None, description="Autonomous web-grounded research dossier and 5-stage personalized interview curriculum")

