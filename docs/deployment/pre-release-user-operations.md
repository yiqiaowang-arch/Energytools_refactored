# Pre-release Checklist and User Operations Manual (energytools v0.1.0)

> **Purpose**: A step-by-step operations manual for the **release operator** (the repository owner). It breaks down "publishing this project to GitHub + Read the Docs from scratch" into 6 items. Each item lists **user action / automatic action** step by step, provides a **decision table** and **acceptance criteria**, and appends a **repository description** and **release announcement drafts**.
>
> **Scope statement**: This document covers only **platform-level operations** — account registration, platform connection, repository creation, project import, webhook, domain, and so on. Code/configuration files such as `pyproject.toml`, `.readthedocs.yaml`, Sphinx `conf.py`, CI, etc. are **not implemented in this branch** (they are handled respectively by branches such as "multi-install packaging scaffold", "documentation build and readthedocs publishing pipeline", and "rtd build pipeline completion and local verification"). The repository/platform facts referenced by this document follow the project's current status (see [Project status](#0)).

---

## 0. Project Status and Terminology

### 0.1 Project status (as the basis for this document)

| Item | Status |
|---|---|
| Package name | `energytools` (src layout, hatchling backend, PEP 621) |
| Version | `0.1.0` (Pre-Alpha; see `pyproject.toml` / `src/energytools/__init__.py` / `pixi.toml`) |
| Description | A Python reimplementation of the SIA 2024 energy tools (Raumdatenblätter, Gebäude-Tool) |
| Language/runtime | Python ≥ 3.11 (3.13 recommended) |
| Install methods | pixi / uv / conda / pip (see `docs/installation.md`) |
| Docs toolchain | Sphinx + myst-parser + sphinx-rtd-theme (`docs` extra, target platform Read the Docs) |
| Default branch | GitHub's default branch should be `main` (the local current branch carries a Chinese task name and is used only for workflow collaboration; `main` is the default branch at release time) |
| Repository status | No GitHub remote repository created yet; no project on readthedocs.org yet |

### 0.2 Glossary

| Term | Meaning |
|---|---|
| GitHub repository (repo) | The code-hosting repository; the **single source of truth** for the documentation |
| Read the Docs (RTD) | Documentation hosting platform; the community edition readthedocs.org is free and requires the repository to be **public** |
| RTD project | A documentation project on RTD, corresponding one-to-one with a Git repository |
| slug | URL identifier of the RTD project; the target slug for this project is `energytools-refactored`, with the default domain `https://energytools-refactored.readthedocs.io/` |
| webhook | Automatic trigger channel from GitHub events → RTD builds; **installed automatically** when RTD imports a project |
| version | RTD's `latest` (default branch), `stable` (newest tag), plus versions generated from branches/tags |
| Pull request builds | Pre-builds documentation for GitHub PRs (optional; enable in RTD advanced settings) |
| CNAME | A DNS record type; how a custom domain connects to RTD |
| OAuth | The authorization mechanism RTD uses to "sign in with GitHub / connect a GitHub account" |
| badge | Image link in the README showing the "docs build status" |

---

## 1. Overall Flow

```
Stage A          Stage B          Stage C           Stage D           Stage E          Stage F
GitHub repo ──► RTD sign-up ──► Project import ──► webhook confirm ──► Domain config ──► Acceptance & release
(creation)      (account/OAuth)  (first build)      (auto/fallback)   (subdomain/custom) (description + copy)
```

