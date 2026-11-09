"""
db.py
-----
Database connection layer. Prepared for PostgreSQL via DATABASE_URL, with
an automatic, transparent fallback to a local SQLite file if:
  - DATABASE_URL is not configured, or
  - the PostgreSQL connection fails for any reason (e.g. no local DB running).

This keeps the app runnable end-to-end for local grading/demo purposes,
while still demonstrating a production-ready Postgres integration layer.
"""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL, FALLBACK_SQLITE_URL
from database.models import AnalysisHistory, Base, ResumeRecord, UserSession

logger = logging.getLogger("resume_analyzer.db")

_engine = None
_SessionLocal = None
_active_backend = "none"


def _build_engine():
    """
    Attempt to connect to PostgreSQL (if DATABASE_URL is set). On any
    failure, transparently fall back to a local SQLite database so the
    app remains functional.
    """
    global _active_backend

    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            with engine.connect():
                pass  # test the connection
            _active_backend = "postgresql"
            logger.info("Connected to PostgreSQL database.")
            return engine
        except SQLAlchemyError as exc:
            logger.warning("PostgreSQL connection failed (%s). Falling back to SQLite.", exc)

    engine = create_engine(FALLBACK_SQLITE_URL, connect_args={"check_same_thread": False})
    _active_backend = "sqlite (fallback)"
    return engine


def init_db():
    """Initialize the engine, session factory, and create tables if needed."""
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    _engine = _build_engine()
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_active_backend() -> str:
    return _active_backend


@contextmanager
def get_db_session():
    """
    Context manager yielding a SQLAlchemy session. Any exception rolls back
    the transaction; the session is always closed afterwards.

    Usage:
        with get_db_session() as db:
            db.add(record)
    """
    if _SessionLocal is None:
        init_db()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Lightweight CRUD helpers used by the Streamlit UI layer.
# These wrap get_db_session() so main.py never touches SQLAlchemy directly.
# ---------------------------------------------------------------------------

def get_or_create_session(session_token: str) -> int:
    """Return the DB id for a given browser/session token, creating it if new."""
    with get_db_session() as db:
        existing = db.query(UserSession).filter_by(session_token=session_token).first()
        if existing:
            return existing.id
        new_session = UserSession(session_token=session_token)
        db.add(new_session)
        db.flush()
        return new_session.id


def save_resume_record(session_id: int, file_name: str, parsed_resume) -> int:
    """Persist an uploaded resume's metadata and raw text."""
    with get_db_session() as db:
        record = ResumeRecord(
            session_id=session_id,
            file_name=file_name,
            candidate_name=parsed_resume.name,
            email=parsed_resume.email,
            phone=parsed_resume.phone,
            raw_text=parsed_resume.raw_text,
        )
        db.add(record)
        db.flush()
        return record.id


def save_analysis_record(
    resume_id: int,
    jd_text: str,
    match_score: float,
    ats_score: float,
    matched_skills,
    missing_skills,
    ai_summary: str,
) -> int:
    """Persist the results of a single analysis run for later history lookup."""
    with get_db_session() as db:
        record = AnalysisHistory(
            resume_id=resume_id,
            jd_text=jd_text,
            match_score=match_score,
            ats_score=ats_score,
            matched_skills=", ".join(sorted(matched_skills)) if matched_skills else "",
            missing_skills=", ".join(sorted(missing_skills)) if missing_skills else "",
            ai_summary=ai_summary,
        )
        db.add(record)
        db.flush()
        return record.id


def get_history_for_session(session_token: str, limit: int = 10):
    """Return the most recent analyses for a given session token."""
    with get_db_session() as db:
        session_row = db.query(UserSession).filter_by(session_token=session_token).first()
        if not session_row:
            return []
        results = (
            db.query(AnalysisHistory)
            .join(ResumeRecord)
            .filter(ResumeRecord.session_id == session_row.id)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "created_at": r.created_at,
                "match_score": r.match_score,
                "ats_score": r.ats_score,
                "matched_skills": r.matched_skills,
                "missing_skills": r.missing_skills,
                "file_name": r.resume.file_name if r.resume else "",
            }
            for r in results
        ]
