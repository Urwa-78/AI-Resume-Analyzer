"""
config.py
----------
Central configuration for the AI Resume Analyzer.
Loads environment variables (API keys, database URL) and defines
global constants used across the application (scoring weights,
skill dictionary path, model name, etc.).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from a .env file placed in the project root.
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# OpenRouter (AI) configuration
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# You can swap this for any model available on OpenRouter
# (e.g. "openai/gpt-4o-mini", "google/gemini-2.0-flash-001",
# "anthropic/claude-3.5-haiku", "meta-llama/llama-3.1-8b-instruct:free")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# Site info recommended by OpenRouter for analytics/rate-limits
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "http://localhost:8501")
OPENROUTER_SITE_NAME = os.getenv("OPENROUTER_SITE_NAME", "AI Resume Analyzer")

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------
# Example Postgres URL:
# postgresql+psycopg2://username:password@localhost:5432/resume_analyzer
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Fallback local SQLite database used automatically when DATABASE_URL is not
# configured, or when the Postgres connection fails. This keeps the app
# fully runnable out-of-the-box for local grading/demo purposes.
FALLBACK_SQLITE_URL = f"sqlite:///{BASE_DIR / 'data' / 'local_fallback.db'}"

# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE_MB = 10

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "skills": 0.50,
    "experience": 0.20,
    "education": 0.15,
    "projects": 0.15,
}

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
APP_TITLE = "AI Resume Intelligence Platform"
APP_TAGLINE = "Analyze, optimize, and match your resume with AI"
APP_ICON = "🧠"