- Stages A–B are **purely user actions** (no automatic step); C–E are a mix of "user action + platform automatic action"; F is **content production** (drafts are provided in Section 8 of this document).
- The "actor" for each stage uses two markers: **👤 user action** (must be done manually; usually not automatable or too risky to automate) / **🤖 automatic action** (done automatically by the platform; the user only needs to verify).
- The **pass criteria** for all stages are summarized in [Section 9 master acceptance checklist](#9).

---

## 2. Item 1: GitHub Repository Creation

### 2.1 Decision table

| Decision ID | Decision point | Options | Recommended | Consequence / Impact |
|---|---|---|---|---|
| D1 | Repository owner | A. Personal account<br>B. Organization | **B (if an organization exists)**, otherwise A | An organization eases multi-person collaboration and ownership; migrating a personal account to an organization later requires changing the remote and the RTD connection |
| D2 | Repository visibility | A. Public<br>B. Private | **A. Public** | RTD community edition (free) **only supports public repositories**; if it must be private → Read the Docs for Business (paid) is required, see D7 |
| D2a | Default branch name | A. `main`<br>B. Other | **A. `main`** | RTD builds `main` by default; the `latest` version automatically follows the default branch |
| D2b | Initialization content | A. Empty repository, push from local<br>B. Initialize with README/license/.gitignore | **B, but local files take precedence** | Local README, docs, etc. already exist; do **not** check GitHub's auto-generated README/license (to avoid conflicts); a local .gitignore already exists |
| D2c | Repository name | `energytools` (recommended) | `energytools` | Consistent with the package name and the RTD slug; avoids ambiguity from variants such as `energytools-refactored`; the name is hard to change once published |

### 2.2 Operation checklist (user action / automatic action)

| # | Actor | Action | Expected result | Acceptance check |
|---|---|---|---|---|
| 1 | 👤 User | Sign in to GitHub → New repository: Owner (per D1), Repository name = `energytools`, **Public** (per D2), default branch `main` (per D2a); do **not** check auto-generated README/.gitignore/license (per D2b) | Repository `https://github.com/<owner>/energytools` created successfully | Opening the repository URL in a browser shows the empty repository page |
| 2 | 🤖 Automatic | GitHub initializes the repository (empty repository, default branch `main`) | The repository page shows the "…or push an existing repository" guidance | The push guidance is visible on the repository page |
| 3 | 👤 User | Push existing content from local: `git remote add origin git@github.com:<owner>/energytools.git`; `git push -u origin main` (push the local `main` content; merge the Chinese-named task branch per the team workflow before pushing) | Local files (pyproject.toml, README.md, docs/, src/, pixi.toml, etc.) appear on GitHub | The GitHub repository file list matches the local one |
| 4 | 👤 User | Fill in the repository description (draft in [8.1](#81-github)) and Topics (see [8.1](#81-github)) | The repository page shows the description and topic tags | Description and topics are visible on the repository page |
| 5 | 👤 User | (Optional) Settings → set the default branch to `main`, enable branch protection (require PR review) | `main` is protected | Settings → Branches shows the protection rule |

### 2.3 Notes

- **Repository name is a prerequisite for the slug**: the RTD slug defaults to the repository name. If `energytools` is taken, RTD will warn about a slug conflict (see [4.3](#43)).
- GitHub description limit is **350 characters**; Topics limit is **20**.
- End-of-stage marker: `https://github.com/<owner>/energytools` is reachable, content matches local, and description and topics are filled in.

---

## 3. Item 2: Read the Docs Registration and GitHub Connection

### 3.1 Decision table

| Decision ID | Decision point | Options | Recommended | Consequence / Impact |
|---|---|---|---|---|
| D3 | Registration/sign-in method | A. Sign in with GitHub OAuth<br>B. Email registration + manual GitHub connection later | **A. GitHub OAuth** | Skips email verification and a second connection step; the GitHub repository list is directly visible when importing; the OAuth scope is "read repository metadata" (no write permission granted) |
| D3a | Connect the GitHub account immediately | A. Authorize at sign-in<br>B. Connect later in Settings → Connected Accounts | **A** | Without connecting, the "automatic import" path (Item 3) is unavailable and the repository URL must be entered manually |
| D3b | Community or Business edition | A. readthedocs.org (community edition, free)<br>B. Read the Docs for Business (paid) | **A (this release's target)** | Community edition requires a public repository (D2); Business supports private repositories, SLAs, and auditing, billed per site/user |

### 3.2 Operation checklist

| # | Actor | Action | Expected result | Acceptance check |
|---|---|---|---|---|
| 1 | 👤 User | Open https://readthedocs.org → **Sign in with GitHub** (per D3) | Lands on the RTD Dashboard | The signed-in username appears in the top-right corner of the page |
| 2 | 🤖 Automatic | GitHub OAuth authorization page → RTD creates an account and links the GitHub identity | The RTD account is linked one-to-one with the GitHub account | Dashboard shows the username (same as GitHub) |
| 3 | 👤 User | (If first signing in by email) Settings → Connected Accounts → Connect GitHub, grant the required permissions | The GitHub account appears in Connected Accounts | The GitHub account and authorization time are visible on the Settings page |
| 4 | 👤 User | Settings → confirm the email is verified (if using the email path) | Email status Verified | Settings → Email shows verified |

### 3.3 Notes

- OAuth scope: importing a project requires **reading the repository list**; RTD does not request write permission. The later automatic webhook creation depends on the permission to "install webhooks in the repository" (determined by the GitHub App / OAuth repo webhook permission; if the authorization is insufficient and webhook creation fails, fall back to the manual path in [Item 4](#5-webhook)).
- End-of-stage marker: signed in to RTD and the GitHub account is connected.

---

## 4. Item 3: Project Import (Import)

### 4.1 Decision table

| Decision ID | Decision point | Options | Recommended | Consequence / Impact |
|---|---|---|---|---|
| D4 | Import method | A. Automatic import via the connected GitHub account (Import a Project → select the repository)<br>B. Enter the repository URL manually | **A** | A also configures the webhook automatically (Item 4); B requires adding the webhook manually |
| D4a | Project name / slug | Defaults to the repository name `energytools-refactored`; rename if conflicting | `energytools` | The slug determines the default domain `https://energytools-refactored.readthedocs.io/`; the slug **cannot be changed** once published |
| D4b | Configuration source for the first build | RTD auto-detects `.readthedocs.yaml` (v2 config) or `docs/conf.py` | Depends on the configuration delivered by the "documentation build" branch | This branch does **not** create configuration files; if none is detected, the first build fails, which is expected (see 4.4 troubleshooting) |

### 4.2 Operation checklist

| # | Actor | Action | Expected result | Acceptance check |
|---|---|---|---|---|
| 1 | 👤 User | Dashboard → **Import a Project** → select the GitHub account → select `energytools` in the repository list (per D4) | Lands on the import confirmation page | The page shows the repository name `energytools` and the slug is editable |
| 2 | 👤 User | Confirm the project name and slug = `energytools-refactored` (per D4a) → **Next / Import** | The project is created and enters the first build | Redirected to the project builds page (Builds) |
| 3 | 🤖 Automatic | RTD clones the repository, detects `.readthedocs.yaml` / `docs/conf.py`, and runs the documentation build (installs the `docs` extra dependencies, runs Sphinx) | First build completes (success or failure, depending on whether the configuration files are ready) | A build #1 record appears on the Builds page |
| 4 | 🤖 Automatic | Generates the default version `latest` (follows the default branch `main`) | `latest` appears in the version list | The Versions page shows `latest` |
| 5 | 👤 User | Verify the default subdomain is reachable: `https://energytools-refactored.readthedocs.io/en/latest/` | The page opens and shows the documentation | Browser access passes |

### 4.3 Notes

- **slug conflict**: if `energytools-refactored.readthedocs.io` is already taken by someone else, the import will report the slug as unavailable; in that case rename it (e.g. `energytools-sia2024`) and record that slug in the decision summary in Section 7 of this manual.
- If the first build fails due to missing `.readthedocs.yaml` / `conf.py`: this is **not a defect of this branch**; it is a delivery prerequisite of the "documentation build and readthedocs publishing pipeline" and "rtd build pipeline completion and local verification" branches. This branch's acceptance only requires that **the project is created successfully and the build mechanism works**.
- End-of-stage marker: the RTD project `energytools` exists, Builds has records, and the `latest` version exists.

---

## 5. Item 4: Webhook Configuration

### 5.1 Decision table

| Decision ID | Decision point | Options | Recommended | Consequence / Impact |
|---|---|---|---|---|
| D5 | webhook source | A. Installed automatically by RTD at import (default)<br>B. Created manually on GitHub<br>C. Not configured (only manual "Build latest") | **A, with B as fallback** | A/B: pushing to `main` automatically triggers a documentation build; C: every release requires a manual build click, easy to miss, not recommended |
| D6 | Pull request builds | A. Enable<br>B. Disable | **A (during team collaboration)** | When enabled, every PR generates a preview of the documentation for review; the cost is one extra build |
| D6a | Build trigger events | push (default) ｜ tag can also be added (tagging auto-builds the version) | push + tag | Tag builds guarantee that `stable` points to the released version correctly (together with the tagging step in [8.3](#83-github-release-v010)) |

### 5.2 Operation checklist

| # | Actor | Action | Expected result | Acceptance check |
|---|---|---|---|---|
| 1 | 🤖 Automatic | At project import, RTD automatically installs a webhook (push event) on the GitHub repository | A readthedocs entry appears in the GitHub repository Settings → Webhooks | The entry is visible under Settings → Webhooks |
| 2 | 👤 User | **Verify**: `git push` to `main` from local → a new build appears automatically in RTD Builds | A build #N appears on the Builds page within ~1 minute of the push | Watch the Builds page refresh automatically |
| 3 | 👤 User | (Fallback only when the automatic webhook is missing) GitHub Settings → Webhooks → **Add webhook**: Payload URL = `https://readthedocs.org/api/v2/webhook/<slug>/<token>/` (slug and token are in the GitHub incoming webhook entry under RTD Admin → Integrations); Content type = `application/json`; event: select **Just the push event**; check Active | GitHub shows the webhook as created (testable via Recent Deliveries) | Send a test push → RTD triggers a build |
| 4 | 👤 User | (Per D6) RTD Admin → Advanced Settings → check **Build pull requests for this project** → Save | Pull request builds enabled | Create a PR → a build for that PR appears in RTD |
| 5 | 👤 User | (Per D6a) Confirm that pushing a tag triggers a build: `git tag v0.1.0 && git push origin v0.1.0` (run at the official release) | RTD builds version `v0.1.0` and `stable` automatically points to it | `v0.1.0` appears on the Versions page and the `stable` marker updates |

### 5.3 Notes

- If the automatic webhook does not appear, the most common cause is that the OAuth authorization did not grant repository webhook management permission — refresh the authorization in RTD Settings → Connected Accounts, or go straight to the manual fallback in step 3 (the manual fallback is **required**, otherwise pushes will not trigger builds).
- Testing the webhook (Recent Deliveries → Redeliver) is a quick troubleshooting method; a failed response body contains the cause.
- End-of-stage marker: all three events — push / tag / PR (as enabled per the decisions) — trigger builds automatically.

---

## 6. Item 5: Domain

### 6.1 Decision table

| Decision ID | Decision point | Options | Recommended | Consequence / Impact |
|---|---|---|---|---|
| D7 | Domain strategy | A. Use the RTD default subdomain `https://energytools-refactored.readthedocs.io/` (free, zero operations)<br>B. Custom domain (e.g. `docs.energytools.dev`; requires owning a domain + DNS operations) | **Choose A for the initial release**; choose B if you own a domain and want unified branding (can be enabled later) | A: no DNS operations needed; TLS is managed automatically by RTD. B: requires domain ownership, a CNAME record, and waiting for certificate issuance (minutes to hours); it can coexist with A (both stay valid) |
| D7a | (If B is chosen) Custom domain form | A. Subdomain `docs.energytools.dev`<br>B. Apex domain `energytools.dev` | **A. Subdomain** | A subdomain only needs one CNAME record; an apex domain requires the DNS provider to support CNAME flattening/ALIAS (some providers do not, and it can conflict with MX and other records) |
| D7b | (If B is chosen) TLS certificate | Issued automatically by RTD (Let's Encrypt) | Automatic | No user action needed; brief domain unavailability during issuance is normal |

### 6.2 Operation checklist (default subdomain, option A)

| # | Actor | Action | Expected result | Acceptance check |
|---|---|---|---|---|
| 1 | 🤖 Automatic | RTD provides `https://energytools-refactored.readthedocs.io/` for the project (with automatic TLS) | The domain is reachable | Browser access passes and the address bar shows the security lock |
| 2 | 👤 User | Put the default domain in the repository description and the README badge (drafts in [8.1](#81-github) / [8.2](#82-readme)) | External copy consistently points to the documentation address | The repository page description contains a clickable documentation link |

### 6.3 Operation checklist (custom domain, option B)

| # | Actor | Action | Expected result | Acceptance check |
|---|---|---|---|---|
| 1 | 👤 User | RTD Admin → **Domains** → Add Domain → enter `docs.energytools.dev` (per D7a) → note the CNAME target shown in the dialog | RTD shows the domain pending verification | The domain appears under Admin → Domains with status pending |
| 2 | 👤 User | Add a **CNAME** at the domain's DNS provider: `docs` → the target given in the RTD dialog (usually `readthedocs.io` or the project subdomain; **follow the dialog**); use the default TTL | DNS takes effect (can be self-tested with `nslookup docs.energytools.dev`) | Local/public DNS resolution results contain the CNAME target |
| 3 | 🤖 Automatic | RTD detects the CNAME → verifies domain ownership → issues a certificate via Let's Encrypt and configures https | The domain status becomes valid and https works | Status under Admin → Domains is valid; https access in the browser passes with a complete certificate chain |
| 4 | 👤 User | Acceptance: `https://docs.energytools.dev/en/latest/` and `https://energytools-refactored.readthedocs.io/en/latest/` are **both reachable** | Both domains work (the default subdomain remains after the custom domain is enabled) | Both URLs open |

### 6.4 Notes

- **The CNAME target is whatever the RTD add-domain dialog shows**; it may differ by period/region, so this document does not hard-code it.
- Certificate issuance usually completes within minutes; if it stays pending for several hours, check whether the CNAME is being interfered with by a CDN/proxy service (if you need a CDN, configure it per the RTD documentation).
- After the custom domain is enabled, the **default subdomain remains valid**; the custom domain can be removed in Domains at any time to roll back.
- End-of-stage marker: the default subdomain (required) or the custom domain (optional) is reachable over https.

---

## 7. Decision Table Summary

| Decision ID | Decision point | Recommended value | Consequence (if not followed) |
|---|---|---|---|
| D1 | Repository owner | Organization (or personal) | Migrating ownership requires changing the remote and the RTD connection |
| D2 | Repository visibility | **Public** | Private → RTD community edition unavailable; Business (paid) needed |
| D2a | Default branch | `main` | RTD `latest` follows another branch; extra configuration needed |
| D2b | Initialization content | Don't use GitHub's auto-generated README/license | Conflicts with local files and overwrites local content |
| D2c | Repository name | `energytools` | slug/URL inconsistency; renaming is costly |
| D3 | RTD sign-in | GitHub OAuth | Email registration requires a second GitHub connection |
| D3b | RTD edition | Community (free) | Business is paid; only needed for private repositories |
| D4 | Import method | Automatic import via connected account | Manual import requires adding the webhook |
| D4a | slug | `energytools` | If taken, rename; the domain changes accordingly |
| D4b | First build configuration | Depends on `.readthedocs.yaml` / `conf.py` delivered by the docs branch | First build fails if the configuration is not ready (expected) |
| D5 | webhook | Automatic install (manual fallback) | Without a webhook → pushes do not auto-build |
| D6 | Pull request builds | Enable | Disabled → PRs have no documentation preview |
| D6a | Trigger events | push + tag | Without tagging, `stable` does not update |
| D7 | Domain strategy | Default subdomain (custom can be added later) | Custom domain requires DNS operations and certificate waiting |
| D7a | Custom domain form | Subdomain `docs.…` | Apex domain requires CNAME flattening support |
| D7b | TLS | RTD automatic (Let's Encrypt) | None |

---

## 8. Repository Description and Release Announcement Drafts

### 8.1 GitHub repository description draft

**Main text (English, ≤350 characters, ready to use):**

> SIA 2024 energy tools — the Raumdatenblätter and Gebäude-Tool Excel workbooks reimplemented as a modern Python library. Install via pip/uv/pixi/conda; docs: https://energytools-refactored.readthedocs.io/

(About 200 characters, with room for one more line: `Pure-Python, Python ≥3.11, hatchling, src layout, extras: dev/api/mcp/data/export/docs.`)

**Alternative (for a repository described in Chinese):**

> A Python library reimplementation of the SIA 2024 energy calculation tools (Raumdatenblätter, Gebäude-Tool). Installable via pip / uv / pixi / conda; docs: https://energytools-refactored.readthedocs.io/

**Topics (20 max, 10 recommended):**

```
sia-2024  energy  building  raumdaten  gebaeude  excel-refactor  python  documentation  readthedocs  sphinx
```

(Consistent with the keywords in `pyproject.toml`: `sia-2024`, `energy`, `building`, `raumdaten`, `gebaeude`, `excel-refactor`, plus platform-related topics.)

### 8.2 README badge draft

Insert at the top of the README (below the title):

```markdown
[![Documentation Status](https://readthedocs.org/projects/energytools-refactored/badge/?version=latest)](https://energytools-refactored.readthedocs.io/en/latest/?badge=latest)
```

Effect: a documentation build status badge that links to the latest documentation. **Note**: the badge URL depends on slug = `energytools-refactored`; if the slug changes, it must be replaced accordingly.

### 8.3 GitHub Release announcement draft (v0.1.0)

**Tag**: `v0.1.0` (after pushing, RTD `stable` automatically points to this version; see Item 4, step 5)

**Release title**: `v0.1.0 — packaging scaffold & installation matrix`

**Body draft**:

```markdown
## What's in this release

First tagged release of **energytools** — the SIA 2024 energy tools
(Raumdatenblätter, Gebäude-Tool) reimplemented as a modern Python library.
This release establishes the packaging & tooling foundation; the OOP core
modules land in subsequent releases.

### Highlights
- PEP 621 package metadata with the hatchling backend (`src/` layout), Python ≥ 3.11
- Multi-toolchain install matrix: **pixi / uv / conda / pip** — see
  [docs/installation.md](docs/installation.md)
- Extras: `dev`, `api`, `mcp`, `data`, `export`, `docs`, `all`
- Console script: `energytools --version`
- Documentation pipeline (Sphinx + MyST) wired for Read the Docs —
  https://energytools-refactored.readthedocs.io/

### Install
    pip install -e ".[dev]"        # or: uv sync --extra dev / pixi install -e dev

### Known limitations
- Pre-alpha: placeholder package; runtime dependencies land with the core modules
- Not yet on PyPI (install from source / git checkout)

### Docs
https://energytools-refactored.readthedocs.io/en/latest/
```

### 8.4 Release announcement draft (external channel)

**Short version (one line):**

> energytools v0.1.0 released: a Python library reimplementation of the SIA 2024 energy calculation tools (Raumdatenblätter / Gebäude-Tool), with four install methods — pixi / uv / conda / pip. Docs: https://energytools-refactored.readthedocs.io/ 🎉

**Long version (internal/team announcement):**

> **energytools v0.1.0 has been released (Pre-Alpha)**
>
> This project reimplements the two SIA 2024 Excel workbooks — Raumdatenblätter and Gebäude-Tool — as a modern Python library. This release lays the packaging and toolchain foundation: PEP 621 metadata (hatchling), `src` layout, Python ≥ 3.11, all four install methods (pixi / uv / conda / pip), and a Sphinx + Read the Docs documentation pipeline.
>
> - Source and release notes: https://github.com/<owner>/energytools/releases/tag/v0.1.0
> - Documentation: https://energytools-refactored.readthedocs.io/
> - Installation guide: https://energytools-refactored.readthedocs.io/en/latest/installation.html
>
> Note: this is currently a scaffold version (Pre-Alpha); the OOP core modules will land in subsequent releases; PyPI publishing is arranged separately.

---

## 9. Master Acceptance Checklist

| # | Item | Acceptance action | Pass criteria | Status |
|---|---|---|---|---|
| 1 | GitHub repository | Open `https://github.com/<owner>/energytools` | Content matches local, description and topics filled in, default branch `main` | ☐ |
| 2 | RTD registration & connection | RTD Dashboard sign-in state | Signed in with GitHub, Connected Accounts contains GitHub | ☐ |
| 3 | Project import | RTD Builds page | Project `energytools` exists, build #1 has a record, version `latest` exists | ☐ |
| 4 | Default subdomain | Visit `https://energytools-refactored.readthedocs.io/en/latest/` | Opens over https with correct content | ☐ |
| 5 | webhook | Push to `main` | A new build appears automatically in Builds (≤1 minute) | ☐ |
| 6 | Tag build (per D6a) | `git push origin v0.1.0` | `v0.1.0` appears in Versions, `stable` points to it | ☐ |
| 7 | Pull request build (per D6) | Create a test PR | A PR preview build appears in RTD | ☐ |
| 8 | Custom domain (per D7, optional) | Visit `https://docs.energytools.dev/en/latest/` | Status valid, https certificate valid | ☐ (optional) |
| 9 | Repository description/badge | Check the repository page and README | Description in effect, badge shows passing | ☐ |
| 10 | Release | Publish the v0.1.0 Release | The Release page shows it, copy per 8.3 | ☐ |

---

## 10. Out-of-Scope and Follow-Up Items (not implemented in this branch)

| Item | Owner | Description |
|---|---|---|
| `.readthedocs.yaml`, Sphinx `conf.py`, docs documentation tree | Branches such as "documentation build and readthedocs publishing pipeline" and "rtd build pipeline completion and local verification" | This document does **not** create any configuration files |
| PyPI release (`pip install energytools` available worldwide) | Later release plan | Requires a PyPI account and Trusted Publishing or a token; this document only covers GitHub + RTD |
| CI (GitHub Actions testing/building) | Later plan | Not covered by this document |
| Private repository + private documentation | Only if requirements change | Requires Read the Docs for Business (paid) |
| Showcase integrations beyond the RTD badge (e.g. codecov) | Later plan | Not covered by this document |

---

## 11. Troubleshooting Quick-Reference Table

| Symptom | Possible cause | Investigation / remedy |
|---|---|---|
| RTD does not auto-build after a push | webhook missing or stale | Check the entry in GitHub Settings → Webhooks; if missing, create it manually per [5.2 step 3](#52); resend a test via Recent Deliveries |
| First build fails | `.readthedocs.yaml` / `conf.py` not ready | A delivery prerequisite of the "documentation build" branch, not a defect of this branch; check dependency installation and the build log |
| slug taken | `energytools-refactored.readthedocs.io` already used by someone else | Rename at import (e.g. `energytools-sia2024`) and update the URLs in 8.1/8.2 of this document accordingly |
| Custom domain stuck on pending | CNAME not effective / interfered with by a CDN | Check the record with `nslookup docs.energytools.dev`; compare with the RTD dialog target; wait and refresh |
| Badge shows unknown/404 | slug does not match the URL | Verify the slug in `readthedocs.org/projects/<slug>/badge/` |
| `stable` version not updated | No tag created or tag build failed | `git tag v0.1.0 && git push origin v0.1.0`; check the Versions page |
| Private repository import fails | Community edition does not support private repositories | Make it public, or evaluate Read the Docs for Business |

---

*This document is a pre-release operations document (platform/account actions only) and contains no development implementation; code and configuration files are implemented in the corresponding branches.*
