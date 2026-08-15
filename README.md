# energytools

SIA 2024 energy tools — the **Raumdatenblätter** and **Gebäude-Tool** Excel
workbooks — reimplemented as a Python library. This repository currently
provides the **packaging scaffold**: a minimal, installable placeholder
distribution with a full multi-toolchain setup.

## Requirements

- Python **≥ 3.11** (3.13 recommended — the pixi/uv environments pin 3.13)
- One of: [pixi](https://pixi.sh), [uv](https://docs.astral.sh/uv),
  [conda](https://docs.conda.io), or plain [pip](https://pip.pypa.io)

## Quick start

| Toolchain | Command |
|---|---|
| **pixi** (recommended) | `pixi install` → `pixi run smoke` |
| **uv** | `uv sync --extra dev` → `uv run energytools --version` |
| **conda** | `conda create -n energytools python=3.13 pip` → `pip install -e ".[dev]"` |
| **pip** | `python -m venv .venv` → `pip install -e ".[dev]"` |

Every method ends with an importable `energytools` package and a working
`energytools --version` console script. See
**[docs/installation.md](docs/installation.md)** for the complete guide:
environments, extras, tasks, verification and troubleshooting.

## Layout

```
pyproject.toml      PEP 621 manifest (hatchling backend, extras, tools config)
pixi.toml           pixi manifest (conda-forge python + editable PyPI mapping, tasks)
src/energytools/    placeholder package (importable, versioned, CLI entry point)
tests/              smoke tests for the scaffold
docs/installation.md  install guide covering pixi / uv / conda / pip
```

## Status

Pre-alpha scaffold. The OOP library architecture and API reference are
specified in the accompanying documentation sets; the placeholder package
will be replaced by the real modules.
