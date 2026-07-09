"""Chunk markdown documentation files by heading."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def slugify(heading: str) -> str:
    """Turn a heading into a GitHub-style anchor slug."""
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return re.sub(r"\s+", "-", slug)


@dataclass(frozen=True)
class Chunk:
    """One heading-scoped section of a markdown file."""

    source_file: str  # path relative to the docs directory
    heading: str
    anchor: str
    level: int  # heading level, 0 for text before the first heading
    text: str

    @property
    def chunk_id(self) -> str:
        return f"{self.source_file}#{self.anchor}"

    @property
    def citation(self) -> str:
        return f"[{self.source_file} § {self.heading}]"


def chunk_markdown(text: str, source_file: str) -> list[Chunk]:
    """Split one markdown document into heading-scoped chunks.

    Every heading starts a new chunk. Text before the first heading is
    attached to a chunk whose heading is the file name. Headings inside
    fenced code blocks are treated as code, not structure. Chunks with
    an empty body (a heading followed directly by another heading) are
    dropped.
    """
    chunks: list[Chunk] = []
    heading, level = source_file, 0
    body: list[str] = []
    in_fence = False

    def flush() -> None:
        stripped = "\n".join(body).strip()
        if stripped:
            chunks.append(Chunk(source_file, heading, slugify(heading), level, stripped))

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = match.group(2)
            body = []
        else:
            body.append(line)
    flush()
    return chunks


def chunk_directory(docs_dir: str | Path) -> list[Chunk]:
    """Chunk every .md file under docs_dir, recursively."""
    docs_dir = Path(docs_dir)
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Docs directory not found: {docs_dir}")
    paths = sorted(docs_dir.rglob("*.md"))
    if not paths:
        raise FileNotFoundError(f"No .md files found under {docs_dir}")
    chunks: list[Chunk] = []
    for path in paths:
        rel = path.relative_to(docs_dir).as_posix()
        chunks.extend(chunk_markdown(path.read_text(encoding="utf-8"), rel))
    return chunks
