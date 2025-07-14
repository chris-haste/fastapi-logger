Story 12.3 – Deploy Documentation via GitHub Pages  
───────────────────────────────────  
Epic: 12 – Documentation  
Sprint Target: Sprint #⟪next⟫  
Story Points: 3

**As a user of fapilog**  
I want to access the project documentation from a public URL  
So that I can browse usage guides and API references online without cloning the repository.

───────────────────────────────────  
Acceptance Criteria

- Docs are published to GitHub Pages on every push to `main`
- Uses GitHub Actions with `mkdocs gh-deploy`
- Hosted at `https://<org>.github.io/fastapi-logger` or custom domain if configured
- Home, Getting Started, and API pages are included in the deployed site
- Badge in README links to the deployed docs
- Previous deploys are cleaned before new ones are pushed

───────────────────────────────────  
Tasks / Technical Checklist

1.  Configure `mkdocs.yml` with site URL:  
     site_url: https://<org>.github.io/fastapi-logger  
     repo_url: https://github.com/<org>/fastapi-logger  
     theme:
    name: material
    features: - navigation.instant - navigation.tracking

2.  Create `.github/workflows/docs.yml`:  
     name: Deploy Docs

    on:
    push:
    branches: [main]

    permissions:
    contents: write

    jobs:
    deploy:
    runs-on: ubuntu-latest
    steps: - uses: actions/checkout@v4 - uses: actions/setup-python@v5
    with:
    python-version: '3.11'

             - name: Install dependencies
               run: pip install ".[docs]"

             - name: Deploy docs
               run: mkdocs gh-deploy --force

3.  Enable Pages in repo settings → Deploy from `gh-pages` branch

4.  Add a badge to README:  
     [![Docs](https://img.shields.io/badge/docs-online-blue)](https://<org>.github.io/fastapi-logger)

5.  Verify deployed site and check for broken links or rendering issues

───────────────────────────────────  
Dependencies / Notes

- Requires 12.1 and 12.2 to be complete
- GitHub Pages branch (`gh-pages`) will be automatically created by MkDocs
- Custom domain can be configured later via `CNAME` if needed

───────────────────────────────────  
Definition of Done  
✓ Docs deploy automatically on push to `main`  
✓ Site is accessible and fully rendered  
✓ Badge added to README  
✓ PR merged to **main** with reviewer approval  
✓ `CHANGELOG.md` updated under _Unreleased → Added_
