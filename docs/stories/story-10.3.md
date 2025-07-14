Story 10.3 – Version Bump Guardrails  
───────────────────────────────────  
Epic: 10 – Release & Versioning  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a maintainer of the fapilog library**  
I want lightweight guardrails to ensure that version bumps and changelog updates are not forgotten  
So that every release is properly documented and semantically versioned.

───────────────────────────────────  
Acceptance Criteria

- CI fails if a release commit (e.g. `chore(release): vX.Y.Z`) is missing a version bump in `pyproject.toml`
- CI fails if a release commit does not update the `CHANGELOG.md`
- Optional: pre-commit hook warns when merging to `main` without changelog or version bump
- Contributing guide documents this requirement
- Release checklist or CI summary includes confirmation step

───────────────────────────────────  
Tasks / Technical Checklist

1. Add GitHub Actions check:

   - If commit message matches `^chore\(release\): v\d+\.\d+\.\d+$`, assert:
     - `pyproject.toml` includes matching version string
     - `CHANGELOG.md` includes matching version section
   - Can use simple shell script or Python to check values

2. Add `.github/workflows/release-guard.yml` workflow to run on `push` to `main`

3. (Optional) Add pre-commit hook to check for version/changelog mismatch before merge

4. Add section to `CONTRIBUTING.md` titled **Release Process & Checklist**, with:

   - Reminder to bump version and changelog
   - Required tag format and PR requirements

5. Test with fake release commit (e.g., `chore(release): v0.2.0`)

   - Confirm CI passes only with correct version and changelog
   - Confirm CI fails if either is missing or inconsistent

6. Add one test version bump (`v0.1.1`) to confirm process works end-to-end

───────────────────────────────────  
Dependencies / Notes

- This story assumes Story 10.2 (manual release process) is complete
- Optional enhancements (e.g., GitHub bots or version bump tools) can be introduced later
- Intentionally simple guardrails for now, rather than full semantic-release tooling

───────────────────────────────────  
Definition of Done  
✓ Guardrails in place to catch missing version/changelog on release commits  
✓ Tests confirm working behavior for correct/incorrect cases  
✓ CONTRIBUTING.md updated  
✓ PR merged to **main** with reviewer approval  
✓ CHANGELOG.md updated under _Unreleased → Added_
