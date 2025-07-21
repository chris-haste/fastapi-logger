# Documentation Style Guide

## Purpose

This guide ensures all documentation is clear, consistent, and easy to maintain. All contributors must follow these standards for every documentation change.

---

## 1. Headings & Structure

- Use clear, descriptive headings (e.g., `## Installation`, `### Usage Example`).
- Use sentence case for headings (capitalize only the first word and proper nouns).
- Use Markdown (`#`, `##`, `###`) or reStructuredText (`=`, `-`, `~`) heading syntax as appropriate for the file type.
- Maintain a logical hierarchy; do not skip heading levels.

---

## 2. Code Blocks

- Use fenced code blocks (triple backticks for Markdown, `::` for reStructuredText) for all code, commands, and configuration examples.
- Specify the language for syntax highlighting (e.g., `python, `bash).
- Keep code examples minimal, correct, and copy-paste ready.
- Use consistent indentation (4 spaces for Python, 2 spaces for YAML/JSON).
- Avoid mixing code and prose in the same block.

---

## 3. Naming Conventions

- Use consistent terminology throughout the docs (e.g., always use "FastAPI app" not "API app").
- File and directory names: use lowercase and hyphens (e.g., `user-guide.md`).
- Variable and function names in code examples should follow the conventions of the language shown (e.g., `snake_case` for Python).

---

## 4. Formatting & Style

- Use plain, direct language. Avoid jargon unless defined.
- Use lists for steps, options, or related items.
- Bold important terms or warnings using `**bold**` (Markdown) or `**strong**` (reStructuredText).
- Italicize new terms or concepts on first use.
- Use tables for structured data where appropriate.
- Keep line length under 100 characters.
- Use one sentence per line for easier diffs and reviews.

---

## 5. References & Links

- Use relative links for internal documentation (e.g., `[User Guide](user-guide.md)`).
- Always check that links are valid and up to date.
- Reference the style guide in all contributor documentation.

---

## 6. Review & Automation

- Review your changes for consistency with this guide before submitting.
- Use available linters or documentation checkers if provided.
- Solicit feedback from other contributors for major changes.

---

## 7. Example

```python
# Good Python example
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

---

## 8. Updates

- Propose changes to this guide via pull request.
- Major changes require consensus from maintainers.
