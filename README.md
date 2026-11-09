# 🧠 AI Resume Analyzer

A production-quality, AI-powered recruitment assistant that analyzes resumes, extracts
structured candidate information, compares them against a Job Description (JD),
generates a weighted Match Score and ATS Score, identifies missing skills, and provides
AI-generated recommendations — all wrapped in a premium, glassmorphism-styled Streamlit
dashboard with a built-in "Chat With Resume" AI assistant.

---

## 1. Project Overview

Recruiters and job seekers both spend a lot of time manually comparing resumes to job
descriptions. This project automates that process end-to-end:

1. A candidate uploads a resume (PDF).
2. A recruiter/job seeker pastes or uploads a Job Description.
3. The system extracts structured resume information, compares required vs. available
   skills, computes a weighted match score and an ATS-style score, and uses an LLM
   (via OpenRouter) to generate a professional summary, strengths, weaknesses, and
   improvement suggestions.
4. Users can then "chat" with an AI assistant that answers questions strictly grounded
   in the uploaded resume and JD.

## 2. Problem Statement

Manually screening resumes against job requirements is slow, inconsistent, and prone to
missing relevant candidates due to keyword mismatches or unclear formatting. This
project builds an AI/NLP-powered tool that standardizes and speeds up that evaluation,
giving both recruiters and candidates clear, actionable, data-backed insights.

## 3. Features

- 📄 **PDF Resume Upload** with validation and robust text extraction (PyMuPDF).
- 🎯 **Job Description Input** — paste text or upload a PDF/TXT file.
- 🪪 **Resume Information Extraction** — name, email, phone, education, experience,
  skills, projects, certifications, LinkedIn/GitHub links.
- 🧩 **Skill Extraction & Comparison** — keyword/alias-based skill detection across 6
  categories (Programming, AI/ML, Data, Web, Cloud/DevOps, Databases, Soft Skills),
  with Matched / Missing / Recommended skill visualizations.
- 📊 **Weighted Resume Match Score** — Skills 50% + Experience 20% + Education 15% +
  Projects 15%, shown as an animated circular progress gauge.
- ✅ **ATS Resume Score** — based on keyword matching, resume structure completeness,
  skills coverage, and experience relevance.
- 🤖 **AI Resume Analysis** (OpenRouter LLM) — professional summary, strengths,
  weaknesses, improvement suggestions, and missing-skill career advice.
- 💬 **Chat With Resume** — a grounded chatbot (chat-bubble UI + suggested questions)
  that answers questions using only the uploaded resume/JD as context.
- 🎨 **Premium Dashboard UI** — glassmorphism cards, dark/light theme toggle, circular
  progress gauges, skill badges, animated feedback, fully responsive layout.
- 🗄️ **Database Layer** — PostgreSQL-ready (via `DATABASE_URL`) for sessions, resume
  records, and analysis history, with an automatic local SQLite fallback so the app
  always runs, even without Postgres configured.
- 🛡️ **Robust Error Handling** — invalid/corrupt PDFs, empty JD, missing API key,
  API failures, and database connection issues are all handled gracefully.

## 4. Technologies Used

| Layer          | Technology                                   |
|----------------|-----------------------------------------------|
| Frontend       | Streamlit + custom CSS (glassmorphism)        |
| Backend        | Python 3.10+, modular architecture            |
| AI             | OpenRouter API (any hosted LLM, e.g. GPT-4o-mini, Gemini, Llama, Claude) |
| PDF Processing | PyMuPDF (`fitz`)                              |
| Database       | PostgreSQL (via SQLAlchemy) with SQLite fallback |
| NLP            | Keyword/alias skill extraction, regex-based section parsing, TF cosine similarity |

## 5. AI / NLP Techniques

- **Text preprocessing** — whitespace normalization, unicode cleanup (`utils/helpers.py`).
- **Information extraction** — regex-based extraction of emails, phone numbers,
  LinkedIn/GitHub URLs, and section-header based segmentation for
  education/experience/skills/projects/certifications (`resume_parser.py`).
