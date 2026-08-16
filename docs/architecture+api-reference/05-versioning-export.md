# API Reference — Versioning, Export & CLI

**Module:** `energytools` (root) + `energytools.raumdaten.service` · **Doc set 02 (API
Reference)** · Back to [index](README.md) · Foundation:
[02-common-foundation.md](02-common-foundation.md) · Data:
[03-raumdaten-service.md](03-raumdaten-service.md)

How versions work in practice, how to export data, and the command-line interface. The
versioning *primitives* (`DatasetRelease`, `ModelRelease`, `VersionInfo`, `VersionResolver`)
are documented in [02 § Classes](02-common-foundation.md#classes); this page is about using
them: the release lifecycle, `get_version()`, the CLI and the export surface.

> **Status.** The full export layer (`energytools.export`, CSV/XLSX/PDF exporters) and the CLI
> subcommands (`versions`, `export`, `serve`, `mcp`) are **planned**, not yet implemented. What
> works today: `get_version()`, `energytools --version`, and **JSON** export through
> `RaumdatenService.export` (part [03](03-raumdaten-service.md)).

---

## In this page

- [Quickstart](#quickstart) — get the version, export a release
- [Release lifecycle](#release-lifecycle) — how the four version axes evolve
- [CLI](#cli) — `energytools --version`
- [Export](#export) — what is available now and what is planned
- [What to import for a new project](#what-to-import-for-a-new-project)

---

<a id="1-distribution-root"></a>
<a id="11-__version__"></a>
<a id="12-get_version"></a>
## Quickstart

```python
import energytools
from energytools import get_version

print(energytools.__version__)          # '0.1.0'  (library version)
print(get_version())                    # VersionInfo(dataset='', model='', implementation='0.1.0', climate='')
```

The version **quadruple** `(dataset, model, implementation, climate)` makes every result,
export and API response reproducible. `get_version()` reports the newest installed release per
axis (see the layout note in [02](02-common-foundation.md#quickstart) — in a source checkout
with the canonical package layout the dataset/model axes are empty here, while
`RaumdatenService.list_releases()` resolves them).

From the command line:

```console
$ energytools --version
energytools 0.1.0
```

JSON export of a release (works today):

```python
from energytools.raumdaten import RaumdatenService

svc = RaumdatenService()
meta = svc.export("V221", fmt="json", scope="all", target="out/V221.json")
print(meta["bytes"], meta["checksum"])   # byte count + sha256 of the exported file
```

---

## Release lifecycle

The library treats data "released like software" (assessment §5.1). Four independent version
axes exist, and a calculation never combines them silently:

| Axis | Example | Convention |
|---|---|---|
| Dataset release | `V221` | Workbook-version id (`V221` → `V222` …). |
| Model release | `1.0.0` | Semantic versioning; `2.0.0` = breaking calculation graph. |
| Implementation | `0.1.0` | PEP 440 library version; never pinned by calculations. |
| Climate data | `meteoschweiz-2024` | External, versioned source. |

Rules that keep the axes consistent:

* A `ModelRelease` declares `compatible_dataset_releases`; the engine refuses combinations
  outside it (`ModelVersionMismatchError`, part [04](04-gebaeude-engine.md)).
* `resolve_dataset("latest")` is allowed **only** for read/display purposes;
  `Engine.calculate` records the resolved concrete ids in `Results.versions` before running.
* Dataset packages are immutable: a corrected release is a **new** release id with
  `supersedes` pointing at the old one — never an overwrite.

```python
from energytools.raumdaten import RaumdatenService

svc = RaumdatenService()
svc.list_releases()
# [{'id': 'V221', 'edition': 'SIA 2024', 'publication_date': '2024-11-17',
#   'checksum_sha256': '1267a9aa…', 'supersedes': None}]

svc.get_release("V221")["changelog"]
# [{'version': 'V221', 'date': '2024-11-17',
#   'change': 'Extracted by the energytools DatasetExtractor from the V221 …', 'migration': None}]
```

### Dataset release structure

A release is a directory with a `package.json` (the canonical package, JSON Schema
draft 2020-12, `schema_version: "1.0"`) plus a copy of the schema:

```text
data/datasets/V221/
├── package.json     # canonical package: release, room_uses, parameters, profiles,
│                    # climate, full_load_hours, qhc, sia3801, mappings, area_tables, …
└── schema.json      # copy of PACKAGE_SCHEMA (energytools.raumdaten.schema)
```

The package declares its own content checksum (`release.checksum_sha256`); the loader verifies
it and refuses corrupt or foreign packages (`DatasetValidationError`, part
[03](03-raumdaten-service.md)).

---

<a id="4-energytoolscli"></a>
<a id="41-main"></a>
<a id="42-versions_cmd"></a>
<a id="43-export_cmd"></a>
## CLI

### `energytools --version` ✅ (works today)

The console script `energytools` prints the library version:

```console
$ energytools --version
energytools 0.1.0
```

### Planned subcommands ⚙ (planned)

The full CLI will dispatch `versions`, `export`, `serve` and `mcp` subcommands. Today only
`--version` exists (running `energytools` with no arguments prints usage help):

```console
# planned (not yet implemented)
$ energytools versions --json          # {"dataset": "V221", "model": "1.0.0", ...}
$ energytools export V221 --fmt xlsx --scope all --target out/V221.xlsx
$ energytools serve --backend native --port 8000
$ energytools mcp
```

Programmatic entry points `energytools.cli.build_parser()` / `main(argv=None)` exist as the
scaffold behind `--version`.

---

<a id="3-energytoolsexport"></a>
<a id="31-exporter"></a>
<a id="32-jsonexporter"></a>
<a id="33-csvexporter"></a>
<a id="34-xlsxexporter"></a>
<a id="35-pdfexporter"></a>
<a id="36-export_dataset"></a>
<a id="37-export_calculation"></a>
## Export

### `RaumdatenService.export` ✅ (JSON today)

`def export(release_id: str, fmt: str, scope: str, target: str) -> dict`

Bulk export of a release. **`fmt="json"` is fully supported**; `csv` / `xlsx` / `pdf` raise
`ExportError` until the export layer lands.

```python
svc = RaumdatenService()
meta = svc.export("V221", "json", "room-uses", "out/room-uses.json")
meta
# {'release_id': 'V221', 'format': 'json', 'scope': 'room-uses',
#  'target': 'out/room-uses.json', 'bytes': 12345, 'checksum': 'ab12…'}
```

Scopes: `"room-uses"`, `"profiles"`, `"climate"`, `"full-load-hours"`, `"qhc"`, `"all"`.

**Raises:** `DatasetNotFoundError` (unknown release); `ExportError` (unsupported format or
scope, or a not-yet-implemented format).

### Planned export layer ⚙ (planned)

`energytools.export` will provide an `Exporter` contract plus `JsonExporter`,
`CsvExporter`, `XlsxExporter` and `PdfExporter` (the functional replacement of the workbook's
`DatenblattSpeichern` / `Res_Export` / `Volll_Lüft_Export` / `Qhc_Export` macros) and the
`export_dataset` / `export_calculation` facades — **semantic exporters** that render from the
domain model (no cell copying, no clipboard) and embed version + provenance metadata. Until
then, use `svc.export(..., fmt="json", ...)` for machine-readable output.

---

## What to import for a new project

```python
# Version info of the installed library
from energytools import __version__, get_version

# Resolve/query releases (see part 03 for the full data service)
from energytools.raumdaten import RaumdatenService

# JSON export
svc = RaumdatenService()
meta = svc.export("V221", fmt="json", scope="all", target="out/V221.json")
```

Typical flow: check `get_version()` / `energytools --version` to know what is installed →
query releases with `RaumdatenService.list_releases()` / `get_release()` → export JSON with
`svc.export(...)` → pass the loaded `Dataset` to the engine (part [04](04-gebaeude-engine.md)).
