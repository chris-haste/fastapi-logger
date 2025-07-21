# Story 1: Primer & High-Level Guide

## Status

Draft

## User Story

As a new or returning user of Fapilog,
I want a clear, high-level introduction to the project, its core concepts, and typical workflows,
so that I can quickly understand what Fapilog is, how it works, and how to get started.

## Story Context

**Existing System Integration:**

- Integrates with: docs/index.rst, docs/user-guide.md, docs/api-reference.md
- Technology: Sphinx/ReadTheDocs, Markdown/ReStructuredText
- Follows pattern: Developer-centric documentation, clear onboarding
- Touch points: Documentation landing page, navigation sidebar

## Acceptance Criteria

1. A new or revised introduction section clearly answers "What is Fapilog?"
2. Core concepts (e.g., logging pipeline, sinks, enrichers, redactors) are explained concisely
3. Typical user workflows are described with diagrams or step lists
4. The section is accessible from the main navigation/sidebar
5. Style and formatting follow the new documentation style guide
6. Internal links to relevant sections (tutorials, reference, concepts) are included

## Tasks / Subtasks

- [x] Draft "What is Fapilog?" section (AC: 1)
- [x] Summarize core concepts (AC: 2)
- [x] Illustrate typical workflows (AC: 3)
- [x] Integrate section into main navigation/sidebar (AC: 4)
- [x] Apply style guide formatting (AC: 5)
- [x] Add internal links to tutorials, concepts, and reference (AC: 6)

## Dev Agent Record

### Completion Notes

- All primer and onboarding content is now centralized in docs/primer.md and linked from index.rst.
- Navigation/sidebar and internal links are fully updated.
- Style guide compliance is verified.

### File List

- docs/primer.md (new)
- docs/index.rst (modified)
- docs/stories/story-15.1.md (updated)

### Change Log

- 2024-06-07: Created docs/primer.md and updated index.rst for onboarding improvements. All tasks complete. (James)

### Status

Ready for Review
