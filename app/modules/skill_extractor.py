"""
skill_extractor.py
-------------------
Keyword-based skill extraction and Resume <-> Job Description skill
comparison. Uses a curated skills dictionary (easily extendable) plus
simple n-gram/alias matching so multi-word skills like "machine learning"
or "power bi" are detected correctly.
"""

import re
from dataclasses import dataclass, field
from typing import List, Set

from utils.helpers import normalize_for_matching

# ---------------------------------------------------------------------------
# Curated skill dictionary, grouped by category. Each skill maps to a list
# of aliases/synonyms so real-world phrasing variations are still detected.
# ---------------------------------------------------------------------------
SKILL_DB = {
    "Programming Languages": {
        "python": ["python"],
        "java": ["java"],
        "c++": ["c++", "cpp"],
        "c#": ["c#", "c sharp"],
        "javascript": ["javascript", "js"],
        "typescript": ["typescript", "ts"],
        "sql": ["sql"],
        "r": ["r programming", " r "],
        "go": ["golang", " go "],
        "php": ["php"],
    },
    "AI / ML": {
        "machine learning": ["machine learning", "ml"],
        "deep learning": ["deep learning", "dl"],
        "natural language processing": ["natural language processing", "nlp"],
        "computer vision": ["computer vision", "cv"],
        "tensorflow": ["tensorflow"],
        "pytorch": ["pytorch"],
        "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
        "keras": ["keras"],
        "opencv": ["opencv"],
        "llm": ["llm", "large language model", "large language models"],
        "generative ai": ["generative ai", "genai"],
        "transformers": ["transformers", "huggingface", "hugging face"],
        "rag": ["retrieval augmented generation", "rag"],
    },
    "Data": {
        "pandas": ["pandas"],
        "numpy": ["numpy"],
        "data analysis": ["data analysis", "data analytics"],
        "data visualization": ["data visualization", "data viz"],
        "power bi": ["power bi", "powerbi"],
        "tableau": ["tableau"],
        "excel": ["excel", "ms excel"],
        "statistics": ["statistics", "statistical analysis"],
        "etl": ["etl", "data pipeline", "data pipelines"],
    },
    "Web Development": {
        "react": ["react", "react.js", "reactjs"],
        "next.js": ["next.js", "nextjs"],
        "node.js": ["node.js", "nodejs", "node"],
        "django": ["django"],
        "flask": ["flask"],
        "fastapi": ["fastapi"],
        "html": ["html"],
        "css": ["css"],
        "rest api": ["rest api", "restful api", "rest apis"],
        "graphql": ["graphql"],
    },
    "Cloud & DevOps": {
        "aws": ["aws", "amazon web services"],
        "azure": ["azure", "microsoft azure"],
        "gcp": ["gcp", "google cloud"],
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
        "ci/cd": ["ci/cd", "ci cd", "continuous integration"],
        "linux": ["linux"],
        "git": ["git", "github", "version control"],
        "terraform": ["terraform"],
    },
    "Databases": {
        "postgresql": ["postgresql", "postgres"],
        "mysql": ["mysql"],
        "mongodb": ["mongodb", "mongo"],
        "redis": ["redis"],
        "sqlite": ["sqlite"],
        "vector database": ["vector database", "vector db", "pinecone", "chromadb", "faiss"],
    },
    "Soft Skills": {
        "communication": ["communication skills", "communication"],
        "teamwork": ["teamwork", "collaboration"],
        "leadership": ["leadership"],
        "problem solving": ["problem solving", "problem-solving"],
        "project management": ["project management"],
        "agile": ["agile", "scrum"],
    },
}


@dataclass
class SkillComparison:
    resume_skills: Set[str] = field(default_factory=set)
    jd_skills: Set[str] = field(default_factory=set)
    matched: Set[str] = field(default_factory=set)
    missing: Set[str] = field(default_factory=set)
    extra: Set[str] = field(default_factory=set)

    @property
    def match_ratio(self) -> float:
        if not self.jd_skills:
            return 1.0 if self.resume_skills else 0.0
        return len(self.matched) / len(self.jd_skills)


def extract_skills(text: str) -> Set[str]:
    """
    Scan free text and return the canonical set of skills found, based on
    the SKILL_DB dictionary and its aliases.
    """
    normalized = f" {normalize_for_matching(text)} "
    found = set()

    for _, skills in SKILL_DB.items():
        for canonical, aliases in skills.items():
            for alias in aliases:
                pattern = r"(?<![a-z0-9])" + re.escape(alias.strip()) + r"(?![a-z0-9])"
                if re.search(pattern, normalized):
                    found.add(canonical)
                    break
    return found


def extract_skills_from_bullet_section(section_text: str) -> List[str]:
    """
    Extract an explicit "Skills" section into a clean list, splitting on
    common delimiters (commas, bullets, pipes, newlines) in addition to
    the dictionary-based matching in extract_skills().
    """
    if not section_text:
        return []
    parts = re.split(r"[\n,•|/;]+", section_text)
    cleaned = [p.strip(" -\t") for p in parts if p.strip(" -\t")]
    # De-duplicate while preserving order
    seen = set()
    result = []
    for item in cleaned:
        key = item.lower()
        if key not in seen and 1 < len(item) < 40:
            seen.add(key)
            result.append(item)
    return result


def compare_resume_to_jd(resume_text: str, jd_text: str) -> SkillComparison:
    """Compare the skill sets extracted from a resume and a job description."""
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)

    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills
    extra = resume_skills - jd_skills

    return SkillComparison(
        resume_skills=resume_skills,
        jd_skills=jd_skills,
        matched=matched,
        missing=missing,
        extra=extra,
    )


def recommend_skills_to_learn(comparison: SkillComparison, limit: int = 8) -> List[str]:
    """Simple recommendation: prioritize missing JD-required skills."""
    return sorted(comparison.missing)[:limit]
