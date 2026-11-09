"""
resume_parser.py
-----------------
Extracts structured information from raw resume text:
name, email, phone, education, experience, skills, projects, certifications.

Uses a combination of regex pattern matching (contact info) and
section-header based text segmentation (education/experience/etc.),
which is a common, dependable approach for keyword/NLP-based resume
parsing without requiring a heavyweight NER model.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.modules.skill_extractor import extract_skills_from_bullet_section

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s\-]?)?(\(?\d{3,4}\)?[\s\-]?)\d{3}[\s\-]?\d{3,4}")
LINKEDIN_RE = re.compile(r"(linkedin\.com/in/[A-Za-z0-9\-_/]+)", re.IGNORECASE)
GITHUB_RE = re.compile(r"(github\.com/[A-Za-z0-9\-_/]+)", re.IGNORECASE)

# Section header aliases -> canonical section name
SECTION_HEADERS = {
    "education": ["education", "academic background", "academics"],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "internship",
        "internships",
    ],
    "skills": ["skills", "technical skills", "core competencies", "key skills"],
    "projects": ["projects", "academic projects", "personal projects"],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
        "courses",
    ],
}


@dataclass
class ParsedResume:
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    education: str = ""
    experience: str = ""
    skills_section: str = ""
    skills_list: List[str] = field(default_factory=list)
    projects: str = ""
    certifications: str = ""
    raw_text: str = ""


def _guess_name(text: str) -> Optional[str]:
    """
    Heuristic: the candidate's name is usually the first non-empty line
    that doesn't look like an email, phone number, or section header,
    and is reasonably short (2-5 words, no digits).
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:6]:
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        words = line.split()
        if 1 <= len(words) <= 5 and not any(ch.isdigit() for ch in line):
            if line.lower() not in ("resume", "curriculum vitae", "cv"):
                return line.strip(" -|")
    return lines[0] if lines else None


def _split_into_sections(text: str) -> Dict[str, str]:
    """
    Walk through the resume line by line, detect section-header lines
    (short lines matching one of SECTION_HEADERS aliases), and bucket the
    text that follows each header until the next header is found.
    """
    lines = text.splitlines()
    sections: Dict[str, List[str]] = {key: [] for key in SECTION_HEADERS}
    current_section: Optional[str] = None

    def match_header(line: str) -> Optional[str]:
        stripped = line.strip().lower().strip(":")
        if len(stripped.split()) > 5:
            return None
        for canonical, aliases in SECTION_HEADERS.items():
            if stripped in aliases:
                return canonical
        return None

    for line in lines:
        header = match_header(line)
        if header:
            current_section = header
            continue
        if current_section:
            sections[current_section].append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def parse_resume(raw_text: str) -> ParsedResume:
    """Main entry point: parse raw resume text into a ParsedResume object."""
    text = raw_text or ""

    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    linkedin_match = LINKEDIN_RE.search(text)
    github_match = GITHUB_RE.search(text)

    sections = _split_into_sections(text)
    skills_list = extract_skills_from_bullet_section(sections.get("skills", ""))

    return ParsedResume(
        name=_guess_name(text),
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0).strip() if phone_match else None,
        linkedin=linkedin_match.group(1) if linkedin_match else None,
        github=github_match.group(1) if github_match else None,
        education=sections.get("education", ""),
        experience=sections.get("experience", ""),
        skills_section=sections.get("skills", ""),
        skills_list=skills_list,
        projects=sections.get("projects", ""),
        certifications=sections.get("certifications", ""),
        raw_text=text,
    )
