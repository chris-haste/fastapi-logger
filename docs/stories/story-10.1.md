Story 10.1 – CHANGELOG Tracking and Conventions  
───────────────────────────────────  
Epic: 10 – Release & Versioning  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

**As a maintainer of the fapilog library**  
I want a consistent CHANGELOG file that documents all user-visible changes  
So that contributors, users, and future maintainers can understand what changed and when.

───────────────────────────────────  
Acceptance Criteria

- A top-level `CHANGELOG.md` file exists
- It follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format
- The file contains at least the following sections:
  - `## [Unreleased]`
  - `## [0.1.0] - YYYY-MM-DD` (placeholder)
- New changes are added under “Unreleased” with subheadings:
  - `### Added`, `### Changed`, `### Fixed`, etc.
- Each merged story includes an appropriate changelog entry
- Release PRs move content from `Unreleased` into a versioned section
- README links to the changelog

───────────────────────────────────  
Tasks / Technical Checklist

1. Create `CHANGELOG.md` in repo root
2. Use the following base content (escaped block to preserve format):

   ```

   # Changelog

   All notable changes to this project will be documented in this file.
   This project adheres to [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

   ## [Unreleased]

   ### Added

   - Initial project scaffold
   - Basic log enrichment middleware

   ## [0.1.0] - YYYY-MM-DD

   ```

3. Update README to include a link to `CHANGELOG.md`
4. Add a project convention (e.g., in CONTRIBUTING.md) for changelog entries per story
5. (Optional) Add pre-commit hook or CI lint to ensure changelog is updated on PRs
6. Add one current entry to `Unreleased → Added` based on existing work

───────────────────────────────────  
Dependencies / Notes

- Future automation (e.g. changelog generation) can build on this
- Used by release workflow (10.2) to formalize version bumps
- Aligns with semantic versioning (planned)

───────────────────────────────────  
Definition of Done  
✓ `CHANGELOG.md` exists and follows the agreed format  
✓ README links to it  
✓ Entries are maintained under `Unreleased` for each merged story  
✓ PR merged to **main** with reviewer approval  
✓ Initial `0.1.0` section scaffolded
