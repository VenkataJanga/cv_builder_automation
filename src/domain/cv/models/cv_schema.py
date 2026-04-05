from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class PersonalDetails(BaseModel):
    full_name: str
    current_title: str
    total_experience: Optional[float] = None
    current_organization: Optional[str] = None
    location: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None


class Summary(BaseModel):
    professional_summary: str
    target_role: Optional[str] = None


class Skills(BaseModel):
    primary_skills: List[str] = Field(default_factory=list)
    secondary_skills: List[str] = Field(default_factory=list)
    tools_and_platforms: List[str] = Field(default_factory=list)
    domain_expertise: List[str] = Field(default_factory=list)


class WorkExperience(BaseModel):
    company_name: str
    role_title: str
    start_date: date
    end_date: Optional[date] = None
    responsibilities: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    location: Optional[str] = None


class ProjectExperience(BaseModel):
    project_name: str
    client_name: Optional[str] = None
    role: str
    duration: Optional[str] = None
    team_size: Optional[int] = None
    technologies: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    outcomes: List[str] = Field(default_factory=list)


class Certification(BaseModel):
    certification_name: str
    issuing_organization: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None


class Education(BaseModel):
    degree: str
    institution: str
    specialization: Optional[str] = None
    year_of_completion: Optional[int] = None


class Publication(BaseModel):
    title: str
    publisher: Optional[str] = None
    publication_date: Optional[date] = None
    link: Optional[str] = None


class Award(BaseModel):
    award_name: str
    organization: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None


class Language(BaseModel):
    language_name: str
    proficiency: Optional[str] = None


class CVSchema(BaseModel):
    personal_details: PersonalDetails
    summary: Summary
    skills: Skills
    work_experience: List[WorkExperience]
    project_experience: List[ProjectExperience]
    certifications: List[Certification]
    education: List[Education]

    # Optional Sections
    publications: Optional[List[Publication]] = None
    awards: Optional[List[Award]] = None
    languages: Optional[List[Language]] = None

    # Metadata
    target_role: Optional[str] = None
    schema_version: str = "1.0"