"""
main.py
-------
Streamlit entry point for the AI Resume Analyzer — a premium, glassmorphism
styled AI SaaS-style dashboard for resume vs. job-description analysis.

Run with:  streamlit run app/main.py
"""

import sys
import uuid
from pathlib import Path

import streamlit as st

# Make the project root importable when running via `streamlit run app/main.py`
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import APP_ICON, APP_TAGLINE, APP_TITLE, MAX_FILE_SIZE_MB, UPLOAD_DIR
from app.modules.ai_analyzer import AIAnalysisError, generate_resume_analysis
from app.modules.chatbot import SUGGESTED_QUESTIONS, ResumeChatSession
from app.modules.pdf_processor import PDFProcessingError, extract_text_from_optional_source, extract_text_from_pdf
from app.modules.resume_parser import parse_resume
from app.modules.scoring_engine import compute_ats_score, compute_match_score
from app.modules.skill_extractor import compare_resume_to_jd, recommend_skills_to_learn
from utils.helpers import safe_filename

try:
    from database.db import (
        get_active_backend,
        get_history_for_session,
        get_or_create_session,
        init_db,
        save_analysis_record,
        save_resume_record,
    )
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


# =============================================================================
# PAGE CONFIG + THEME
# =============================================================================
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "session_token" not in st.session_state:
    st.session_state.session_token = str(uuid.uuid4())
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "parsed_resume" not in st.session_state:
    st.session_state.parsed_resume = None
if "db_session_id" not in st.session_state:
    st.session_state.db_session_id = None


def load_css():
    css_path = Path(__file__).parent / "assets" / "style.css"
    base_css = css_path.read_text()

    if st.session_state.theme == "light":
        override = """
        :root {
          --bg-primary: #f5f6fb;
          --bg-secondary: #ffffff;
          --bg-gradient: radial-gradient(circle at 15% 0%, #eef0ff 0%, #f5f6fb 45%), radial-gradient(circle at 85% 100%, #eafcff 0%, #f5f6fb 55%);
          --glass-bg: rgba(255, 255, 255, 0.65);
          --glass-border: rgba(15, 23, 42, 0.08);
          --text-primary: #131623;
          --text-secondary: #5b6478;
          --accent: #6d4bff;
          --accent-2: #0891b2;
          --success: #059669;
          --warning: #d97706;
          --danger: #e11d48;
          --shadow: 0 8px 32px rgba(15, 23, 42, 0.08);
          --input-bg: rgba(15,23,42,0.04);
        }
        """
    else:
        override = ""

    st.markdown(f"<style>{base_css}\n{override}</style>", unsafe_allow_html=True)


load_css()

if DB_AVAILABLE and st.session_state.db_session_id is None:
    try:
        init_db()
        st.session_state.db_session_id = get_or_create_session(st.session_state.session_token)
    except Exception:
        DB_AVAILABLE_RUNTIME = False


# =============================================================================
# SMALL UI HELPERS
# =============================================================================
def circular_progress(percent: float, label: str, color_var: str = "--accent") -> str:
    """Return an inline SVG ring gauge as an HTML string."""
    percent = max(0, min(100, percent))
    radius = 46
    circumference = 2 * 3.14159265 * radius
    offset = circumference * (1 - percent / 100)
    return f"""
    <div class="circle-wrap">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="{radius}" stroke="var(--glass-border)" stroke-width="10" fill="none"/>
        <circle cx="60" cy="60" r="{radius}" stroke="var({color_var})" stroke-width="10" fill="none"
          stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}"
          stroke-linecap="round" transform="rotate(-90 60 60)"/>
        <text x="60" y="66" text-anchor="middle" font-size="22" font-weight="800" fill="var(--text-primary)">{percent:.0f}%</text>
      </svg>
      <div class="circle-caption">{label}</div>
    </div>
    """


def metric_card(value: str, label: str) -> str:
    return f"""
    <div class="metric-card">
      <div class="metric-value">{value}</div>
      <div class="metric-label">{label}</div>
    </div>
    """


def skill_badges(skills, css_class: str, symbol: str) -> str:
    if not skills:
        return f'<span style="color: var(--text-secondary); font-size:14px;">None found</span>'
    return "".join(
        f'<span class="skill-badge {css_class}">{symbol} {s.title()}</span>' for s in sorted(skills)
    )


