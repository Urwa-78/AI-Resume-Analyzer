"""
scoring_engine.py
------------------
Implements the weighted Resume Match Score and the ATS Resume Score.

Match Score = Skills(50%) + Experience(20%) + Education(15%) + Projects(15%)

Text similarity between free-text sections (experience/education/projects)
uses a lightweight TF cosine-similarity implementation (no heavy ML
dependency required), which satisfies the "semantic similarity comparison"
requirement while keeping the project dependency-light and fast to run.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from app.config import SCORE_WEIGHTS
from app.modules.resume_parser import ParsedResume
from app.modules.skill_extractor import SkillComparison

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "being", "this", "that",
    "as", "at", "by", "it", "its", "from", "will", "we", "you", "your",
    "our", "their", "have", "has had", "not", "but", "into", "such",
    "than", "then", "so", "if", "over", "about", "which", "who", "whom",
}


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\+\#]*", (text or "").lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def cosine_similarity(text_a: str, text_b: str) -> float:
    """
    Compute cosine similarity between two texts based on term-frequency
    vectors. Returns a value between 0.0 and 1.0.
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0

    vec_a, vec_b = Counter(tokens_a), Counter(tokens_b)
    all_terms = set(vec_a) | set(vec_b)

    dot = sum(vec_a[t] * vec_b[t] for t in all_terms)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class MatchScoreBreakdown:
    skills_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    projects_score: float = 0.0
    overall_score: float = 0.0
    weights: Dict[str, float] = field(default_factory=lambda: dict(SCORE_WEIGHTS))


@dataclass
class ATSResult:
    keyword_score: float
    structure_score: float
    skills_coverage_score: float
    experience_relevance_score: float
    overall_ats_score: float
    missing_sections: List[str]


def compute_match_score(
    parsed_resume: ParsedResume, jd_text: str, comparison: SkillComparison
) -> MatchScoreBreakdown:
    """Compute the weighted overall Resume <-> JD match score."""

    skills_score = round(comparison.match_ratio * 100, 1)

    experience_score = round(
        cosine_similarity(parsed_resume.experience, jd_text) * 100, 1
    )
    # Blend in a small bonus if resume experience is non-trivial in length
    if parsed_resume.experience and len(parsed_resume.experience.split()) > 40:
        experience_score = min(100.0, experience_score + 5)

    education_score = round(
        cosine_similarity(parsed_resume.education, jd_text) * 100, 1
    )
    if not parsed_resume.education:
        education_score = 30.0  # neutral baseline if no education section detected

    projects_score = round(
        cosine_similarity(parsed_resume.projects, jd_text) * 100, 1
    )
    if not parsed_resume.projects:
        projects_score = 30.0

    weights = SCORE_WEIGHTS
    overall = (
        skills_score * weights["skills"]
        + experience_score * weights["experience"]
        + education_score * weights["education"]
        + projects_score * weights["projects"]
    )

    return MatchScoreBreakdown(
        skills_score=skills_score,
        experience_score=experience_score,
        education_score=education_score,
        projects_score=projects_score,
        overall_score=round(overall, 1),
    )


def compute_ats_score(
    parsed_resume: ParsedResume, jd_text: str, comparison: SkillComparison
) -> ATSResult:
    """
    Compute an ATS-style score based on:
      - keyword matching (JD keywords found in resume)
      - resume structure completeness (key sections present)
      - required skills coverage
      - experience relevance to JD
    """
    jd_tokens = set(_tokenize(jd_text))
    resume_tokens = set(_tokenize(parsed_resume.raw_text))
    keyword_score = 0.0
    if jd_tokens:
        keyword_score = round((len(jd_tokens & resume_tokens) / len(jd_tokens)) * 100, 1)

    required_sections = {
        "Contact Info": bool(parsed_resume.email or parsed_resume.phone),
        "Education": bool(parsed_resume.education),
        "Experience": bool(parsed_resume.experience),
        "Skills": bool(parsed_resume.skills_list or parsed_resume.skills_section),
        "Projects": bool(parsed_resume.projects),
    }
    present = sum(1 for ok in required_sections.values() if ok)
    structure_score = round((present / len(required_sections)) * 100, 1)
    missing_sections = [name for name, ok in required_sections.items() if not ok]

    skills_coverage_score = round(comparison.match_ratio * 100, 1)

    experience_relevance_score = round(
        cosine_similarity(parsed_resume.experience, jd_text) * 100, 1
    )

    overall = round(
        keyword_score * 0.35
        + structure_score * 0.20
        + skills_coverage_score * 0.30
        + experience_relevance_score * 0.15,
        1,
    )

    return ATSResult(
        keyword_score=keyword_score,
        structure_score=structure_score,
        skills_coverage_score=skills_coverage_score,
        experience_relevance_score=experience_relevance_score,
        overall_ats_score=overall,
        missing_sections=missing_sections,
    )
