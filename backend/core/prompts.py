"""System prompt factory and OpenAI message assembler for the RAG chat endpoint."""
from __future__ import annotations

_SYSTEM_TEMPLATE = """\
You are a literary assistant for a book publishing company.
Active scope: {scope_label}

Answer questions using ONLY the retrieved passages provided at the end of this conversation.
For every claim, cite the book title and chapter.
If the passages do not contain enough information to answer, say so clearly.
Do not use any knowledge outside the provided passages.
"""


def build_system_prompt(scope_label: str) -> str:
    return _SYSTEM_TEMPLATE.format(scope_label=scope_label)


def build_messages(
    system_prompt: str,
    history: list[dict],
    context_chunks: list[dict],
    scope_label: str = "",
) -> list[dict]:
    """Assemble the full OpenAI messages array.

    Order:
    1. System message (exactly system_prompt, unchanged)
    2. All history turns except the last, each tagged with [asked under: scope_label]
    3. The current question (history[-1]) — passed through unmodified
    4. A trailing user message containing the formatted context passages
    """
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    tag = f"\n[asked under: {scope_label}]" if scope_label else ""

    for turn in history[:-1]:
        messages.append({**turn, "content": turn["content"] + tag})

    if history:
        messages.append(history[-1])

    if context_chunks:
        lines = []
        for i, chunk in enumerate(context_chunks):
            book = chunk.get("book_title", "")
            chapter = chunk.get("chapter_title", "")
            text = chunk.get("text", "")
            lines.append(f'[CHUNK {i + 1}] Book: {book} | {chapter}\n"{text}"')
        messages.append({"role": "user", "content": "\n\n".join(lines)})

    return messages
