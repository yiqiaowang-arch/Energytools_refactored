# Part 05 — API Reference: Versioning & Export

**Document set 02** · Target-state design specification · Back to [index](README.md) ·
Inventory: [01-package-inventory.md](01-package-inventory.md) · Foundation:
[02-common-foundation.md](02-common-foundation.md)

This part covers the **versioning & export** concern of the library: the distribution root
(§1), the release-management workflow built on `VersionResolver` (§2), the export layer
`energytools.export` (§3) and the CLI (§4). Versioning primitives (`DatasetRelease`,
`ModelRelease`, `VersionInfo`, `ChangelogEntry`, `VersionResolver`) are defined in
[02 §2](02-common-foundation.md#2-energytoolscommonversioning); this part documents their use.

---

## 1. Distribution root

### 1.1 `__version__`

`__version__: str`

- **Purpose:** PEP 440 version of the installed library (e.g. `"0.1.0"`). Single source: the
  `pyproject.toml` version, imported at build time; used as `VersionInfo.implementation`.
- **Inputs:** —.
- **Outputs:** `str`.
- **Raises:** —.
- **Example:**
  ```python
  import energytools
  energytools.__version__            # '0.1.0'
  ```

### 1.2 `get_version`

`def get_version() -> VersionInfo`

- **Purpose:** Structured version info of the installed library: the library version plus the
  latest installed dataset and model releases and the climate version. Convenience wrapper
  around `VersionResolver.current()`.
- **Inputs:** —.
- **Outputs:** `VersionInfo` (`dataset`, `model`, `implementation`, `climate`).
- **Raises:** — (if no dataset is installed, `dataset` is `""`).
- **Example:**
  ```python
  from energytools import get_version
  get_version().as_dict()   # {'dataset': 'V221', 'model': '1.0.0', 'implementation': '0.1.0', …}
  ```

---

## 2. Versioning & release management

### 2.1 Release model (workflow)

- **Purpose:** Describe how the four version axes evolve and how the library keeps them
  consistent (assessment §5.1 "released like software").
- **Inputs:** —.
- **Outputs:** The release lifecycle below.
- **Raises:** —.
- **Example:** (release rules)
  ```text
  Dataset releases   V221 (SIA 2024) → V222 …      id convention from the workbook version
  Model releases     1.0.0 → 1.1.0 → 2.0.0        semantic versioning; 2.0.0 = breaking graph
  Implementation     0.1.0 …                       PEP 440; never pinned by calculations
  Climate data       meteoschweiz-2024 …           external, versioned source (assessment §8.6)
  ```
  * A `ModelRelease` declares `compatible_dataset_releases`; the engine refuses combinations
    outside it (`ModelVersionMismatchError`).
  * `VersionResolver.resolve_dataset("latest")` is allowed **only** for read/display purposes;
    `CalculationEngine.calculate` records the concrete resolved ids in `VersionInfo` before
    running.
  * Every export embeds the versions of the data it contains; exports of results embed the
    result's `VersionInfo`.
  * Dataset packages are immutable: a corrected release is a **new** release id with
    `supersedes` pointing at the old one (the `12.1`/`12.10` code quirk and the
    `…V221_20241117.xlsm` vs `…V221.xlsm` naming trap of assessment §8.8 are resolved by pinning
    the release id, never by overwriting).

### 2.2 `VersionResolver` (usage)

Full entry: [02 §2.5](02-common-foundation.md#25-versionresolver). Usage contract:

- **Purpose:** The only component that answers "which release is this id/alias?". Used by
  `RaumdatenService`, `CalculationEngine`, the FastAPI `versions` router, the MCP `get_versions`
  tool and the CLI `versions` command.
- **Inputs:** mapping of installed releases (constructed from the dataset/model directories at
  startup).
- **Outputs:** `DatasetRelease` / `ModelRelease` / `VersionInfo`.
- **Raises:** `DatasetNotFoundError` for unknown ids (including unknown aliases).
- **Example:**
  ```python
  from energytools.common.versioning import VersionResolver
  resolver = VersionResolver.from_installed(dataset_dir="data/datasets", model_dir="data/models")
  print(resolver.current())
  ```

---

## 3. `energytools.export`

Replaces the workbook export macros (`Res_Export`, `Volll_Lüft_Export`, `Qhc_Export`,
`DatenblattSpeichern` — see [01 §3.1](01-package-inventory.md#31-raumdatenblätter-raumdatenxlsm-34-modules))
with semantic exporters: **no cell copying, no filters, no clipboard**; exports are rendered
from the domain model. Every exporter embeds version + provenance metadata.

### 3.1 `Exporter`

`class Exporter(abc.ABC)`

- **Purpose:** Contract of all exporters: render one domain object (dataset release, table,
  calculation result) into bytes or a file, in one format.
- **Inputs (constructor):** `format: str` (e.g. `"json"`), `options: dict | None = None`
  (format-specific: pretty printing, sheet selection, language, value kind).
- **Attributes:** `format`, `options`.
- **Outputs:** — (exporter object; artifacts are returned by its methods).
- **Methods (abstract):**
  - **`export(data: object, target: str | None = None) -> ExportArtifact`** — renders `data`;
    writes to `target` when given. `ExportArtifact = (bytes, content_type, checksum_sha256,
    metadata)` dataclass. **Raises:** `ExportError`.
- **Raises:** constructor: —.
- **Example:**
  ```python
  artifact = JsonExporter().export(dataset, target="out/V221.json")
  print(artifact.checksum_sha256)
  ```

### 3.2 `JsonExporter`

`class JsonExporter(Exporter)`

- **Purpose:** Dataset release / table / result → JSON, annotated with the package JSON Schema
  `$schema` reference and embedded versions (the canonical interchange format, assessment §5.1).
- **Inputs (constructor):** `options: dict | None = None` (`{"indent": 2, "include_provenance":
  True}`).
- **Outputs:** `ExportArtifact` with `content_type = "application/json"`.
- **Raises:** `ExportError` for non-serializable data or unwritable target.
- **Example:**
  ```python
  JsonExporter({"include_provenance": False}).export(service.get_room_use_profile("V221", 1))
  ```

### 3.3 `CsvExporter`

`class CsvExporter(Exporter)`

- **Purpose:** Tabular views → CSV: room-use lists, parameter catalogs, profile matrices,
  full-load-hour tables, Qhc matrices, resultate tables (the workbook's TSV-like exports as
  standard CSV with a header row).
- **Inputs (constructor):** `options: dict | None = None` (`{"delimiter": ",", "language":
  "de", "value_kind": None}`).
- **Outputs:** `ExportArtifact` with `content_type = "text/csv"`.
- **Raises:** `ExportError` when the data is not tabular for the requested scope.
- **Example:**
  ```python
  CsvExporter({"language": "fr"}).export(service.list_room_uses("V221"), target="uses.csv")
  ```

### 3.4 `XlsxExporter`

`class XlsxExporter(Exporter)`

- **Purpose:** Dataset release / result → a single XLSX workbook with one sheet per table
  (Eingabedaten, Profile, Volll_Lüft, Qhc_Klimastat, Resultate …), including a metadata sheet
  (release, versions, checksums, provenance). Replaces the three export macros with one
  deterministic artifact; **not** a copy of the authoring workbook.
- **Inputs (constructor):** `options: dict | None = None` (`{"sheets": ["all"|…],
  "value_kind": None, "language": "de"}`).
- **Outputs:** `ExportArtifact` with `content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`.
- **Raises:** `ExportError` for unknown sheet names or write failures.
- **Example:**
  ```python
  XlsxExporter({"sheets": ["room-uses", "qhc"]}).export(dataset, target="V221.xlsx")
  ```

### 3.5 `PdfExporter`

`class PdfExporter(Exporter)`

- **Purpose:** Renders the 45 data sheets as PDFs (one file per room use, or one merged file) —
  the functional replacement of `DatenblattSpeichern` (assessment §1.3), with trilingual labels
  selected per option.
- **Inputs (constructor):** `options: dict | None = None` (`{"language": "de", "merged":
  False, "include_metadata": True}`).
- **Outputs:** `ExportArtifact` with `content_type = "application/pdf"` (single file when
  `merged`, else a zip of 45 PDFs).
- **Raises:** `ExportError` for rendering failures.
- **Example:**
  ```python
  PdfExporter({"language": "de", "merged": True}).export(dataset, target="Datenblatt.pdf")
  ```

### 3.6 `export_dataset`

`def export_dataset(service_or_dataset, release_id: str, fmt: str, scope: str, target: str) -> dict`

- **Purpose:** Convenience facade: resolves the release, selects the exporter by `fmt` and the
  scope view by `scope`, exports, returns metadata (used by `RaumdatenService.export` and the
  CLI `export` command).
- **Inputs:** `service_or_dataset` (`RaumdatenService` or `Dataset`), `release_id: str`,
  `fmt: str` (`"json" | "csv" | "xlsx" | "pdf"`), `scope: str` (`"room-uses" | "profiles" |
  "climate" | "full-load-hours" | "qhc" | "sia3801" | "all"`), `target: str` (file path).
- **Outputs:** `{"release_id", "format", "scope", "target", "bytes", "checksum_sha256",
  "versions"}`.
- **Raises:** `DatasetNotFoundError`, `ExportError` (unsupported format/scope, write failure).
- **Example:**
  ```python
  from energytools.export import export_dataset
  export_dataset(service, "V221", "xlsx", "all", "out/V221.xlsx")
  ```

### 3.7 `export_calculation`

`def export_calculation(result: CalculationResult, fmt: str, target: str) -> dict`

- **Purpose:** Convenience facade for result exports (resultate table, per-system AHU results,
  trace).
- **Inputs:** `result: CalculationResult`, `fmt: str` (`"json" | "csv" | "xlsx"`), `target:
  str`.
- **Outputs:** metadata dict as in 3.6 (plus `result_id`).
- **Raises:** `ExportError`.
- **Example:**
  ```python
  export_calculation(result, "json", "out/result.json")
  ```

---

## 4. `energytools.cli`

### 4.1 `main`

`def main(argv: list[str] | None = None) -> int`

- **Purpose:** CLI dispatcher with subcommands `versions`, `export`, `serve`, `mcp` (console
  entry point `energytools`).
- **Inputs:** `argv` (defaults to `sys.argv[1:]`).
- **Outputs:** exit code (0 ok, 2 usage error, 1 runtime error).
- **Raises:** — (errors are printed and mapped to exit codes).
- **Example:**
  ```console
  $ energytools versions
  $ energytools export V221 --fmt xlsx --scope all --target out/V221.xlsx
  $ energytools serve --backend native --port 8000
  $ energytools mcp
  ```

### 4.2 `versions_cmd`

`def versions_cmd(args: argparse.Namespace) -> int`

- **Purpose:** Prints the current `VersionInfo` (dataset, model, implementation, climate) and
  the installed releases with dates and checksums.
- **Inputs:** `args` (parsed arguments; `--json` for machine-readable output).
- **Outputs:** exit code 0; prints to stdout.
- **Raises:** —.
- **Example:**
  ```console
  $ energytools versions --json
  {"dataset": "V221", "model": "1.0.0", "implementation": "0.1.0", "climate": "meteoschweiz-2024"}
  ```

### 4.3 `export_cmd`

`def export_cmd(args: argparse.Namespace) -> int`

- **Purpose:** Exports a dataset release or a stored calculation result to a file
  (`export_dataset` / `export_calculation` facade).
- **Inputs:** `args` (`release_id` or `result_id`, `--fmt`, `--scope`, `--target`).
- **Outputs:** exit code 0 on success; prints the artifact checksum.
- **Raises:** — (errors printed, exit code 1).
- **Example:**
  ```console
  $ energytools export V221 --fmt csv --scope qhc --target qhc.csv
  wrote qhc.csv (12345 bytes, sha256 ab12…)
  ```
