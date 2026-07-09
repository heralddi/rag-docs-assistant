"""Command-line interface: python -m ragdocs {index,ask}."""

from __future__ import annotations

import argparse
import sys

from .answer import answer
from .index import BACKENDS, DEFAULT_INDEX_DIR, build_index, load_index, save_index
from .ingest import chunk_directory

DEFAULT_DOCS_DIR = "data/sample_docs"


def cmd_index(args: argparse.Namespace) -> None:
    chunks = chunk_directory(args.docs)
    print(f"Chunked {args.docs}: {len(chunks)} chunks")
    index = build_index(chunks, args.backend)
    save_index(index, args.index_dir)
    print(f"Saved {args.backend} index to {args.index_dir}")


def cmd_ask(args: argparse.Namespace) -> None:
    index = load_index(args.index_dir)
    print(answer(args.question, index, k=args.k, mode=args.mode))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="ragdocs", description="Question answering over API docs with cited sources."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_index = subparsers.add_parser("index", help="Chunk docs and build a retrieval index.")
    p_index.add_argument("--docs", default=DEFAULT_DOCS_DIR, help="Directory of .md files.")
    p_index.add_argument("--backend", choices=BACKENDS, default="embed")
    p_index.add_argument("--index-dir", default=str(DEFAULT_INDEX_DIR))
    p_index.set_defaults(func=cmd_index)

    p_ask = subparsers.add_parser("ask", help="Answer a question from the indexed docs.")
    p_ask.add_argument("question")
    p_ask.add_argument("--k", type=int, default=3, help="Number of chunks to retrieve.")
    p_ask.add_argument(
        "--mode",
        choices=["extractive", "generative"],
        default="extractive",
        help="generative needs OPENAI_API_KEY and falls back to extractive without it.",
    )
    p_ask.add_argument("--index-dir", default=str(DEFAULT_INDEX_DIR))
    p_ask.set_defaults(func=cmd_ask)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except FileNotFoundError as exc:
        sys.exit(f"Error: {exc}")


if __name__ == "__main__":
    main()
