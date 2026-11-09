"""
ai_analyzer.py
--------------
Wraps calls to the OpenRouter API (https://openrouter.ai) to generate:
  - Professional candidate summary
  - Resume strengths / weaknesses
  - Improvement suggestions & missing-skill recommendations

All prompts are grounded in the actual extracted resume text and job
description, so responses stay factual and specific to the candidate.
"""

import json
from dataclasses import dataclass
from typing import List, Optional

import requests

from app.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_SITE_NAME,
    OPENROUTER_SITE_URL,
)
from utils.helpers import truncate


class AIAnalysisError(Exception):
    """Raised when the OpenRouter API call fails or the key is missing."""


@dataclass
class AIAnalysisResult:
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    missing_skill_advice: str


def _require_api_key() -> None:
    if not OPENROUTER_API_KEY:
        raise AIAnalysisError(
            "OPENROUTER_API_KEY is not configured. Add it to your .env file "
            "(see .env.example) to enable AI-powered analysis."
        )


def call_openrouter(messages: list, temperature: float = 0.4, max_tokens: int = 900) -> str:
    """
    Low-level helper that sends a chat-completion request to OpenRouter
    and returns the assistant's text response.
    """
    _require_api_key()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_SITE_NAME,
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(
            OPENROUTER_BASE_URL, headers=headers, data=json.dumps(payload), timeout=60
        )
    except requests.exceptions.RequestException as exc:
        raise AIAnalysisError(f"Network error while calling OpenRouter: {exc}") from exc

    if response.status_code == 401:
        raise AIAnalysisError("Invalid OpenRouter API key. Please check your .env file.")
    if response.status_code == 429:
        raise AIAnalysisError("OpenRouter rate limit reached. Please try again shortly.")
    if response.status_code >= 400:
        raise AIAnalysisError(
            f"OpenRouter API error ({response.status_code}): {response.text[:300]}"
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise AIAnalysisError(f"Unexpected OpenRouter response format: {exc}") from exc


def _parse_json_block(raw: str) -> dict:
    """Extract and parse a JSON object even if the model wraps it in prose/fences."""
    cleaned = raw.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```")[1] if cleaned.count("```") >= 2 else cleaned
        cleaned = cleaned.replace("json", "", 1).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def generate_resume_analysis(
    resume_text: str,
    jd_text: str,
    matched_skills: List[str],
    missing_skills: List[str],
) -> AIAnalysisResult:
    """
    Ask the LLM for a structured analysis: summary, strengths, weaknesses,
    improvement suggestions, and missing-skill advice. Requests strict JSON
    output for reliable parsing in the UI.
    """
    system_prompt = (
        "You are an expert technical recruiter and career coach. Analyze the "
        "candidate's resume against the job description and respond ONLY with "
        "a valid JSON object (no markdown fences, no extra commentary) using "
        "exactly this schema: {\"summary\": string, \"strengths\": [string], "
        "\"weaknesses\": [string], \"suggestions\": [string], "
        "\"missing_skill_advice\": string}. Keep each list to 3-5 concise, "
        "specific, actionable bullet points grounded in the actual resume text."
    )

    user_prompt = f"""
JOB DESCRIPTION:
{truncate(jd_text, 3000)}

CANDIDATE RESUME:
{truncate(resume_text, 4000)}

MATCHED SKILLS: {', '.join(matched_skills) or 'None detected'}
MISSING SKILLS (required by JD but absent from resume): {', '.join(missing_skills) or 'None'}

Provide the JSON analysis now.
"""

    raw = call_openrouter(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    try:
        parsed = _parse_json_block(raw)
    except (json.JSONDecodeError, ValueError):
        # Graceful fallback: return the raw text as the summary so the user
        # still sees useful output even if strict JSON parsing failed.
        return AIAnalysisResult(
            summary=raw,
            strengths=[],
            weaknesses=[],
            suggestions=[],
            missing_skill_advice="",
        )

    return AIAnalysisResult(
        summary=parsed.get("summary", ""),
        strengths=parsed.get("strengths", []) or [],
        weaknesses=parsed.get("weaknesses", []) or [],
        suggestions=parsed.get("suggestions", []) or [],
        missing_skill_advice=parsed.get("missing_skill_advice", ""),
    )


def answer_chat_question(
    question: str,
    resume_text: str,
    jd_text: Optional[str],
    chat_history: Optional[List[dict]] = None,
) -> str:
    """
    Answer a user's question about the resume (and optionally the JD),
    strictly grounded in the provided context, for the "Chat with Resume"
    feature.
    """
    system_prompt = (
        "You are a helpful AI career assistant embedded in a resume analyzer "
        "tool. Answer the user's question using ONLY the resume text (and job "
        "description, if provided) given below as context. Be specific, "
        "concise, and actionable. If the answer cannot be determined from the "
        "provided context, say so honestly instead of inventing details."
    )

    context = f"RESUME:\n{truncate(resume_text, 4000)}\n\n"
    if jd_text:
        context += f"JOB DESCRIPTION:\n{truncate(jd_text, 2500)}\n\n"

    messages = [{"role": "system", "content": system_prompt + "\n\n" + context}]
    for turn in (chat_history or [])[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})

    return call_openrouter(messages, temperature=0.5, max_tokens=600)