- **Keyword-based skill extraction** — a curated, alias-aware skill dictionary spanning
  6 categories, matched against resume and JD text with word-boundary safe regex
  (`skill_extractor.py`).
- **Semantic similarity comparison** — a lightweight TF (term-frequency) cosine
  similarity implementation, used to score how closely resume sections (experience,
  education, projects) align with the job description (`scoring_engine.py`).
- **AI-powered recommendation generation** — structured JSON prompting against an LLM
  via OpenRouter to produce a grounded summary, strengths, weaknesses, and suggestions
  (`ai_analyzer.py`), plus a context-grounded chatbot (`chatbot.py`).

## 6. Architecture Explanation

**AI Workflow / Pipeline:**

```
User Upload Resume (PDF)
        ↓
PDF Text Extraction            → app/modules/pdf_processor.py
        ↓
Text Cleaning                  → utils/helpers.py
        ↓
Information Extraction         → app/modules/resume_parser.py
        ↓
Skill Extraction                → app/modules/skill_extractor.py
        ↓
JD Comparison                  → app/modules/skill_extractor.py (compare_resume_to_jd)
        ↓
Scoring Engine                 → app/modules/scoring_engine.py (Match Score + ATS Score)
        ↓
OpenRouter AI Analysis          → app/modules/ai_analyzer.py
        ↓
Dashboard Results + Chatbot     → app/main.py (Streamlit UI) + app/modules/chatbot.py
        ↓
Persisted to Database           → database/db.py + database/models.py
```

Each stage is a pure, independently testable module — `main.py` only orchestrates the
pipeline and renders the UI; it contains no business logic itself.

## 7. Folder Structure Explanation

```
resume-analyzer/
│
├── app/
│   ├── main.py                  # Streamlit UI + pipeline orchestration
│   ├── config.py                # Env vars, constants, scoring weights
│   ├── assets/
│   │   └── style.css            # Glassmorphism dark/light theme CSS
│   │
│   └── modules/
│       ├── pdf_processor.py     # PDF validation + text extraction (PyMuPDF)
│       ├── skill_extractor.py   # Skill dictionary + resume/JD comparison
│       ├── resume_parser.py     # Structured info extraction (regex + sections)
│       ├── scoring_engine.py    # Weighted Match Score + ATS Score + similarity
│       ├── ai_analyzer.py       # OpenRouter API calls for AI analysis
│       └── chatbot.py           # Chat session manager for "Chat With Resume"
│
├── database/
│   ├── db.py                    # SQLAlchemy engine, Postgres + SQLite fallback, CRUD
│   └── models.py                # ORM models: UserSession, ResumeRecord, AnalysisHistory
│
├── utils/
│   └── helpers.py               # Text cleaning, validation, formatting helpers
│
├── uploads/                     # Uploaded resumes are locally saved here
├── data/                        # Local SQLite fallback DB lives here
│
├── requirements.txt
├── .env.example
├── README.md
└── .gitignore
```

## 8. Installation Steps

```bash
# 1. Clone or unzip the project
cd resume-analyzer

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

> **Note:** `psycopg2-binary` requires no extra system setup on most platforms. If you
> don't plan to use PostgreSQL, you can remove it from `requirements.txt` — the app
> will automatically use its local SQLite fallback instead.

## 9. Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in:
   - `OPENROUTER_API_KEY` — get a free/paid key at https://openrouter.ai/keys
   - `OPENROUTER_MODEL` — any model slug available on OpenRouter (default:
     `openai/gpt-4o-mini`)
   - `DATABASE_URL` — (optional) your PostgreSQL connection string, e.g.
     `postgresql+psycopg2://postgres:password@localhost:5432/resume_analyzer`.
     Leave empty to use the automatic local SQLite fallback.

The `.env` file must sit in the **project root** (same folder as `requirements.txt`).

## 10. Running Instructions

```bash
streamlit run app/main.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`) in your browser.

