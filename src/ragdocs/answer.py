"""Turn retrieved chunks into an answer with citations."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .ingest import Chunk

GENERATIVE_SYSTEM_PROMPT = (
    "You answer questions about API documentation. Use only the numbered "
    "passages provided. After every claim, cite the passage it came from "
    "using its bracketed citation exactly as given. If the passages do not "
    "answer the question, say so."
)


def format_extractive(question: str, results: list[tuple[Chunk, float]]) -> str:
    """Best passage verbatim, then the runners-up as pointers."""
    if not results:
        return "No matching passages found."
    best_chunk, _ = results[0]
    lines = [
        f"Q: {question}",
        "",
        f"Best passage {best_chunk.citation}:",
        "",
        best_chunk.text,
    ]
    if len(results) > 1:
        lines += ["", "Other relevant sections:"]
        for rank, (chunk, score) in enumerate(results[1:], start=2):
            lines.append(f"  {rank}. {chunk.citation} (score {score:.3f})")
    return "\n".join(lines)


def generative_answer(question: str, results: list[tuple[Chunk, float]]) -> str:
    """Synthesize a grounded answer via an OpenAI-compatible chat endpoint.

    Requires OPENAI_API_KEY. OPENAI_BASE_URL and OPENAI_MODEL are optional.
    Raises RuntimeError when the key is missing or the call fails; the CLI
    falls back to extractive mode in that case.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    passages = "\n\n".join(
        f"Passage {i} {chunk.citation}:\n{chunk.text}"
        for i, (chunk, _) in enumerate(results, start=1)
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": GENERATIVE_SYSTEM_PROMPT},
            {"role": "user", "content": f"{passages}\n\nQuestion: {question}"},
        ],
        "temperature": 0,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Chat completion request failed: {exc}") from exc
    return body["choices"][0]["message"]["content"].strip()


def answer(question: str, index, k: int = 3, mode: str = "extractive") -> str:
    """Retrieve top-k chunks and answer in the requested mode.

    Generative mode degrades to extractive with a notice when no API key
    is configured or the request fails.
    """
    results = index.search(question, k=k)
    if mode == "generative":
        try:
            text = generative_answer(question, results)
            sources = ", ".join(chunk.citation for chunk, _ in results)
            return f"{text}\n\nRetrieved sources: {sources}"
        except RuntimeError as exc:
            notice = f"[generative mode unavailable: {exc}; showing extractive answer]"
            return f"{notice}\n\n{format_extractive(question, results)}"
    return format_extractive(question, results)
