from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from src.backend.config.settings import BASE_DIR

# Anthropic Messages API settings. Keeping these constants near the top makes
# provider-specific pieces easy to replace later if we add other models.
ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
SYSTEM_PROMPT = (
    "You answer questions about a codebase using only the supplied retrieved snippets. "
    "Be direct and cite files as path:start-end. If the snippets are insufficient, "
    "say what is missing."
)

# Reject answers when retrieval confidence is too low (tune with on-repo vs off-topic questions).
MIN_RELEVANCE_SCORE = 0.6
OUT_OF_SCOPE_MESSAGE = (
    "That question doesn't look related to this indexed repository. "
    "Try asking about a file, function, class, or feature in the codebase."
)


def best_match_score(matches: list[dict]) -> float:
    return max((float(match.get("score", 0.0)) for match in matches), default=0.0)


def filter_relevant_matches(matches: list[dict]) -> list[dict]:
    return [
        match
        for match in matches
        if float(match.get("score", 0.0)) >= MIN_RELEVANCE_SCORE
    ]


# Decide whether to call Claude or fall back to retrieval-only text. The rest of
# the app always receives the same shape: {"answer": ..., "mode": ..., "sources": ...}.
def answer_question(question: str, matches: list[dict]) -> dict:
    if not matches or best_match_score(matches) < MIN_RELEVANCE_SCORE:
        return {
            "answer": OUT_OF_SCOPE_MESSAGE,
            "mode": "out_of_scope",
            "sources": [],
        }

    sources = filter_relevant_matches(matches)
    api_key, model = load_llm_settings()
    if api_key and model and matches:
        try:
            # This is the "G" in RAG: generate an explanation using retrieved chunks.
            answer = call_anthropic(
                api_key=api_key,
                model=model,
                question=question,
                matches=matches,
            )
            return {"answer": answer, "mode": "anthropic", "sources": sources}
        except RuntimeError as exc:
            # If the network/API fails, still return useful evidence instead of
            # making the user lose the whole answer.
            fallback = extractive_answer(
                question,
                matches,
                intro="Anthropic synthesis failed, so this is the retrieved evidence instead.",
            )
            return {
                "answer": f"{fallback}\n\nAnthropic synthesis failed: {exc}",
                "mode": "retrieval_fallback",
                "sources": sources,
            }
    return {
        "answer": extractive_answer(question, matches),
        "mode": "retrieval",
        "sources": sources,
    }


# Load secrets/config from `.env` into process environment, then read the two
# variables this prototype needs. `.env.example` is only documentation.
def load_llm_settings() -> tuple[str | None, str | None]:
    load_dotenv(BASE_DIR / ".env")
    return os.getenv("ANTHROPIC_API_KEY"), os.getenv("ANTHROPIC_MODEL")


# Minimal dotenv loader so the app does not need python-dotenv as a dependency.
def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# Make a direct HTTPS request to Anthropic. We use urllib from the standard
# library to keep the backend small and easy to inspect.
def call_anthropic(api_key: str, model: str, question: str, matches: list[dict]) -> str:
    context = format_context(matches)
    # The prompt contains the user question plus only the retrieved snippets,
    # which is the core RAG idea: compact context instead of the whole repo.
    payload = {
        "model": model,
        "max_tokens": 1200,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"Question:\n{question}\n\nRetrieved snippets:\n{context}",
            },
        ],
    }
    # Anthropic expects the API key and version as headers, not inside the JSON body.
    request = urllib.request.Request(
        ANTHROPIC_MESSAGES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        # certifi gives Python a reliable CA bundle on machines where system
        # certificate paths are missing or stale.
        with urllib.request.urlopen(
            request,
            timeout=60,
            context=create_ssl_context(),
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Anthropic API returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc

    return parse_anthropic_text(data)


# Build an SSL context. Prefer certifi if installed; fall back to Python defaults.
def create_ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


# Anthropic returns content blocks; collect all text blocks into one answer string.
def parse_anthropic_text(data: dict) -> str:
    output_parts: list[str] = []
    for content in data.get("content", []):
        if content.get("type") == "text" and content.get("text"):
            output_parts.append(content["text"])
    if output_parts:
        return "\n".join(output_parts).strip()
    raise RuntimeError("Anthropic response did not contain text output.")


# Retrieval-only response builder. This is useful when no key/model is configured
# or when Claude fails, because the user can still inspect the evidence.
def extractive_answer(
    question: str,
    matches: list[dict],
    intro: str | None = None,
) -> str:
    if not matches:
        return (
            "I could not find relevant indexed code for that question. Try re-indexing "
            "the repository or asking with a file, function, class, or feature name."
        )

    lines = [
        intro
        or "Retrieval-only answer. Set ANTHROPIC_API_KEY and ANTHROPIC_MODEL for synthesized answers.",
        "",
        "Most relevant evidence:",
    ]
    for match in matches[:4]:
        # Keep snippets short enough for chat while preserving the citation.
        snippet = compact_snippet(match["text"])
        citation = f"{match['path']}:{match['start_line']}-{match['end_line']}"
        lines.append(f"- {citation} (score {match['score']}): {snippet}")
    return "\n".join(lines)


# Convert retrieved chunks into a prompt-friendly text block with explicit citations.
def format_context(matches: list[dict]) -> str:
    sections = []
    for match in matches:
        citation = f"{match['path']}:{match['start_line']}-{match['end_line']}"
        sections.append(f"[{citation}]\n{match['text']}")
    return "\n\n---\n\n".join(sections)


# Trim long source chunks for retrieval-only display. Claude still receives the
# full retrieved chunks via format_context above.
def compact_snippet(text: str, max_chars: int = 700) -> str:
    compact = "\n".join(line.rstrip() for line in text.strip().splitlines()[:18])
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."
