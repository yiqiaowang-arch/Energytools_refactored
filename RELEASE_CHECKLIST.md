# Release Checklist Entry

The **complete release checklist** for the Energytools documentation site (first ReadTheDocs
launch) is at:

👉 [docs/deployment/release-checklist.md](docs/deployment/release-checklist.md)

That checklist covers the items the user must register/perform:

- **GitHub**: create repository, push, default branch, `repo_url` update
- **ReadTheDocs**: register account, link GitHub, import project, first build
- **Webhook**: confirm the automatic rebuild integration, verify that a push triggers a build
- Domain, versions (latest/stable), final checks and FAQ

Once the site is live, the checklist page can also be reached directly from the
"Release & Deployment" section.

## Local verification status (2026-08-15)

- ✅ `pip install -r requirements.txt` (mkdocs 1.6.1 + mkdocs-material 9.7.7, Python 3.12) — the
  pixi environment was verified as equivalent
- ✅ `mkdocs build` passes: 0 errors, 0 warnings (`--strict` re-verified)
- ✅ The three main navigation sections (Architecture / Calculation Model / API Reference) plus
  the appendices (cross-verification report, consistency report, pre-release checklist) are
  registered and rendered
- ✅ `site_url` / `repo_url` in `mkdocs.yml` replaced with real addresses
  (`energytools-refactored.readthedocs.io` / `yiqiaowang-arch/Energytools_refactored`)
- ⬜ To-do: user imports the project on the ReadTheDocs website
  (https://readthedocs.org/dashboard/import/ )