# (Chat bubbles are rendered natively via st.chat_message further below —
# no custom HTML renderer needed, which also avoids the empty-div bug.)


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown(f"### {APP_ICON} {APP_TITLE}")
    st.caption(APP_TAGLINE)
    st.divider()

    theme_choice = st.radio(
        "🎨 Theme", ["Dark", "Light"],
        index=0 if st.session_state.theme == "dark" else 1,
        horizontal=True,
    )
    new_theme = theme_choice.lower()
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.divider()
    st.markdown("#### ⚙️ Status")
    if DB_AVAILABLE:
        try:
            backend = get_active_backend()
        except Exception:
            backend = "not initialized"
        st.caption(f"Database: `{backend}`")
    else:
        st.caption("Database: unavailable")

    from app.config import OPENROUTER_API_KEY
    st.caption(f"AI Engine: {'🟢 OpenRouter connected' if OPENROUTER_API_KEY else '🔴 API key missing'}")

    st.divider()
    if st.session_state.parsed_resume and DB_AVAILABLE:
        st.markdown("#### 🕘 Recent Analyses")
        try:
            history = get_history_for_session(st.session_state.session_token)
            if history:
                for h in history[:5]:
                    st.caption(f"{h['file_name']} — Match {h['match_score']}% • ATS {h['ats_score']}%")
            else:
                st.caption("No previous analyses yet.")
        except Exception:
            st.caption("History unavailable.")


