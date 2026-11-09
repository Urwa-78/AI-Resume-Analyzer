"""
models.py
---------
SQLAlchemy ORM models for the AI Resume Analyzer's database layer.

Tables:
  - UserSession: one row per app session (anonymous, session-token based).
  - ResumeRecord: metadata + extracted text for each uploaded resume.
  - AnalysisHistory: stores each analysis run (scores + AI results) so a
    user can review previous analyses.
"""

import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    resumes = relationship("ResumeRecord", back_populates="session", cascade="all, delete-orphan")


class ResumeRecord(Base):
    __tablename__ = "resume_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False)
    file_name = Column(String(255))
    candidate_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    raw_text = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("UserSession", back_populates="resumes")
    analyses = relationship("AnalysisHistory", back_populates="resume", cascade="all, delete-orphan")


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resume_records.id"), nullable=False)
    jd_text = Column(Text, nullable=True)
    match_score = Column(Float, nullable=True)
    ats_score = Column(Float, nullable=True)
    matched_skills = Column(Text, nullable=True)   # comma-separated
    missing_skills = Column(Text, nullable=True)   # comma-separated
    ai_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    resume = relationship("ResumeRecord", back_populates="analyses")
