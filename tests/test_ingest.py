from ragdocs.ingest import chunk_markdown, slugify

SAMPLE = """Intro paragraph before any heading.

# Widgets

Widgets are the core object.

## Create a widget

POST /v1/widgets creates a widget.

## Empty section

### Widget statuses

`active` and `retired`.
"""


def test_chunks_split_on_headings():
    chunks = chunk_markdown(SAMPLE, "widgets.md")
    assert [c.heading for c in chunks] == [
        "widgets.md",  # preamble chunk
        "Widgets",
        "Create a widget",
        "Widget statuses",  # "Empty section" has no body and is dropped
    ]
    assert [c.level for c in chunks] == [0, 1, 2, 3]
    assert chunks[2].text == "POST /v1/widgets creates a widget."
    assert all(c.source_file == "widgets.md" for c in chunks)


def test_heading_inside_code_fence_is_not_a_chunk_boundary():
    text = "# Config\n\nExample file:\n\n```\n# not a heading\nkey = value\n```\n"
    chunks = chunk_markdown(text, "config.md")
    assert len(chunks) == 1
    assert "# not a heading" in chunks[0].text


def test_anchor_and_citation_format():
    chunks = chunk_markdown("# Verifying signatures\n\nUse HMAC.", "webhooks.md")
    (chunk,) = chunks
    assert chunk.anchor == "verifying-signatures"
    assert chunk.chunk_id == "webhooks.md#verifying-signatures"
    assert chunk.citation == "[webhooks.md § Verifying signatures]"


def test_slugify_strips_punctuation():
    assert slugify("Step 3: report usage") == "step-3-report-usage"
    assert slugify("Errors & retries") == "errors-retries"