**Basic usage:**
1. Upload a resume PDF in the "Upload Resume" card.
2. Paste or upload the Job Description.
3. Click **🚀 Analyze Resume**.
4. Explore the dashboard: overview, match/ATS scores, skills comparison, AI analysis.
5. Use the **Chat With Resume** section to ask follow-up questions.
6. Toggle **Dark/Light mode** from the sidebar at any time.

## 11. Challenges Faced and Solutions

| Challenge | Solution |
|---|---|
| Resumes have wildly inconsistent formatting, making section detection hard | Used a header-alias dictionary (`SECTION_HEADERS`) matched against short standalone lines, which handles the vast majority of real-world resume templates without needing a heavy NER model. |
| Multi-word skills (e.g. "machine learning", "power bi") are easy to miss with naive keyword search | Built an alias-based skill dictionary with word-boundary-safe regex matching so variations and abbreviations are captured. |
| Avoiding a heavy ML dependency for "semantic similarity" while keeping the app fast and simple to install | Implemented a lightweight TF cosine-similarity function from scratch (no scikit-learn/embedding model required) that still meaningfully scores textual overlap between resume sections and the JD. |
| The AI must not hallucinate scores/analysis | All LLM prompts are strictly grounded: the model is only given the actual extracted resume/JD text and matched/missing skills, and is instructed to return structured JSON so the UI can render it reliably. |
| The app must run even without PostgreSQL configured (for grading/demo purposes) | `database/db.py` attempts a Postgres connection first and transparently falls back to a local SQLite file (`data/local_fallback.db`) on any failure, with zero code changes required elsewhere. |
| Making Streamlit — which is normally very "default-looking" — feel like a premium SaaS product | Wrote a full custom CSS theme (`app/assets/style.css`) with glassmorphism cards, CSS-variable-based dark/light theming, custom buttons, SVG circular progress gauges, and a chat-bubble UI, all injected via `st.markdown(..., unsafe_allow_html=True)`. |

## 12. Future Improvements

- Swap the TF cosine-similarity module for sentence-transformer embeddings for deeper
  semantic matching.
- Add spaCy-based Named Entity Recognition as an alternative/complementary extraction
  path to the current regex + section-header approach.
- Support batch analysis of multiple resumes against a single JD, with a ranked
  leaderboard view.
- Add resume rewriting/export (auto-generate an improved resume PDF/Word doc).
- Add authenticated multi-user accounts (currently sessions are anonymous, per browser
  session token).
- Add unit + integration test suite (pytest) for all modules.

---

## Sample Test Data

### Sample Job Description (paste into the JD box)

```
We are hiring a Python Developer with strong experience in Machine Learning,
SQL, FastAPI, Docker, and AWS. Experience building RAG (Retrieval-Augmented
Generation) systems is a strong plus. Bachelor's degree in Computer Science
or a related field required. 1-2 years of experience preferred.
```

### Sample Resume Snippet (paste into a PDF, or use your own resume)

```
John Doe
john.doe@email.com
+1 555-123-4567
linkedin.com/in/johndoe

Education
BS in Computer Science, FAST University, 2022-2026

Experience
Software Engineering Intern at TechCorp
Worked on Python backend services and REST APIs using FastAPI.
Built machine learning pipelines using scikit-learn and pandas.

Skills
Python, SQL, Machine Learning, FastAPI, Docker, Git

Projects
Built a RAG chatbot using LangChain and OpenAI API for a university helpdesk.

Certifications
AWS Certified Cloud Practitioner
```

### Sample Chatbot Questions to Try

- "What are my strongest skills?"
- "Which skills should I learn to better match this job?"
- "How can I improve my ATS score?"
- "Am I suitable for this job based on my experience?"

---

## Where to Place API Keys / Configuration

| Setting | File | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | `.env` (project root) | Required for all AI features (analysis + chatbot). Without it, the rest of the app (scores, skill extraction) still works; AI sections show a clear warning instead. |
| `OPENROUTER_MODEL` | `.env` | Any valid OpenRouter model slug. |
| `DATABASE_URL` | `.env` | Optional. Leave blank to use the automatic SQLite fallback. |

---

Built for the **Axorvian Internship Program — Task 3: AI Resume Analyzer**.
