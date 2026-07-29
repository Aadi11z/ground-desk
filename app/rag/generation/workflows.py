"""Higher-level support workflows built on top of grounded retrieval."""

from __future__ import annotations

from app.core.models import ChatRequest

from .agent import SupportAgent


class SupportWorkflowService:
    def __init__(self, agent: SupportAgent):
        self.agent = agent

    def escalation_note(self, question: str) -> dict:
        response = self.agent.answer(
            ChatRequest(question=question), force_template=True
        )
        note = (
            f"Escalation needed for query: {question}\n"
            f"Current answer confidence: {response.confidence}\n"
            f"Evidence count: {len(response.citations)}\n"
            f"Reason: {'insufficient grounded evidence' if response.needs_escalation else 'manual review requested'}"
        )
        return {"note": note, "response": response}

    def summarize_conversation(self, messages: list[str]) -> dict:
        cleaned = [message.strip() for message in messages if message.strip()]
        summary = " ".join(cleaned[-6:])
        return {
            "summary": summary[:900],
            "turns": len(cleaned),
            "open_questions": [
                message for message in cleaned if message.rstrip().endswith("?")
            ][-3:],
        }

    def faq_from_document(self, title: str, text: str) -> dict:
        sentences = [
            sentence.strip()
            for sentence in text.replace("\n", " ").split(".")
            if sentence.strip()
        ]
        faqs = []
        for sentence in sentences[:5]:
            faqs.append(
                {
                    "question": f"What should customers know about {title}?",
                    "answer": sentence + ".",
                }
            )
        return {"title": title, "faqs": faqs}

    def summarize_document(self, title: str, text: str) -> dict:
        sentences = [
            sentence.strip()
            for sentence in text.replace("\n", " ").split(".")
            if sentence.strip()
        ]
        return {
            "title": title,
            "summary": ". ".join(sentences[:3]) + ("." if sentences else ""),
        }

    def summarize_changelog(self, title: str, text: str) -> dict:
        bullets = [
            line.strip("- ").strip() for line in text.splitlines() if line.strip()
        ]
        return {
            "title": title,
            "highlights": bullets[:5],
        }

    def knowledge_gap(self, question: str) -> dict:
        response = self.agent.answer(
            ChatRequest(question=question), force_template=True
        )
        return {
            "question": question,
            "knowledge_gap": response.needs_escalation or not response.citations,
            "confidence": response.confidence,
            "supporting_citations": len(response.citations),
        }

    def suggest_support_article(self, question: str) -> dict:
        gap = self.knowledge_gap(question)
        return {
            "question": question,
            "should_draft": gap["knowledge_gap"],
            "suggested_title": f"How to resolve: {question.rstrip('?')}",
            "outline": [
                "Problem",
                "Likely causes",
                "Resolution steps",
                "When to escalate",
            ],
        }
