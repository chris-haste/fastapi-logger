Story 10.4 – CONTRIBUTING Guide  
───────────────────────────────────  
Epic: 10 – Release & Versioning  
Sprint Target: Sprint #⟪next⟫  
Story Points: 2

**As a contributor to the fapilog library**  
I want clear contribution guidelines  
So that I can follow project conventions for setup, testing, and submitting PRs successfully.

───────────────────────────────────  
Acceptance Criteria

- A `CONTRIBUTING.md` file exists at the repo root
- It includes setup instructions, development flow, and commit expectations
- Explains how to install dependencies and run tests/lint locally
- Outlines how and when to update the `CHANGELOG.md`
- Describes release versioning and tagging policy
- References pre-commit, Hatch, and GitHub Actions checks
- Includes section on how to request a new feature or file a bug

───────────────────────────────────  
Tasks / Technical Checklist

1. Create `CONTRIBUTING.md` in the root of the repository

2. Add the following sections:

   - **Project Setup**
     - Clone repo
     - Create and activate virtual environment
     - `pip install -e ".[dev]"`
     - `hatch run test`
   - **Development Workflow**
     - Use feature branches
     - Ensure code is linted, typed, and tested
     - Pre-commit hooks (if configured)
     - Include `CHANGELOG.md` entry in PR
   - **Commit & PR Guidelines**
     - Use conventional commits
     - e.g. `feat: add new sink`, `fix: handle invalid config`, `chore(release): v0.1.1`
   - **Release Process**
     - Reference `RELEASING.md`
     - Outline semantic versioning
   - **How to Get Help or Suggest Features**
     - Link to Discussions or Issues

3. Link `CONTRIBUTING.md` in the README under a **Contributing** section

4. Ensure file renders correctly on GitHub UI (headings, bullets, code blocks)

───────────────────────────────────  
Dependencies / Notes

- Assumes Stories 9.1 (CI), 9.4 (build), and 10.2 (RELEASING.md) are done
- Guidelines should evolve with team or external contributor needs
- May become part of a wider documentation effort later

───────────────────────────────────  
Definition of Done  
✓ `CONTRIBUTING.md` exists with required sections  
✓ Linked in `README.md`  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
