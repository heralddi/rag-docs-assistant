"""Content-word overlap between each benchmark question and its gold heading.

Usage: python eval/question_overlap.py [--questions FILE]

Content words are the terms the bm25 backend indexes: lowercased tokens of two or
more word characters, minus scikit-learn's English stop-word list, with no stemming.
Prints, per question, the gold heading's content words that also occur in the
question, then how many questions contain at least one and at least half of them.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from run_eval import load_questions
from sklearn.feature_extraction.text import CountVectorizer

EVAL_DIR = Path(__file__).parent
_analyze = CountVectorizer(stop_words="english").build_analyzer()


def content_words(text: str) -> set[str]:
    return set(_analyze(text))


def heading_overlap(question: dict) -> tuple[set[str], set[str]]:
    """The gold heading's content words, and the subset that occurs in the question."""
    heading = content_words(question["heading"])
    return heading, heading & content_words(question["question"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", default=str(EVAL_DIR / "questions.jsonl"))
    args = parser.parse_args()

    questions = load_questions(Path(args.questions))
    at_least_one = at_least_half = 0
    for question in questions:
        heading, shared = heading_overlap(question)
        at_least_one += len(shared) >= 1
        at_least_half += len(heading) > 0 and 2 * len(shared) >= len(heading)
        print(
            f"{len(shared)}/{len(heading)}  {question['source_file']} § {question['heading']}"
            f"  shared: {', '.join(sorted(shared)) or '-'}"
        )
    n = len(questions)
    print(f"Questions with at least one gold-heading content word: {at_least_one} of {n}")
    print(f"Questions with at least half of them: {at_least_half} of {n}")


if __name__ == "__main__":
    main()
