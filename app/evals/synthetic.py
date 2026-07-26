"""Deterministic synthetic eval-data generation."""

from __future__ import annotations

from app.rag.retrieval.vector_store import ChunkRecord


def generate_synthetic_eval_dataset(records: list[ChunkRecord]) -> dict:
    examples = []
    for record in records:
        first_sentence = record.text.split(".")[0].strip()
        if not first_sentence:
            continue
        examples.append(
            {
                "question": f"What does the documentation say about {record.title}?",
                "paraphrases": [
                    f"Explain {record.title}.",
                    f"Summarize the guidance for {record.title}.",
                ],
                "expected_answer": first_sentence,
                "citation_labels": [record.chunk_id],
                "hard_negative": f"This answer is unrelated to {record.title}.",
                "should_escalate": False,
            }
        )
    examples.append(
        {
            "question": "Can you configure unrelated payroll software?",
            "paraphrases": ["Help me with my payroll vendor."],
            "expected_answer": "",
            "citation_labels": [],
            "hard_negative": "",
            "should_escalate": True,
        }
    )
    return {"num_examples": len(examples), "examples": examples}
