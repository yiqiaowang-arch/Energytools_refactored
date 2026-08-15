# Installation Guide — pixi / uv / conda / pip

`energytools` is a plain Python package (PEP 621 metadata, hatchling build
backend, `src/` layout) and can be installed with **any** of the four major
toolchains. The repository ships the config for all of them:

| File | Role |
|---|---|
| `pyproject.toml` | Single source of metadata, dependencies and **extras** (optional groups). Consumed by pip and uv; mirrored by pixi/conda for tools. |
| `pixi.toml` | pixi manifest: conda-forge Python + **editable PyPI mapping** of `energytools`, feature environments, tasks. |
| `.python-version` | Python version hint for uv (and other tools that read it). |

Everything installs the same small placeholder package: importable
`energytools` with `__version__` / `get_version()`, plus the `energytools`
console script (`energytools --version`).

**Prerequisite for all methods:** Python ≥ 3.11 (3.13 recommended — see
[Troubleshooting](#6-troubleshooting) for why on Windows).

---

## 0. Extras (optional dependency groups)

| Extra | Contents | For |
|---|---|---|
| *(none)* | — | Core library (scaffold has no runtime deps yet) |
| `dev` | build, hatchling, mypy, pytest, pytest-cov, ruff | Contributing / running tests |
| `api` | fastapi, pydantic-settings, uvicorn | FastAPI layer |
| `mcp` | mcp | MCP adapter |
| `data` | pandas | Dataset model (`raumdaten`) |
| `export` | openpyxl, pandas | JSON/CSV/XLSX/PDF export |
| `docs` | mkdocs, mkdocs-material | Documentation builds (MkDocs site — see [deployment/readthedocs.md](deployment/readthedocs.md)) |
| `all` | everything above | Full install |

---

## 1. pixi (recommended for contributors)

[pixi](https://pixi.sh) manages the conda-forge interpreter **and** the PyPI
package in one environment file.

### 1.1 Install pixi

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm -useb https://pixi.sh/install.ps1 | iex"
# macOS / Linux
curl -fsSL https://pixi.sh/install.sh | bash
```

### 1.2 Install the environment

```bash
pixi install            # default env: python 3.13 + energytools (editable)
```

What happens: pixi creates `.pixi/`, solves `pixi.lock` against conda-forge
(Python) and PyPI (hatchling, then `energytools` as an **editable path
dependency** — equivalent to `pip install -e .`). `pixi.lock` is committed,
so environments are reproducible.

### 1.3 Environments

`pixi.toml` defines these environments (features mirror the pyproject extras):

| Environment | Contents | Create with |
|---|---|---|
| `default` | python + energytools | `pixi install` |
| `dev` | default + pytest, ruff, mypy, build | `pixi install -e dev` |
| `api` | default + fastapi, uvicorn, pydantic-settings | `pixi install -e api` |
| `docs` | default + mkdocs, mkdocs-material | `pixi install -e docs` |
| `full` | dev + api + docs | `pixi install -e full` |

Enter an environment with `pixi shell -e dev` (or use `pixi run -e dev`).

### 1.4 Tasks

```bash
pixi run version            # prints 0.1.0
pixi run smoke              # runs `energytools --version`
pixi run -e dev test        # python -m pytest (via -m, see troubleshooting)
pixi run -e dev lint        # ruff check .
pixi run -e dev format      # ruff format .
pixi run -e dev typecheck   # mypy src
pixi run -e dev build       # python -m build (sdist + wheel into dist/)
```

### 1.5 How the PyPI mapping works

```toml
[pypi-dependencies]
energytools = { path = ".", editable = true }
```

The repository itself is the only PyPI package in the default environment;
feature tools come from conda-forge. When the library later depends on
PyPI-only packages, add them to `[pypi-dependencies]` (or to feature-scoped
`[feature.<name>.pypi-dependencies]`) — pixi resolves them from PyPI next to
the conda packages.

---

## 2. uv

[uv](https://docs.astral.sh/uv) is a fast pip/venv replacement that reads
`pyproject.toml` directly.

### 2.1 Install uv

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# …or via pip / winget / scoop / brew
```

### 2.2 Project-style sync (recommended)

```bash
uv sync --extra dev        # creates .venv, installs energytools + dev extra
uv run energytools --version
```

`uv sync` honors `.python-version` (3.11) and generates/updates `uv.lock`
(commit it). Add more extras: `uv sync --extra api --extra docs`, or
`uv sync --all-extras` for everything.

### 2.3 Classic pip-style

```bash
uv venv .venv
uv pip install -e ".[dev]"
uv run python -c "import energytools; print(energytools.__version__)"
```

---

## 3. conda

`energytools` is a pure-Python package, so the conda workflow is a hybrid:
**conda provides the Python interpreter, pip installs the package** (the same
strategy pixi automates).

```bash
# create an environment with Python 3.13 (conda-forge recommended)
conda create -n energytools -c conda-forge python=3.13 pip
conda activate energytools

# install the package (editable, with the dev extra)
pip install -e ".[dev]"

# verify
python -c "import energytools; print(energytools.__version__)"
energytools --version
```

Notes:

- If you prefer a fully conda-managed setup (single solver, no pip), use
  **pixi** (section 1) — it is conda-forge-native and mirrors this workflow
  automatically.
- The package is not (yet) published on conda-forge; always install from
  source in a git checkout. Once published on PyPI, `pip install energytools`
  (non-editable, from any environment) also works.
- Native-extension tools (e.g. a future geospatial backend) belong in conda
  (`conda install gdal` etc.) — that is exactly why the hybrid exists.

---

## 4. pip

The baseline method — works with any Python ≥ 3.11 (3.13 recommended).

```bash
# create and activate a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# POSIX:    source .venv/bin/activate

# editable install with the dev extra (tests, linting, build)
pip install -e ".[dev]"

# plain install (runtime only) or with specific extras:
#   pip install -e .
#   pip install -e ".[api,mcp]"
#   pip install -e ".[all]"

# verify
python -c "import energytools; print(energytools.__version__)"
energytools --version
```

CLI-only users can install into an isolated environment without a venv:

```bash
pipx install .            # provides the `energytools` command
```

> On Windows, quote the extra: `pip install -e ".[dev]"` (PowerShell/cmd
> would otherwise interpret `[dev]`).

---

## 5. Verification (all toolchains)

After any install, these must succeed:

```bash
python -c "import energytools; print(energytools.__version__)"   # → 0.1.0
python -c "from energytools import get_version; print(get_version())"  # → 0.1.0
energytools --version                                             # → energytools 0.1.0
python -m pytest -q        # in dev environments → 3 passed
```

One-line equivalents per toolchain:

| Toolchain | Command |
|---|---|
| pixi | `pixi run smoke` and `pixi run -e dev test` |
| uv | `uv run energytools --version` and `uv run python -m pytest -q` |
| conda/pip | `energytools --version` and `python -m pytest -q` (inside the env) |

---

## 6. Troubleshooting

- **First `pixi install` is slow.** It downloads Python from conda-forge and
  hatchling from PyPI. Subsequent installs use the pixi cache
  (`~/.pixi` / `PIXI_HOME`).
- **Python dies at startup with `UnicodeDecodeError: 'charmap' …` when
  importing `site` (Windows, non-ASCII checkout path).** The editable install
  writes a `.pth` file containing the repository path; Python < 3.12.5 reads
  `.pth` files with the *locale* codec (e.g. cp1252), which cannot decode a
  path containing Chinese/other non-ANSI characters. Fixes:
  1. Use **Python 3.13** (or 3.12.5+): CPython [gh-77102](https://github.com/python/cpython/pull/117802)
     reads `.pth` as UTF-8 with locale fallback. The pixi manifest and
     `.python-version` already pin 3.13 for this reason; for conda/pip pick a
     3.13 interpreter as well.
  2. Or check the repository out to an ASCII-only path
     (e.g. `C:\src\energytools`).
  3. Or install non-editable (`pip install .`) until Python 3.13 is available.
- **`pytest.exe` launcher fails with `Cannot open …\pytest-script.py` on
  Windows (same non-ASCII path cause).** The distlib-style console-script
  launcher cannot handle the mangled path. Use `python -m pytest` instead
  (the pixi `test` task already does), or the ASCII-path fix above.
- **PyPI index blocked / corporate proxy.** Set
  `PIP_INDEX_URL` (or pixi's `PIXI_PYPI_INDEX_URL`) to a mirror and retry.
  For conda, add a mirror to `~/.condarc` / pixi channels.
- **`pip install -e .` rebuilds every time.** Editable installs re-run the
  hatchling build on each install; that is expected and fast.
- **`energytools` not found after install.** The editable install points at
  this repository — don't move/delete the checkout, and make sure the
  environment was activated (`pixi shell`, `conda activate`, `source .venv/bin/activate`).
- **Version mismatch between tools.** `__version__` lives in
  `src/energytools/__init__.py`; pyproject (`version = "0.1.0"`) and pixi.toml
  (`version = "0.1.0"`) must be bumped together on release.
