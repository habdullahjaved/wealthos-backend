from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from groq import AsyncGroq  # ✅ use AsyncGroq, not Groq
from pydantic import BaseModel

router = APIRouter()


# ── Groq async client — created once, reused ─────────────────────────────────

@lru_cache(maxsize=1)
def get_groq() -> AsyncGroq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    return AsyncGroq(api_key=api_key)  # ✅ AsyncGroq


# ── Request models ────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str        # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: dict | None = None


# ── System prompt builder ─────────────────────────────────────────────────────

def _build_system_prompt(context: dict | None) -> str:
    base = (
        "You are WealthOS AI, a personal finance assistant.\n"
        "Be concise, specific, and actionable. User is based in Dubai, UAE.\n"
        "Use USD amounts from the data. Never invent numbers.\n"
        "Keep replies under 200 words unless a breakdown is explicitly requested.\n"
    )

    if not context:
        return base

    recent  = context.get("recent_transactions", [])
    by_cat  = context.get("categories", [])
    monthly = context.get("monthly_summary", {})

    total_spent = sum(monthly.values()) if monthly else 0
    lines = [base, "\n## User's financial data\n"]

    if total_spent:
        lines.append(f"Total spent this month: ${total_spent:,.0f}")

    if by_cat:
        lines.append("\nTop spending categories this month:")
        for c in by_cat[:5]:
            lines.append(f"  - {c['category']}: ${c['amount']:,.0f}")

    if recent:
        lines.append("\nLast 10 transactions:")
        for t in recent:
            lines.append(
                f"  {t.get('date','')} | {t.get('description','')} | "
                f"{t.get('category','')} | {t.get('amount','')}"
            )

    return "\n".join(lines)


# ── SSE async generator ───────────────────────────────────────────────────────

async def _stream(messages: list[dict]) -> AsyncGenerator[str, None]:
    client = get_groq()
    try:
        stream = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=512,
            temperature=0.7,
            stream=True,  # ✅ this is how async streaming works in groq 1.x
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield f"data: {json.dumps({'content': token})}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("")
async def chat(req: ChatRequest) -> StreamingResponse:
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages list is required")

    system_prompt = _build_system_prompt(req.context)
    full_messages = [{"role": "system", "content": system_prompt}] + [
        {"role": m.role, "content": m.content}
        for m in req.messages
    ]

    return StreamingResponse(
        _stream(full_messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "Connection":        "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )