# Documentation Build & ReadTheDocs Release Pipeline

This document explains how to build the documentation site of this repository (MkDocs +
Material) locally and publish it via ReadTheDocs. The site content comprises all documents
under `docs/` (workbook assessment, architecture & API reference, calculation textbook,
installation guide); the navigation structure is defined in `mkdocs.yml` at the repository
root.

## 1. Local build

Prerequisite: Python ≥ 3.11 (3.13 recommended).

```bash
# Install the build dependencies (mkdocs + mkdocs-material)
pip install -r requirements.txt

# Local preview (http://127.0.0.1:8000, auto-reload)
mkdocs serve

# Static site build (output to site/)
mkdocs build
```

You can also install through the repository's own packaging scaffold
(`pip install -e ".[docs]"` or `pixi install -e docs`), see
[installation.md](../installation.md).

## 2. Site structure

The `nav` of `mkdocs.yml` maps one-to-one onto the `docs/` directory:

| Navigation group | Content |
|---|---|
| Home | `docs/README.md` (docs inventory) |
| Workbook assessment | `docs/01-workbook-assessment.md` (document set 01) |
| Architecture | `docs/architecture+api-reference/` guide + 01 (package & symbol inventory) + 08 (completeness check) |
| Calculation model | `docs/textbook/` (document set 03, chapters 1–6 + appendix A) |
| API reference | `docs/architecture+api-reference/` 02–07 (common foundation / Raumdaten / Gebäude / versioning & export / FastAPI / MCP) |
| Installation | `docs/installation.md` (pixi / uv / conda / pip) |
| Release & deployment | this document + [first-launch release checklist](release-checklist.md) |

Conventions: `docs_dir: docs` (default), theme `material`, language `zh`, search and code-copy
features enabled.

## 3. ReadTheDocs publishing

1. Import this repository in ReadTheDocs (Admin → Advanced Settings can specify the build
   configuration).
2. The build configuration is `.readthedocs.yaml` (MkDocs builder, Python 3.12, dependencies
   from `requirements.txt`).
3. Every push to the default branch triggers a build; site address:
   `https://energytools-refactored.readthedocs.io/` (`site_url` in `mkdocs.yml`; replace with
   the real domain before publishing).
4. Before publishing, replace `repo_name` / `repo_url` in `mkdocs.yml` with the real repository
   address.

## 4. Validation & maintenance

* After modifying documentation, run `mkdocs build` (or `mkdocs serve`) to validate links and
  navigation; the relative-link and anchor validation script between documents is described in
  `docs/architecture+api-reference/08-completeness-check.md` §5 and in
  `docs-consistency-report.md`.
* When adding a document, update three places in sync: `docs/README.md` (docs inventory),
  `mkdocs.yml` (`nav`), and, if necessary,
  `docs/architecture+api-reference/08-completeness-check.md` §3 (inventory status table).
