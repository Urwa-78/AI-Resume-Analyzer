"""
chatbot.py
----------
Conversation manager for the "Chat With Resume" feature. Keeps track of
message history and delegates the actual generation to ai_analyzer, so the
Streamlit UI layer stays clean and only deals with rendering chat bubbles.
"""

from dataclasses import dataclass, field
from typing import List

from app.modules.ai_analyzer import AIAnalysisError, answer_chat_question

SUGGESTED_QUESTIONS = [
    "What are my strongest skills?",
    "Which skills should I learn?",
    "How can I improve this resume?",
    "Am I suitable for this job?",
    "How can I improve my ATS score?",
    "Summarize my experience in 2 lines.",
]


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class ResumeChatSession:
    resume_text: str
    jd_text: str = ""
    history: List[ChatMessage] = field(default_factory=list)

    def as_api_history(self) -> List[dict]:
        return [{"role": m.role, "content": m.content} for m in self.history]

    def ask(self, question: str) -> str:
        """Send a question to the LLM, grounded in resume/JD context, and
        append both the question and answer to the running history."""
        self.history.append(ChatMessage(role="user", content=question))
        try:
            answer = answer_chat_question(
                question=question,
                resume_text=self.resume_text,
                jd_text=self.jd_text,
                chat_history=self.as_api_history()[:-1],
            )
        except AIAnalysisError as exc:
            answer = f"⚠️ {exc}"
        self.history.append(ChatMessage(role="assistant", content=answer))
        return answer
