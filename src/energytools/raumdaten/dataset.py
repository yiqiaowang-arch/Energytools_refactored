"""energytools.raumdaten.dataset -- loading, store and extraction (API reference part 03, section 2).

Loading (`load_dataset`, `DatasetStore`): JSON package + JSON Schema -> frozen
:class:`~energytools.raumdaten.model.Dataset`.  Extraction (`DatasetExtractor`):
stage-0 pipeline that reads a **copy** of the source workbook deterministically
(cell graph: values + formulas + cached results), checksums it, validates the
result against the package JSON Schema and writes the canonical JSON package.
No cell is written, no macro runs, no link is followed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from energytools.common.errors import (
    DatasetNotFoundError,
    DatasetValidationError,
    UnitError,
)
from energytools.common.language import TrilingualText
from energytools.common.provenance import Provenance, SourceRef
from energytools.common.units import Quantity, Unit
from energytools.common.versioning import ChangelogEntry, DatasetRelease
from energytools.raumdaten.model import (
    AreaTable,
    BuildingCategoryMapping,
    ClimateData,
    ClimateStation,
    Dataset,
    FullLoadHoursTable,
    HourlyProfile,
    MonthlyProfile,
    Parameter,
    ParameterValue,
    QhcTable,
    RoomUse,
    RoomUseProfile,
    Sia3801Result,
    ValueKind,
    normalize_room_use_code,
)
from energytools.raumdaten.schema import PACKAGE_SCHEMA

__all__ = ["DEFAULT_DATASET_DIR_ENV", "DatasetExtractor", "DatasetStore", "load_dataset"]

DEFAULT_DATASET_DIR_ENV = "ENERGYTOOLS_DATASET_DIR"
_RELEASE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# Process-wide cache: (release_id, dataset_dir) -> Dataset.  Enforces the
# invariant "one frozen Dataset per release id" per dataset directory.
_LOAD_CACHE: dict[tuple[str, str], Dataset] = {}


def default_dataset_dir() -> str:
    """The configured dataset directory (``ENERGYTOOLS_DATASET_DIR`` or ``./data/datasets``)."""
    return os.environ.get(DEFAULT_DATASET_DIR_ENV, "data/datasets")


def _canonical_bytes(data: dict) -> bytes:
    """Deterministic canonical JSON bytes (checksum basis)."""
    return json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _content_checksum(data: dict) -> str:
    """SHA-256 of the canonical package content, excluding the checksum field itself."""
    without_checksum = json.loads(json.dumps(data))
    release = without_checksum.get("release")
    if isinstance(release, dict):
        release.pop("checksum_sha256", None)
    return hashlib.sha256(_canonical_bytes(without_checksum)).hexdigest()


def _schema_errors(instance: Any) -> list[str]:
    """Human-readable JSON-Schema validation errors (empty when valid)."""
    # Lazily imported: jsonschema is part of the 'data' extra.
    import jsonschema  # type: ignore[import-untyped]

    validator = jsonschema.Draft202012Validator(PACKAGE_SCHEMA)
    return sorted(
        f"{list(error.path) or ['<root>']}: {error.message}"
        for error in validator.iter_errors(instance)
    )


def _require_jsonschema() -> None:
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        raise ImportError(
            "jsonschema is required to load dataset packages; "
            "install it with `pip install 'energytools[data]'`"
        ) from None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_dataset(release_id: str, path: str | None = None) -> Dataset:
    """Load a dataset release from disk (JSON package + JSON Schema).

    Results are cached in the process-wide :class:`DatasetStore`; subsequent
    calls with the same ``release_id`` (and dataset directory) return the
    identical frozen object.

    Args:
        release_id: Release id (e.g. ``"V221"``).
        path: Directory of the package; defaults to the configured dataset
            directory (``ENERGYTOOLS_DATASET_DIR`` or ``./data/datasets``).

    Raises:
        DatasetNotFoundError: release not installed.
        DatasetValidationError: package fails schema/checksum/content validation
            (a corrupt/foreign package is never half-loaded).
    """
    dataset_dir = path or default_dataset_dir()
    return DatasetStore(dataset_dir).get(release_id)


class DatasetStore:
    """Process-wide registry of loaded releases.

    Enforces the invariant "one frozen :class:`Dataset` per release id" and
    answers existence queries without touching disk.

    Args:
        dataset_dir: Root of installed packages (defaults to the configured
            dataset directory).
    """

    def __init__(self, dataset_dir: str | None = None) -> None:
        self.dataset_dir = dataset_dir or default_dataset_dir()

    # -- public API ---------------------------------------------------------

    def get(self, release_id: str) -> Dataset:
        """Load-on-demand (via :func:`load_dataset` semantics), cached.

        Raises:
            DatasetNotFoundError: release not installed.
            DatasetValidationError: package fails validation.
        """
        self._check_release_id(release_id)
        key = (release_id, os.path.abspath(self.dataset_dir))
        cached = _LOAD_CACHE.get(key)
        if cached is not None:
            return cached
        dataset = self._load_from_disk(release_id)
        _LOAD_CACHE[key] = dataset
        return dataset

    def list(self) -> list[DatasetRelease]:
        """Installed releases (from package manifests), newest first."""
        releases = []
        root = Path(self.dataset_dir)
        if not root.is_dir():
            return []
        for package_file in sorted(root.glob("*/package.json")):
            try:
                data = json.loads(package_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue  # a corrupt package is skipped here; get() reports it properly
            release = data.get("release")
            if not isinstance(release, dict) or not release.get("id"):
                continue
            try:
                releases.append(_release_from_dict(release))
            except (KeyError, TypeError, ValueError):
                continue
        return sorted(releases, key=lambda rel: (rel.publication_date, rel.id), reverse=True)

    def register(self, dataset: Dataset) -> None:
        """Pre-register an in-memory dataset (tests, custom packages).

        Raises:
            ValueError: on a duplicate id with different content.
        """
        key = (dataset.release_id, os.path.abspath(self.dataset_dir))
        existing = _LOAD_CACHE.get(key)
        if existing is not None and existing != dataset:
            raise ValueError(
                f"dataset release '{dataset.release_id}' is already registered with different content"
            )
        _LOAD_CACHE[key] = dataset

    def refresh(self) -> None:
        """Drop the cache and re-scan the dataset directory."""
        prefix = os.path.abspath(self.dataset_dir)
        for key in [k for k in _LOAD_CACHE if k[1] == prefix]:
            del _LOAD_CACHE[key]

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _check_release_id(release_id: str) -> None:
        if not release_id or not _RELEASE_ID_RE.match(release_id):
            raise DatasetValidationError(
                f"invalid release id '{release_id}' (allowed: letters, digits, '.', '_', '-')",
                {"release_id": release_id},
            )

    def _load_from_disk(self, release_id: str) -> Dataset:
        release_dir = Path(self.dataset_dir) / release_id
        package_file = release_dir / "package.json"
        if not package_file.is_file():
            raise DatasetNotFoundError(release_id)

        _require_jsonschema()

        try:
            data = json.loads(package_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DatasetValidationError(
                f"package '{release_id}' is not valid JSON: {exc}",
                {"release_id": release_id, "errors": [str(exc)]},
            ) from exc
        except OSError as exc:
            raise DatasetValidationError(
                f"package '{release_id}' cannot be read: {exc}",
                {"release_id": release_id, "errors": [str(exc)]},
            ) from exc

        errors = _schema_errors(data)
        if errors:
            raise DatasetValidationError(
                f"package '{release_id}' fails schema validation",
                {"release_id": release_id, "errors": errors},
            )

        expected_checksum = data.get("release", {}).get("checksum_sha256")
        actual_checksum = _content_checksum(data)
        if expected_checksum and expected_checksum.lower() != actual_checksum.lower():
            raise DatasetValidationError(
                f"package '{release_id}' checksum mismatch "
                f"(expected {expected_checksum}, computed {actual_checksum})",
                {"release_id": release_id, "errors": ["checksum mismatch"]},
            )

        try:
            return Dataset.from_package_dict(data)
        except (ValueError, TypeError, KeyError) as exc:
            raise DatasetValidationError(
                f"package '{release_id}' has inconsistent content: {exc}",
                {"release_id": release_id, "errors": [str(exc)]},
            ) from exc


def _release_from_dict(data: dict) -> DatasetRelease:
    from datetime import date

    return DatasetRelease(
        id=data["id"],
        edition=data["edition"],
        publication_date=date.fromisoformat(data["publication_date"]),
        checksum_sha256=data["checksum_sha256"],
        source_workbook=data["source_workbook"],
        extraction_tool_version=data["extraction_tool_version"],
        supersedes=data.get("supersedes"),
        changelog=tuple(
            ChangelogEntry(
                version=entry["version"],
                date=date.fromisoformat(entry["date"]),
                change=entry["change"],
                migration=entry.get("migration"),
            )
            for entry in data.get("changelog", [])
        ),
    )


# ---------------------------------------------------------------------------
# Extraction (stage 0)
# ---------------------------------------------------------------------------

# Standard versions of the Volll_Lüft table (assessment 1.2).  V221 ships one
# version block; the version axis is the model for the dataset's evolution.
STANDARD_VERSIONS = ("SIA 2024:2015", "prSIA 2024:2021", "prSIA 2024-C1:2024")
REQUIRED_SHEETS = (
    "Eingabedaten",
    "Begriffe",
    "Datenblatt",
    "Profile",
    "Monatswerte",
    "Winter_Auslegung",
    "Volll_Lüft",
    "Qhc_Klimastat",
    "Fläche-E",
    "GEPAMOD",
    "SIA 380-1",
)

_SECTION_HEADERS = (
    "Raum",
    "Bauphysikalische Eigenschaften",
    "Raumklima",
    "Schallschutz",
    "Personen",
    "Geräte und Prozessanlagen",
    "Beleuchtung",
    "Lüftung",
    "Raumkühlung",
    "Befeuchtung",
    "Raumheizung",
    "Wasser",
)

_ERROR_VALUE_STRINGS = {"#N/A", "#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "Fehler"}

# Monatswerte: 11-row blocks per station, starting at rows 1, 12, 23, ...
_MONTHLY_BLOCK_UNITS = {
    "t_aussen": "°C",
    "radiation_horizontal": "MJ/m2",
    "radiation_east": "MJ/m2",
    "radiation_south": "MJ/m2",
    "radiation_west": "MJ/m2",
    "radiation_north": "MJ/m2",
    "precipitation": "mm",
    "mixing_ratio": "g/kg",
    "absolute_humidity": "g/m3",
}


class DatasetExtractor:
    """Stage-0 extraction pipeline (assessment 7.1).

    Reads a **copy** of the source workbook deterministically (cell graph:
    values + formulas + cached results), checksums it, validates against the
    package JSON Schema and writes the canonical JSON package + manifest.

    Args:
        workbook_path: Path to a **copy** of ``2024_Raumdatenblätter_dfi_V221.xlsm``.
        output_dir: Directory the release package is written to.
        release_id: Release id of the produced package.
        extraction_tool_version: Version of this extraction tool (required).
        standard_version: Standard version tag of the extracted ``Volll_Lüft``
            block (V221 ships ``prSIA 2024-C1:2024``).

    Raises:
        FileNotFoundError: when the workbook copy does not exist (constructor).
    """

    def __init__(
        self,
        workbook_path: str,
        output_dir: str,
        release_id: str = "V221",
        *,
        extraction_tool_version: str,
        standard_version: str = "prSIA 2024-C1:2024",
    ) -> None:
        self.workbook_path = workbook_path
        self.output_dir = output_dir
        self.release_id = release_id
        self.extraction_tool_version = extraction_tool_version
        self.standard_version = standard_version
        if not os.path.isfile(workbook_path):
            raise FileNotFoundError(f"workbook copy not found: {workbook_path}")

    # -- pipeline -----------------------------------------------------------

    def extract(self) -> DatasetRelease:
        """Run the pipeline and return the release metadata of the written package.

        Raises:
            DatasetValidationError: unexpected sheet layout, missing required
                tables, unknown value kinds.
            OSError: unreadable copy.
        """
        try:
            # Lazily imported: openpyxl is part of the 'data' extra.
            import openpyxl  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "openpyxl is required for workbook extraction; "
                "install it with `pip install 'energytools[data]'`"
            ) from None

        workbook_name = os.path.basename(self.workbook_path)
        source_checksum = self._checksum_file(self.workbook_path)

        # Two deterministic reads of the cell graph: formulas + cached results.
        wb_formulas = openpyxl.load_workbook(self.workbook_path, data_only=False, read_only=True)
        try:
            wb_values = openpyxl.load_workbook(self.workbook_path, data_only=True, read_only=True)
            try:
                self._check_layout(wb_values)
                package = self._build_package(
                    wb_values, wb_formulas, workbook_name, source_checksum
                )
            finally:
                wb_values.close()
        finally:
            wb_formulas.close()

        errors = _schema_errors(package)
        if errors:
            raise DatasetValidationError(
                f"extracted package for '{self.release_id}' fails schema validation",
                {"release_id": self.release_id, "errors": errors},
            )

        # Content validation: a corrupt/foreign extraction is never written.
        self._to_dataset(package)
        package["release"]["checksum_sha256"] = _content_checksum(package)
        release = _release_from_dict(package["release"])

        release_dir = Path(self.output_dir) / self.release_id
        release_dir.mkdir(parents=True, exist_ok=True)
        package_file = release_dir / "package.json"
        package_file.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        schema_file = release_dir / "schema.json"
        schema_file.write_text(
            json.dumps(PACKAGE_SCHEMA, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return release

    # -- workbook parsing ---------------------------------------------------

    @staticmethod
    def _checksum_file(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _check_layout(self, wb: Any) -> None:
        missing = [name for name in REQUIRED_SHEETS if name not in wb.sheetnames]
        if missing:
            raise DatasetValidationError(
                f"workbook copy has unexpected sheet layout; missing required sheets: {missing}",
                {"release_id": self.release_id, "errors": [f"missing sheets: {missing}"]},
            )

    def _build_package(
        self, wb_values: Any, wb_formulas: Any, workbook_name: str, source_checksum: str
    ) -> dict:
        room_uses = self._extract_room_uses(wb_values["Eingabedaten"], wb_values["Begriffe"])
        by_nutzid = {room_use.nutzid: room_use for room_use in room_uses}
        by_code = {room_use.code: room_use for room_use in room_uses}
        catalog, selected_nutzid = self._extract_parameters(
            wb_values["Datenblatt"], wb_values["Begriffe"], by_nutzid
        )
        profiles, merged_catalog = self._extract_profiles(
            wb_values["Eingabedaten"], catalog, by_nutzid
        )
        climate = self._extract_climate(wb_values["Winter_Auslegung"], wb_values["Monatswerte"])
        full_load_hours = self._extract_full_load_hours(wb_values["Volll_Lüft"], by_code)
        qhc = self._extract_qhc(wb_values["Qhc_Klimastat"], by_code)
        hourly_profiles = self._extract_hourly_profiles(wb_values["Profile"])
        mappings, area_tables = self._extract_mappings_and_areas(
            wb_values["Fläche-E"], wb_values["GEPAMOD"], by_code
        )
        sia3801 = self._extract_sia3801(wb_values, by_nutzid, selected_nutzid, climate)

        return {
            "schema_version": "1.0",
            "source_checksum_sha256": source_checksum,
            "release": {
                "id": self.release_id,
                "edition": "SIA 2024",
                "publication_date": "2024-11-17",
                "checksum_sha256": "0" * 64,  # placeholder; replaced once content is final
                "source_workbook": workbook_name,
                "extraction_tool_version": self.extraction_tool_version,
                "supersedes": None,
                "changelog": [
                    {
                        "version": self.release_id,
                        "date": "2024-11-17",
                        "change": (
                            "Extracted by the energytools DatasetExtractor from the V221 "
                            "Raumdatenblätter workbook copy."
                        ),
                        "migration": None,
                    }
                ],
            },
            "room_uses": [room_use.as_dict() for room_use in room_uses],
            "parameters": [parameter.as_dict() for parameter in merged_catalog],
            "profiles": [
                {
                    "nutzid": nutzid,
                    "values": {
                        parameter_id: {
                            kind.value: value.as_dict() for kind, value in by_kind.items()
                        }
                        for parameter_id, by_kind in profile.values.items()
                    },
                }
                for nutzid, profile in sorted(profiles.items())
            ],
            "hourly_profiles": [profile.as_dict() for profile in hourly_profiles],
            "monthly_profiles": [
                profile.as_dict()
                for station in climate.stations
                for profile in station.monthly.values()
            ],
            "weekly_profiles": [],
            "climate": climate.as_dict(),
            "full_load_hours": full_load_hours.as_dict(),
            "qhc": qhc.as_dict(),
            "sia3801": [result.as_dict() for result in sia3801],
            "mappings": [mapping.as_dict() for mapping in mappings],
            "area_tables": [table.as_dict() for table in area_tables],
            "sia3801_coefficients": [],
        }

    def _to_dataset(self, package: dict) -> Dataset:
        try:
            return Dataset.from_package_dict(package)
        except (ValueError, TypeError, KeyError) as exc:
            raise DatasetValidationError(
                f"extracted package for '{self.release_id}' has inconsistent content: {exc}",
                {"release_id": self.release_id, "errors": [str(exc)]},
            ) from exc

    # -- table extractors ---------------------------------------------------

    @staticmethod
    def _extract_room_uses(ws: Any, ws_begriffe: Any) -> list[RoomUse]:
        """``Eingabedaten!A9:C53`` (codes + German names), joined with ``Begriffe`` names."""
        name_map: dict[str, TrilingualText] = {}
        for row in ws_begriffe.iter_rows(min_row=134, max_row=178, min_col=2, max_col=5):
            if row[0].value is None:
                continue
            de = str(row[1].value or "").strip()
            if de:
                name_map[_normalize_label(de)] = TrilingualText(
                    de=de,
                    fr=str(row[2].value or "").strip(),
                    it=str(row[3].value or "").strip(),
                )
        room_uses = []
        for row_index, row in enumerate(
            ws.iter_rows(min_row=9, max_row=53, min_col=1, max_col=3), start=9
        ):
            code_raw = row[0].value
            de_name = str(row[2].value or "").strip()
            if code_raw is None or not de_name:
                continue
            code = normalize_room_use_code(str(code_raw).strip())
            category = int(code.split(".")[0])
            nutzid = row_index - 8
            name = name_map.get(_normalize_label(de_name), TrilingualText(de=de_name))
            room_uses.append(RoomUse(nutzid=nutzid, code=code, category=category, name=name))
        return room_uses

    def _extract_parameters(
        self, ws: Any, ws_begriffe: Any, by_nutzid: dict[int, RoomUse]
    ) -> tuple[list[Parameter], int]:
        """``Datenblatt`` rows 4-196; ids from ``Begriffe`` Ziffern or documented slugs."""
        ziffer_by_label: dict[str, str] = {}
        for row in ws_begriffe.iter_rows(min_row=25, max_row=127, min_col=2, max_col=3):
            ziffer = row[0].value
            label = row[1].value
            if ziffer and label:
                ziffer_by_label.setdefault(_normalize_label(str(label)), str(ziffer).strip())

        nutzid_cell = _cell(ws, 1, 3)
        selected_nutzid = int(nutzid_cell) if nutzid_cell not in (None, "") else 1
        if selected_nutzid not in by_nutzid:
            raise DatasetValidationError(
                f"unexpected sheet layout: Datenblatt!C1 nutzid {selected_nutzid} is not in 1..45",
                {"release_id": self.release_id, "errors": [f"nutzid {selected_nutzid} unknown"]},
            )

        parameters: list[Parameter] = []
        used_ids: set[str] = set()
        used_symbols: set[str] = set()
        category = ""
        for row_index, row in enumerate(
            ws.iter_rows(min_row=4, max_row=196, min_col=1, max_col=19), start=4
        ):
            section = row[0].value
            if isinstance(section, str) and section.strip() in _SECTION_HEADERS:
                category = section.strip()
            label = row[2].value
            if not isinstance(label, str) or not label.strip():
                continue
            label = label.strip()
            symbol = str(row[8].value or "").strip()
            unit = _safe_unit(str(row[9].value or ""))
            values_raw = (row[12].value, row[13].value, row[14].value)
            flags = tuple(_to_bool(row[idx].value) for idx in (15, 16, 17, 18))

            parameter_id = self._parameter_id(
                label, symbol, ziffer_by_label, used_ids, used_symbols
            )
            value_kinds = tuple(
                kind
                for kind, raw in zip(
                    (ValueKind.STANDARD, ValueKind.ZIELWERT, ValueKind.BESTAND), values_raw
                )
                if raw is not None
            )
            data_type = _infer_data_type(values_raw)
            parameters.append(
                Parameter(
                    id=parameter_id,
                    label=TrilingualText(de=label),
                    symbol=symbol,
                    unit=unit,
                    data_type=data_type,
                    category=category,
                    value_kinds=frozenset(value_kinds)
                    if value_kinds
                    else frozenset({ValueKind.STANDARD}),
                    export_flag=flags[0],
                    display_flag=flags[1],
                    internal_heat_flag=flags[2],
                    qhc_flag=flags[3],
                    provenance=Provenance(
                        sources=(
                            SourceRef(
                                workbook=os.path.basename(self.workbook_path),
                                sheet="Datenblatt",
                                range=f"A{row_index}:S{row_index}",
                            ),
                        )
                    ),
                )
            )
        return parameters, selected_nutzid

    def _parameter_id(
        self,
        label: str,
        symbol: str,
        ziffer_by_label: dict[str, str],
        used_ids: set[str],
        used_symbols: set[str],
    ) -> str:
        base = ziffer_by_label.get(_normalize_label(label))
        if base is None:
            if symbol and symbol not in ("-", "–", "—") and symbol not in used_symbols:
                base = symbol
            else:
                base = _slugify(label)
        # Sub-case rows (symbol ends with ",C" / ",H", e.g. qi,des,C) get a suffix.
        if re.search(r",[CH]$", symbol):
            base = f"{base}.{symbol[-1]}"
        candidate = base
        counter = 2
        while candidate in used_ids:
            candidate = f"{base}-{counter}"
            counter += 1
        used_ids.add(candidate)
        if symbol and symbol not in ("-", "–", "—"):
            used_symbols.add(symbol)
        return candidate

    def _extract_profiles(
        self, ws: Any, catalog: list[Parameter], by_nutzid: dict[int, RoomUse]
    ) -> tuple[dict[int, RoomUseProfile], list[Parameter]]:
        """Per-room-use values from the ``Eingabedaten`` master matrix (rows 9-53).

        Returns the profiles and the merged parameter catalog (Datenblatt
        parameters plus matrix-only parameters referenced by the profiles).
        """
        catalog_by_label: dict[str, list[Parameter]] = {}
        for catalog_parameter in catalog:
            catalog_by_label.setdefault(_normalize_label(catalog_parameter.label.de), []).append(
                catalog_parameter
            )

        raw_parameters: dict[str, Parameter] = {}
        raw_values: dict[str, dict[int, dict[ValueKind, Any]]] = {}

        max_col = ws.max_column or 1
        name_by_col: dict[int, str] = {}
        kind_by_col: dict[int, str] = {}
        unit_by_col: dict[int, str] = {}
        for row in ws.iter_rows(min_row=6, max_row=8, min_col=4, max_col=max_col):
            for cell in row:
                if cell.value is None or not str(cell.value).strip():
                    continue
                if cell.row == 6:
                    name_by_col[cell.column] = str(cell.value).strip()
                elif cell.row == 7:
                    kind_by_col[cell.column] = str(cell.value).strip()
                else:
                    unit_by_col[cell.column] = str(cell.value).strip()
        # Read the value matrix once (rows 9-53, columns D..max); pads short
        # sheets (e.g. synthetic test workbooks) with empty rows.
        matrix = [
            [cell.value for cell in row]
            for row in ws.iter_rows(min_row=9, max_row=53, min_col=4, max_col=max_col)
        ]
        if len(matrix) < 45:
            matrix.extend([None] * (max_col - 3) for _ in range(45 - len(matrix)))

        col = 4  # column D
        while col <= max_col:
            name = name_by_col.get(col)
            if not name:
                col += 1
                continue
            kind_text = kind_by_col.get(col, "")  # row-7 kind of this column
            unit = _safe_unit(unit_by_col.get(col, "-"))
            matches = catalog_by_label.get(_normalize_label(name), [])

            kinds: tuple[ValueKind, ...]
            if kind_text == "Standard" and col + 2 <= max_col:
                group = [col, col + 1, col + 2]
                kinds = (ValueKind.STANDARD, ValueKind.ZIELWERT, ValueKind.BESTAND)
                col += 3
                sub_kind = None
            else:
                group = [col]
                kinds = (ValueKind.STANDARD,)
                sub_kind = {"Kühlfall": ".C", "Heizfall": ".H"}.get(kind_text)
                col += 1

            parameter: Parameter | None = self._match_parameter(matches, sub_kind, name, unit)
            if parameter is None:
                parameter_id = _slugify(name) + (sub_kind or "")
                parameter = Parameter(
                    id=parameter_id,
                    label=TrilingualText(de=name),
                    symbol="",
                    unit=unit,
                    data_type="number",
                    category="",
                    value_kinds=frozenset(kinds),
                )
            raw_parameters[parameter.id] = parameter
            for nutzid in range(1, 46):
                row_values = matrix[nutzid - 1]
                for offset, kind in enumerate(kinds):
                    cell_value = row_values[group[offset] - 4]
                    raw_values.setdefault(parameter.id, {}).setdefault(nutzid, {})[kind] = (
                        _clean_cell_value(cell_value)
                    )

        catalog_dict = {parameter.id: parameter for parameter in catalog}
        for parameter_id, parameter in raw_parameters.items():
            if parameter_id not in catalog_dict:
                catalog_dict[parameter_id] = parameter

        profiles: dict[int, RoomUseProfile] = {}
        for nutzid, room_use in by_nutzid.items():
            values = {}
            for parameter_id, by_nutzid_values in raw_values.items():
                by_kind = by_nutzid_values.get(nutzid, {})
                values[parameter_id] = {
                    kind: ParameterValue(
                        parameter_id=parameter_id,
                        kind=kind,
                        value=value,
                        unit=catalog_dict[parameter_id].unit,
                    )
                    for kind, value in by_kind.items()
                    if value is not None
                }
            profiles[nutzid] = RoomUseProfile(
                room_use=room_use,
                values=values,
                parameter_catalog=catalog_dict,
            )
        return profiles, list(catalog_dict.values())

    @staticmethod
    def _match_parameter(
        matches: list[Parameter], sub_kind: str | None, name: str, unit: str
    ) -> Parameter | None:
        """Pick the catalog parameter matching a matrix column (label + sub-case)."""
        for parameter in matches:
            if sub_kind is not None:
                if parameter.id.endswith(sub_kind):
                    return parameter
            elif not re.search(r",[CH]$", parameter.symbol) and not parameter.id.endswith(
                (".C", ".H")
            ):
                return parameter
        if matches:
            return matches[0]
        return None

    def _extract_climate(self, ws_winter: Any, ws_monatswerte: Any) -> ClimateData:
        stations = []
        monthly_blocks: dict[str, dict[str, MonthlyProfile]] = {}
        for row_index, row in enumerate(
            ws_monatswerte.iter_rows(min_row=1, max_row=450, min_col=1, max_col=23), start=1
        ):
            if row_index % 11 != 1:
                continue
            name = str(row[0].value or "").strip()
            if not name:
                continue
            monthly = monthly_blocks.setdefault(name, {})
            values = [_month_value(row[offset].value) for offset in range(11, 23)]
            if all(value is None for value in values):
                continue  # header-only block
            monthly["t_aussen"] = MonthlyProfile(
                id="t_aussen",
                values=tuple(value if value is not None else 0.0 for value in values),
                unit="°C",
            )
            for key, row_offset in (
                ("radiation_horizontal", 2),
                ("radiation_east", 3),
                ("radiation_south", 4),
                ("radiation_west", 5),
                ("radiation_north", 6),
                ("precipitation", 7),
                ("mixing_ratio", 8),
                ("absolute_humidity", 9),
            ):
                values_row = next(
                    ws_monatswerte.iter_rows(
                        min_row=row_index + row_offset,
                        max_row=row_index + row_offset,
                        min_col=12,
                        max_col=23,
                    ),
                    (),
                )
                values = [_month_value(cell.value) for cell in values_row]
                if any(value is not None for value in values):
                    monthly[key] = MonthlyProfile(
                        id=key,
                        values=tuple(value if value is not None else 0.0 for value in values),
                        unit=_MONTHLY_BLOCK_UNITS[key],
                    )

        for index, row in enumerate(
            ws_winter.iter_rows(min_row=5, max_row=44, min_col=1, max_col=15), start=5
        ):
            name = str(row[0].value or "").strip()
            if not name:
                continue
            station_id = index - 4
            winter_design: dict[str, Quantity] = {}
            for key, column, unit in (
                ("t_a", 7, "°C"),  # H column: design temperature
                ("t_heating", 5, "°C"),  # F column: Heizung
                ("t_ventilation", 6, "°C"),  # G column: Lüftung
                ("radiation", 9, "W/m2"),  # J column: horizontal
            ):
                value = row[column].value
                if isinstance(value, (int, float)):
                    winter_design[key] = Quantity(float(value), unit)
            hdd_value = row[4].value  # E column: Heizgradtage
            hdd = Quantity(float(hdd_value), "K·d") if isinstance(hdd_value, (int, float)) else None
            stations.append(
                ClimateStation(
                    id=station_id,
                    name=TrilingualText(de=name),
                    winter_design=winter_design,
                    summer_design={},
                    monthly=monthly_blocks.get(name, {}),
                    hdd=hdd,
                    provenance=Provenance(
                        sources=(
                            SourceRef(
                                workbook=os.path.basename(self.workbook_path),
                                sheet="Winter_Auslegung",
                                range=f"A{index}:O{index}",
                            ),
                        )
                    ),
                )
            )
        return ClimateData(
            version="meteoschweiz-2024", stations=tuple(stations), source="MeteoSchweiz"
        )

    def _extract_full_load_hours(self, ws: Any, by_code: dict[str, RoomUse]) -> FullLoadHoursTable:
        rows: dict[tuple[int, str, str], float] = {}
        regulations = ("1-stufig", "2-stufig", "stufenlos")
        for row in ws.iter_rows(min_row=7, max_row=51, min_col=1, max_col=10):
            code = str(row[0].value or "").strip()
            room_use = by_code.get(normalize_room_use_code(code))
            if room_use is None:
                continue
            for regulation, column_index in zip(regulations, (3, 5, 9)):
                value = row[column_index].value
                if value is not None and isinstance(value, (int, float)):
                    rows[(room_use.nutzid, regulation, self.standard_version)] = float(value)
        return FullLoadHoursTable(
            rows=rows,
            standard_versions=frozenset({self.standard_version}),
            regulations=frozenset(regulations),
            provenance=Provenance(
                sources=(
                    SourceRef(
                        workbook=os.path.basename(self.workbook_path),
                        sheet="Volll_Lüft",
                        range="A7:J51",
                    ),
                ),
                note=f"Volllaststunden Volumenstrom; standard version {self.standard_version}",
            ),
        )

    def _extract_qhc(self, ws: Any, by_code: dict[str, RoomUse]) -> QhcTable:
        """``Qhc_Klimastat``: 12 columns per station block, E/I/M = annual cooling per kind."""
        rows: dict[tuple[int, int, ValueKind], float] = {}
        station_start = 4  # column D
        station_id = 1
        while station_start <= (ws.max_column or 1):
            station_name_cell = _cell(ws, 3, station_start)
            if station_name_cell is None:
                break
            for kind, offset in (
                (ValueKind.STANDARD, 0),
                (ValueKind.ZIELWERT, 4),
                (ValueKind.BESTAND, 8),
            ):
                value_column = station_start + offset + 1  # E/I/M: annual cooling kWh/m2
                for row_index, row in enumerate(
                    ws.iter_rows(min_row=7, max_row=51, min_col=1, max_col=1), start=7
                ):
                    code = str(row[0].value or "").strip()
                    room_use = by_code.get(normalize_room_use_code(code))
                    if room_use is None:
                        continue
                    value_cell = _cell(ws, row_index, value_column)
                    if isinstance(value_cell, (int, float)):
                        rows[(room_use.nutzid, station_id, kind)] = float(value_cell)
            station_start += 12
            station_id += 1
        return QhcTable(
            rows={key: Quantity(value, "kWh/m2") for key, value in rows.items()},
            provenance=Provenance(
                sources=(
                    SourceRef(
                        workbook=os.path.basename(self.workbook_path),
                        sheet="Qhc_Klimastat",
                        range="A7:M51",
                    ),
                ),
                note="Jährlicher Klimakältebedarf (kWh/m2), E/I/M columns per station block",
            ),
        )

    def _extract_hourly_profiles(self, ws: Any) -> list[HourlyProfile]:
        """``Profile`` rows 63-86: person / device / ventilation hour fractions."""
        columns = (
            ("personen_werktag", "person", 1),
            ("geraete_werktag", "device", 3),
            ("geraete_freier_tag", "device", 4),
            ("lueftung_einstufig", "ventilation", 5),
            ("lueftung_zweistufig", "ventilation", 6),
            ("lueftung_stufenlos", "ventilation", 8),
        )
        profiles = []
        for profile_id, profile_type, column_index in columns:
            values = []
            for row in ws.iter_rows(
                min_row=63, max_row=86, min_col=column_index + 1, max_col=column_index + 1
            ):
                value = row[0].value
                values.append(float(value) if isinstance(value, (int, float)) else 0.0)
            profiles.append(
                HourlyProfile(
                    id=profile_id,
                    profile_type=profile_type,
                    values=tuple(values),
                    unit="%",
                    provenance=Provenance(
                        sources=(
                            SourceRef(
                                workbook=os.path.basename(self.workbook_path),
                                sheet="Profile",
                                range="A63:J86",
                            ),
                        )
                    ),
                )
            )
        return profiles

    def _extract_mappings_and_areas(
        self, ws_flaeche: Any, ws_gepamod: Any, by_code: dict[str, RoomUse]
    ) -> tuple[list[BuildingCategoryMapping], list[AreaTable]]:
        """``Fläche-E`` rows 3-49: category columns (row 1) x room-use codes (column A)."""
        category_names: dict[str, str] = {}
        for row in ws_gepamod.iter_rows(min_row=1, max_row=2, min_col=1, max_col=41):
            for cell in row:
                if cell.value is not None:
                    category_names.setdefault(str(cell.value).strip(), "")

        categories: list[str] = []
        for cell in next(
            ws_flaeche.iter_rows(
                min_row=1, max_row=1, min_col=4, max_col=ws_flaeche.max_column or 4
            ),
            (),
        ):
            if cell.value is not None:
                categories.append(str(cell.value).strip())

        rows: dict[str, dict[str, float]] = {category: {} for category in categories}
        for row_index, row in enumerate(
            ws_flaeche.iter_rows(min_row=3, max_row=49, min_col=1, max_col=1), start=3
        ):
            code_raw = row[0].value
            if code_raw is None:
                continue
            code = normalize_room_use_code(str(code_raw).strip())
            if code not in by_code:
                continue
            for column_index, category in enumerate(categories, start=4):
                value_cell = _cell(ws_flaeche, row_index, column_index)
                if isinstance(value_cell, (int, float)):
                    rows[category][code] = float(value_cell)

        mappings = [
            BuildingCategoryMapping(
                sia3801_category=category,
                room_use_codes=frozenset(codes),
                name=TrilingualText(de=category_names.get(category, ""))
                if category_names.get(category)
                else None,
                provenance=Provenance(
                    sources=(
                        SourceRef(
                            workbook=os.path.basename(self.workbook_path),
                            sheet="GEPAMOD",
                            range="A1:L2",
                        ),
                    )
                ),
            )
            for category, codes in rows.items()
            if codes
        ]
        area_table = AreaTable(
            kind=ValueKind.STANDARD,
            rows={
                category: {code: Quantity(value, "%") for code, value in codes.items()}
                for category, codes in rows.items()
                if codes
            },
            provenance=Provenance(
                sources=(
                    SourceRef(
                        workbook=os.path.basename(self.workbook_path),
                        sheet="Fläche-E",
                        range="A3:C49",
                    ),
                ),
                note="Anteil der Raumfläche an der Gebäudekategorie (%)",
            ),
        )
        return mappings, [area_table]

    def _extract_sia3801(
        self, wb: Any, by_nutzid: dict[int, RoomUse], selected_nutzid: int, climate: ClimateData
    ) -> list[Sia3801Result]:
        """``SIA 380-1`` + ``_Qc`` / ``_EN`` / ``_Qc_EN``: Qh per value kind (P134/P166/P196)."""
        variants = {
            "SIA 380-1": "de",
            "SIA 380-1_EN": "en",
            "SIA 380-1_Qc": "de+qc",
            "SIA 380-1_Qc_EN": "en+qc",
        }
        station_name_cell = _cell(wb["SIA 380-1"], 68, 2)
        station_name = str(station_name_cell or "").strip()
        station_id = next(
            (station.id for station in climate.stations if station.name.de == station_name),
            climate.stations[0].id,
        )
        results = []
        for sheet_name, variant in variants.items():
            if sheet_name not in wb.sheetnames:
                continue
            ws = wb[sheet_name]
            for kind, row_number in (
                (ValueKind.STANDARD, 134),
                (ValueKind.ZIELWERT, 166),
                (ValueKind.BESTAND, 196),
            ):
                value_cell = _cell(ws, row_number, 16)
                if not isinstance(value_cell, (int, float)):
                    continue
                results.append(
                    Sia3801Result(
                        room_use_id=selected_nutzid,
                        station_id=station_id,
                        kind=kind,
                        variant=variant,
                        values={"Qh": Quantity(value_cell, "kWh/m2a")},
                        provenance=Provenance(
                            sources=(
                                SourceRef(
                                    workbook=os.path.basename(self.workbook_path),
                                    sheet=sheet_name,
                                    range=f"P{row_number}",
                                ),
                            ),
                            note="Heizwärmebedarf Qh, eff (kWh/m2a), "
                            "Energiebilanz mit mechanischer Lüftung",
                        ),
                    )
                )
        return results


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip().lower()


def _cell(ws: Any, row: int, column: int) -> Any:
    """Read one cell from a (possibly read-only) worksheet, without cell indexing."""
    for row_values in ws.iter_rows(min_row=row, max_row=row, min_col=column, max_col=column):
        for cell in row_values:
            return cell.value
    return None


def _safe_unit(raw: str) -> str:
    """Normalize a workbook unit cell; typographic dashes / unknown symbols -> ``"-"``."""
    unit = raw.strip()
    if unit in ("-", "–", "—", "−"):
        return "-"
    try:
        Unit(unit)
        return unit
    except UnitError:
        return "-"


def _slugify(label: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower()
    return slug or "parameter"


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip() in ("1", "ja", "true", "TRUE", "wahr")
    return False


def _infer_data_type(values_raw: tuple[Any, Any, Any]) -> str:
    numeric = True
    enum_like = True
    for raw in values_raw:
        value = _clean_cell_value(raw)
        if value is None:
            continue
        if not isinstance(value, (int, float)):
            numeric = False
        if isinstance(value, str) and value.lower() not in ("ja", "nein"):
            enum_like = False
    if numeric:
        return "number"
    if enum_like:
        return "enum"
    return "text"


def _clean_cell_value(value: Any) -> float | int | str | bool | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in _ERROR_VALUE_STRINGS or stripped == "":
            return None
        return stripped
    return value


def _month_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None
