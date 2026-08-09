"""POST /api/chat — SSE streaming RAG pipeline."""
from __future__ import annotations

import json
import logging
import sys

import openai
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from core.citation_selection import select_citations
from core.embeddings import embed_texts
from core.prompts import build_messages, build_system_prompt
from core.query_analysis import analyze_query
from core.retrieval import retrieve

router = APIRouter()
logger = logging.getLogger(__name__)

_SCOPE_LABELS: dict[str, str] = {
    "little_women": "Little Women",
    "pride_prejudice": "Pride & Prejudice",
    "both": "both books",
}


class ChatRequest(BaseModel):
    book_id: str
    message: str
    history: list[dict] = []

    @field_validator("book_id")
    @classmethod
    def validate_book_id(cls, v: str) -> str:
        if v not in _SCOPE_LABELS:
            raise ValueError(f"book_id must be one of {sorted(_SCOPE_LABELS)}")
        return v


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/chat")
def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    openai_client = request.app.state.openai_client
    collection = request.app.state.chroma_collection
    deployment = request.app.state.openai_deployment
    scope_label = _SCOPE_LABELS[body.book_id]

    def generate():
        try:
            print(f"[chat] book_id={body.book_id!r} message={body.message[:80]!r}", file=sys.stderr)
            sub_queries = analyze_query(body.message, body.book_id, openai_client)
            print(f"[chat] sub_queries={[(sq['book_id'], sq['query'][:60]) for sq in sub_queries]}", file=sys.stderr)
            embeddings = embed_texts([sq["query"] for sq in sub_queries])
            sub_query_inputs = [
                {"query_embedding": emb, "book_id": sq["book_id"]}
                for sq, emb in zip(sub_queries, embeddings)
            ]
            context_chunks, citable = retrieve(sub_query_inputs, collection)
            print(f"[chat] retrieved {len(context_chunks)} chunks: {[(c.get('book_title','?'), c.get('chapter_title','?')) for c in context_chunks]}", file=sys.stderr)

            system_prompt = build_system_prompt(scope_label)
            messages = build_messages(
                system_prompt,
                body.history + [{"role": "user", "content": body.message}],
                context_chunks,
                scope_label,
            )

            answer_parts: list[str] = []
            try:
                completion = openai_client.chat.completions.create(
                    model=deployment,
                    messages=messages,
                    stream=True,
                )
                for chunk in completion:
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    delta = choice.delta
                    if delta.refusal:
                        yield _sse({"error": f"Refusal: {delta.refusal}"})
                        yield _sse({"done": True})
                        return
                    if choice.finish_reason == "content_filter":
                        yield _sse({"error": "Content filtered by Azure policy"})
                        yield _sse({"done": True})
                        return
                    if delta.content:
                        answer_parts.append(delta.content)
                        yield _sse({"token": delta.content})
            except openai.BadRequestError as exc:
                if exc.code == "content_filter":
                    yield _sse({"error": "Content filtered by Azure policy"})
                    yield _sse({"done": True})
                    return
                raise

            cited = select_citations(
                "".join(answer_parts), context_chunks, openai_client, deployment
            )
            sources = [{k: v for k, v in c.items() if k != "text"} for c in cited]
            yield _sse({"sources": sources})
            yield _sse({"done": True})
        except Exception as exc:
            logger.error("SSE stream error: %s", exc)
            yield _sse({"error": "An unexpected error occurred"})
            yield _sse({"done": True})

    return StreamingResponse(generate(), media_type="text/event-stream")
