import json
from pathlib import Path

import pytest

from ragdocs.__main__ import main

DOCS_DIR = Path(__file__).parents[1] / "data" / "sample_docs"


def test_cli_builds_and_queries_a_bm25_index(tmp_path, capsys):
    index_dir = tmp_path / "idx"
    main(["index", "--docs", str(DOCS_DIR), "--backend", "bm25", "--index-dir", str(index_dir)])
    assert json.loads((index_dir / "meta.json").read_text())["backend"] == "bm25"

    main(["ask", "How do I verify a webhook signature?", "--index-dir", str(index_dir)])
    out = capsys.readouterr().out
    assert "Saved bm25 index" in out
    assert "Best passage [webhooks.md § Verifying signatures]:" in out


def test_cli_rejects_an_unknown_backend(tmp_path):
    with pytest.raises(SystemExit):
        main(["index", "--docs", str(DOCS_DIR), "--backend", "bm26", "--index-dir", str(tmp_path)])
