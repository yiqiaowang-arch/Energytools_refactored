# Release Checklist (ReadTheDocs first launch)

> Status legend: `[ ]` to-do · `[x]` done
> This document targets the **first launch**. After that, routine releases only require pushing
> to the GitHub default branch; RTD rebuilds automatically.
> `RELEASE_CHECKLIST.md` at the repository root is the entry pointer to this document.

---

## 0. Prerequisite: repository content ready

- [ ] Code review passed: `mkdocs.yml`, `.readthedocs.yaml`, `requirements.txt` confirmed
- [ ] Local build passes: `mkdocs build` without errors (see README "Local build")
- [ ] The pages of the three main navigation sections (Architecture / Calculation Model / API
      Reference) are all registered in the `nav` of `mkdocs.yml`
- [ ] `site_url` and `repo_url` in `mkdocs.yml` set to the real addresses (see steps 1 and 3)

---

## 1. GitHub repository (user registration/creation required)

- [ ] Create a repository on GitHub, e.g. `energytools/energytools`
      (public repositories need no extra authorization; private repositories later require
      granting RTD read access)
- [ ] Push this repository to GitHub:

      ```bash
      git remote add origin https://github.com/<org>/<repo>.git
      git push -u origin main
      ```

- [ ] Set the default branch to `main` (Settings → Branches)
- [ ] Update `mkdocs.yml`: `repo_url` → real repository address
- [ ] Recommended: enable **Website** in the GitHub repository's About section pointing to
      `https://energytools-refactored.readthedocs.io/`

---

## 2. ReadTheDocs account (user registration required)

- [ ] Register a ReadTheDocs account: <https://readthedocs.org/accounts/signup/>
      (recommended: sign in directly with the **GitHub account**, which simplifies later
      linking and webhook management)
- [ ] Link GitHub: Settings → Connected Services → **Connect GitHub account**
      (authorizes repository import; grant all-repositories or organization-scoped access as
      needed)

---

## 3. Import the project (performed by the user after the account is linked)

- [ ] Log in to RTD → **Import a Project** → select the GitHub repository
- [ ] RTD automatically recognizes `.readthedocs.yaml` (no need to fill in the build
      configuration manually)
- [ ] Trigger the first build: Projects → `energytools` → **Builds** → Build version: `latest`
- [ ] Build succeeds; site address: `https://energytools-refactored.readthedocs.io/`
- [ ] Update `mkdocs.yml`: `site_url` → actual site address (affects search and SEO)

> If no integration was created automatically on import, check it manually (see step 4).

---

## 4. Webhook (automatic rebuild, user confirmation required)

- [ ] RTD project → **Admin → Integrations**, confirm a **GitHub incoming webhook** exists
      (usually created automatically when the project is imported)
- [ ] In the GitHub repository **Settings → Webhooks**, confirm the webhook exists and that the
      latest **delivery status is green (success)**
- [ ] Verify: push a commit to `main` and confirm RTD triggers a build automatically
      (a new build record appears under RTD project → Builds)

> If the webhook is missing: on the RTD Integrations page, manually **Add integration →
> GitHub incoming webhook**, then paste the generated URL into the GitHub repository's
> Webhooks.

---

## 5. Domain and appearance (optional, user action required)

- [ ] Custom domain: add it under RTD project → **Admin → Domains** (e.g.
      `docs.energytools.example.com`), and add a CNAME record at the DNS provider as prompted
- [ ] This site does not depend on GitHub Pages; no Pages configuration is needed in the GitHub
      repository

---

## 6. Versions and formal release (maintenance after the first launch)

- [ ] Create a release tag: GitHub → Releases → `v1.0.0` (or per semantic versioning rules)
- [ ] RTD project → **Versions** → set `v1.0.0` to **Active** and mark it as **stable**
- [ ] Use `https://energytools-refactored.readthedocs.io/en/stable/` consistently for external
      official links

---

## 7. Final checks

- [ ] The three main sections of the site are accessible: Architecture / Calculation Model /
      API Reference
- [ ] Search works correctly (built into the Material theme)
- [ ] Commit this checklist update: tick the completed items and push

---

## FAQ

| Symptom | Handling |
| ---- | ---- |
| Build fails: `mkdocs not found` | Check that `requirements.txt` is referenced by `.readthedocs.yaml` and committed |
| Build fails: YAML syntax error | Make a local `mkdocs build` pass first, then push |
| No automatic build after push | See step 4: check the webhook and the GitHub integration authorization |
| Private repository cannot be imported | When linking GitHub, grant read access to the corresponding organization/repository |
| Want to change the site subpath | RTD project → Admin → Advanced settings → `Default branch` etc. |

---

*Maintainer: project team · Generated: 2025 (update at first launch)*
