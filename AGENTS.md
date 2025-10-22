# SmartInk Agent Guide

## Environment & Tooling
- Use [uv](https://github.com/astral-sh/uv) for all Python environment tasks. Do **not** call `pip install` directly; prefer `uv sync`, `uv run`, and `uv pip` when you need package operations.
- The project targets Python 3.12. Stick to standard library features available in that version.

## Testing Expectations
- Always run the full test suite with `uv run pytest` before asking for a review. Include the command and its result in your final status update.
- When you touch modules under `smartink/`, also run `python -m compileall smartink` to catch syntax errors early. (This can use `uv run python -m compileall smartink` if you need to stay inside the uv-managed environment.)

## Code Style & Quality
- Preserve and extend type hints and docstrings when modifying existing functions or adding new ones.
- Keep SQL queries readable: multiline strings should align keywords and indent nested clauses for clarity.
- Favor small, pure helper functions for complex calculations—especially in analytics modules—to simplify testing.
- Make logging and user-facing text actionable and professional; avoid emoji unless the surrounding code already uses them consistently.

## Streamlit & UI Work
- Cache expensive computations with `st.cache_data` or `st.cache_resource` as appropriate.
- Any substantial visual change to the Streamlit dashboard should include an updated screenshot when the tooling is available.

## Git & PR Notes
- Group related changes into a single commit whenever possible; avoid mixing refactors with functional fixes without clear justification.
- Keep PR descriptions concise: summarize key changes and list the verification commands you ran.