# =============================================================================
# HERO HEADER
# =============================================================================
st.markdown(
    f"""
    <div class="hero-header">
      <div>
        <p class="brand-title">{APP_ICON} {APP_TITLE}</p>
        <p class="brand-tagline">{APP_TAGLINE}</p>
      </div>
      <div class="badge-pill">✨ Powered by OpenRouter AI</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# UPLOAD + JD SECTION
# =============================================================================
col_upload, col_jd = st.columns([1, 1])

with col_upload:
    st.markdown('<div class="section-title">📄 Upload Resume</div>', unsafe_allow_html=True)
    uploaded_resume = st.file_uploader(
        "Drag & drop your resume PDF here", type=["pdf"], key="resume_uploader"
    )
    if uploaded_resume:
        st.success(f"✅ **{uploaded_resume.name}** ready for analysis")

with col_jd:
    st.markdown('<div class="section-title">🎯 Job Description</div>', unsafe_allow_html=True)
    jd_input_mode = st.radio("Provide JD via:", ["Paste text", "Upload file"], horizontal=True, label_visibility="collapsed")
    jd_text_input, jd_file = "", None
    if jd_input_mode == "Paste text":
        jd_text_input = st.text_area("Paste the job description", height=170, placeholder="Paste the full job description here...")
    else:
        jd_file = st.file_uploader("Upload JD (PDF or TXT)", type=["pdf", "txt"], key="jd_uploader")

analyze_clicked = st.button("🚀 Analyze Resume", use_container_width=True)

# =============================================================================
# ANALYSIS PIPELINE
# =============================================================================
if analyze_clicked:
    if not uploaded_resume:
        st.error("⚠️ Please upload a resume PDF before analyzing.")
    else:
        try:
            resume_bytes = uploaded_resume.getvalue()
            with st.spinner("🔍 Extracting resume text..."):
                extracted = extract_text_from_pdf(resume_bytes, uploaded_resume.name)

            jd_file_bytes = jd_file.getvalue() if jd_file else None
            jd_file_name = jd_file.name if jd_file else None
            with st.spinner("📋 Reading job description..."):
                jd_text = extract_text_from_optional_source(jd_file_bytes, jd_file_name, jd_text_input)

            with st.spinner("🧠 Parsing resume structure..."):
                parsed = parse_resume(extracted.text)

            with st.spinner("🔗 Comparing skills..."):
                comparison = compare_resume_to_jd(extracted.text, jd_text)

            with st.spinner("📊 Calculating match & ATS scores..."):
                match_breakdown = compute_match_score(parsed, jd_text, comparison)
                ats_result = compute_ats_score(parsed, jd_text, comparison)

            ai_result, ai_error = None, None
            with st.spinner("✨ Generating AI-powered insights..."):
                try:
                    ai_result = generate_resume_analysis(
                        extracted.text, jd_text, list(comparison.matched), list(comparison.missing)
                    )
                except AIAnalysisError as exc:
                    ai_error = str(exc)

            # Persist uploaded file locally
            safe_name = safe_filename(uploaded_resume.name)
            (UPLOAD_DIR / safe_name).write_bytes(resume_bytes)

            # Save to session state
            st.session_state.parsed_resume = parsed
            st.session_state.resume_text = extracted.text
            st.session_state.jd_text = jd_text
            st.session_state.comparison = comparison
            st.session_state.match_breakdown = match_breakdown
            st.session_state.ats_result = ats_result
            st.session_state.ai_result = ai_result
            st.session_state.ai_error = ai_error
            st.session_state.chat_session = ResumeChatSession(resume_text=extracted.text, jd_text=jd_text)
            st.session_state.file_name = uploaded_resume.name

            # Persist to DB (best-effort, never blocks the UI)
            if DB_AVAILABLE and st.session_state.db_session_id:
                try:
                    resume_id = save_resume_record(st.session_state.db_session_id, uploaded_resume.name, parsed)
                    save_analysis_record(
                        resume_id,
                        jd_text,
                        match_breakdown.overall_score,
                        ats_result.overall_ats_score,
                        comparison.matched,
                        comparison.missing,
                        ai_result.summary if ai_result else "",
                    )
                except Exception:
                    pass

            st.success("✅ Analysis complete! Scroll down to view your dashboard.")
        except PDFProcessingError as exc:
            st.error(f"⚠️ {exc}")
        except Exception as exc:
            st.error(f"❌ Unexpected error during analysis: {exc}")


# =============================================================================
# RESULTS DASHBOARD
# =============================================================================
if st.session_state.get("parsed_resume"):
    parsed = st.session_state.parsed_resume
    comparison = st.session_state.comparison
    match_breakdown = st.session_state.match_breakdown
    ats_result = st.session_state.ats_result
    ai_result = st.session_state.ai_result
    ai_error = st.session_state.get("ai_error")

    st.markdown("---")

    # ---------------- Resume Overview ----------------
    st.markdown('<div class="section-title">🪪 Resume Overview</div>', unsafe_allow_html=True)
    ov1, ov2, ov3, ov4 = st.columns(4)
    ov1.markdown(f"**👤 Name**\n\n{parsed.name or 'Not detected'}")
    ov2.markdown(f"**📧 Email**\n\n{parsed.email or 'Not detected'}")
    ov3.markdown(f"**📞 Phone**\n\n{parsed.phone or 'Not detected'}")
    ov4.markdown(f"**🔗 Links**\n\n{parsed.linkedin or parsed.github or 'Not detected'}")

    # ---------------- Analytics Cards ----------------
    st.markdown('<div class="section-title">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.markdown(
            f'<div class="glass-card">{circular_progress(match_breakdown.overall_score, "Match Score", "--accent")}</div>',
            unsafe_allow_html=True,
        )
    with a2:
        st.markdown(
            f'<div class="glass-card">{circular_progress(ats_result.overall_ats_score, "ATS Score", "--accent-2")}</div>',
            unsafe_allow_html=True,
        )
    with a3:
        total_jd = len(comparison.jd_skills) or 1
        st.markdown(
            f'<div class="glass-card">{metric_card(f"{len(comparison.matched)}/{total_jd}", "Skills Matched")}</div>',
            unsafe_allow_html=True,
        )
    with a4:
        st.markdown(
            f'<div class="glass-card">{metric_card(f"{match_breakdown.experience_score:.0f}%", "Experience Match")}</div>',
            unsafe_allow_html=True,
        )

    with st.expander("📈 View detailed score breakdown"):
        st.markdown("**Resume Match Score components**")
        st.progress(match_breakdown.skills_score / 100, text=f"Skills Match — {match_breakdown.skills_score:.0f}%")
        st.progress(match_breakdown.experience_score / 100, text=f"Experience Match — {match_breakdown.experience_score:.0f}%")
        st.progress(match_breakdown.education_score / 100, text=f"Education Match — {match_breakdown.education_score:.0f}%")
        st.progress(match_breakdown.projects_score / 100, text=f"Projects Match — {match_breakdown.projects_score:.0f}%")
        st.markdown("**ATS Score components**")
        st.progress(ats_result.keyword_score / 100, text=f"Keyword Matching — {ats_result.keyword_score:.0f}%")
        st.progress(ats_result.structure_score / 100, text=f"Resume Structure — {ats_result.structure_score:.0f}%")
        st.progress(ats_result.skills_coverage_score / 100, text=f"Skills Coverage — {ats_result.skills_coverage_score:.0f}%")
        st.progress(ats_result.experience_relevance_score / 100, text=f"Experience Relevance — {ats_result.experience_relevance_score:.0f}%")
        if ats_result.missing_sections:
            st.warning(f"Missing/undetected resume sections: {', '.join(ats_result.missing_sections)}")

    # ---------------- Skills Visualization ----------------
    st.markdown('<div class="section-title">🧩 Skills Comparison</div>', unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f'<div class="glass-card"><h4>✅ Matched Skills</h4>{skill_badges(comparison.matched, "skill-matched", "✓")}</div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f'<div class="glass-card"><h4>⚠️ Missing Skills</h4>{skill_badges(comparison.missing, "skill-missing", "✗")}</div>',
            unsafe_allow_html=True,
        )
    with s3:
        recommended = recommend_skills_to_learn(comparison)
        st.markdown(
            f'<div class="glass-card"><h4>💡 Recommended to Learn</h4>{skill_badges(recommended, "skill-recommend", "★")}</div>',
            unsafe_allow_html=True,
        )

    # ---------------- AI Analysis ----------------
    st.markdown('<div class="section-title">🤖 AI Resume Analysis</div>', unsafe_allow_html=True)
    if ai_error:
        st.warning(f"⚠️ AI analysis unavailable: {ai_error}")
    elif ai_result:
        with st.expander("📝 Professional Summary", expanded=True):
            st.write(ai_result.summary or "No summary generated.")
        with st.expander("💪 Resume Strengths"):
            for item in ai_result.strengths or ["No strengths generated."]:
                st.markdown(f"- {item}")
        with st.expander("🔧 Resume Weaknesses"):
            for item in ai_result.weaknesses or ["No weaknesses generated."]:
                st.markdown(f"- {item}")
        with st.expander("🚀 Improvement Suggestions"):
            for item in ai_result.suggestions or ["No suggestions generated."]:
                st.markdown(f"- {item}")
        with st.expander("🎯 Career Recommendations / Missing Skill Advice"):
            st.write(ai_result.missing_skill_advice or "No additional advice generated.")

    # ---------------- Chatbot ----------------
    st.markdown('<div class="section-title">💬 Chat With Your Resume</div>', unsafe_allow_html=True)

    chat_session: ResumeChatSession = st.session_state.chat_session

    if not chat_session.history:
        st.caption(
            "Ask a quick question below, or type your own — answers are grounded "
            "only in your resume and the job description."
        )
        chip_cols = st.columns(len(SUGGESTED_QUESTIONS))
        suggested_clicked = None
        for i, q in enumerate(SUGGESTED_QUESTIONS):
            if chip_cols[i].button(q, key=f"suggested_{i}"):
                suggested_clicked = q
        if suggested_clicked:
            with st.spinner("Thinking..."):
                chat_session.ask(suggested_clicked)
            st.rerun()
    else:
        for msg in chat_session.history:
            avatar = "🧑‍💻" if msg.role == "user" else "🤖"
            with st.chat_message(msg.role, avatar=avatar):
                st.markdown(msg.content)

    user_question = st.chat_input("Ask something about your resume or the job fit...")
    if user_question:
        with st.spinner("Thinking..."):
            chat_session.ask(user_question)
        st.rerun()

else:
    st.info("👆 Upload a resume and provide a job description, then click **Analyze Resume** to see your AI-powered dashboard.")

st.markdown(
    '<p style="text-align:center; color: var(--text-secondary); font-size: 12px; margin-top: 30px;">'
    "AI Resume Analyzer • Built with Streamlit & OpenRouter</p>",
    unsafe_allow_html=True,
)
