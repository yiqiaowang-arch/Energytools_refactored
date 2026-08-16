"""Building aggregation and ``Resultate`` summary — pure-Python port.

This module is the last link of the computation chain: it turns the room
KPIs (``Gebäude!F12:W32``), the ventilation systems (``Lüftung!A7:Z22``) and
the generator inputs (``Erzeugung!A7:Q28``) into the building totals
(``Gebäude!D33:W39``), the final-energy matrix by Energieträger
(``Resultate!D7:U15``) and the weighted indicators (``Resultate!D21:U25``).

Authoritative documentation: ``docs/textbook/ch02-room-kpi-derivation.md``
(room KPI derivation, the ``Res`` matrix ``KZ_Raum_2024!B7:AV51`` and the
``Std`` table) and ``docs/textbook/ch05-heat-generation-resultate.md``
(generation allocation ``Erzeugung!L7:Q27`` and the ``Resultate`` summary).
The AHU air-treatment energies come from
:mod:`energytools.engine.native.ahu` (:class:`AhuAnnualResult`) — this module
only aggregates the per-system annual results.

Workbook conventions reproduced faithfully (deviations documented):

- **Res column selectors** (``Gebäude!F9:W9``, ch02 §2.3): power columns use
  offsets +7/+14 (Standard→Zielwert→Bestand), energy columns +8/+16 — with
  the workbook's **Lüftung deviation** kept verbatim: ``N9`` uses +6/+12 and
  ``O9`` uses +7/+14, so under Zielwert/Bestand the Lüftung power/energy
  lookups hit the *Beleuchtung*/*Prozessanlagen* columns of the matrix
  (ch02 §2.3 "Known deviation").  The golden caches follow the workbook, so
  the port reproduces the deviation instead of "fixing" it.
- **Gating** (ch02 §2.4): ``IF(flag=FALSE,0,…)`` for Lüftung (system
  selected), Raumkühlung (``P`` = gekühlt) and Raumheizung (``S`` = beheizt).
  The gated lookup is short-circuited: a gated-off room never queries the KPI
  matrix.
- **Erzeugung** (ch05 §5.4/§5.5/§5.6): demand × Deckungsgrad × (1 + losses),
  ``eta = IF(E≠"", E, D)`` (project value overrides the catalogue), the
  ``IF(D=0,0,…)`` guards, the WW power conversion
  ``V35·4.186/3.6·50/t_Aufh/1000`` and the unprotected Total-row
  Volllaststunden ``M·1000/L`` (guarded here, ch05 §5.12-5).
- **Resultate** (ch05 §5.8/§5.9/§5.10): the Kühlung power column ``N7`` is
  the group total ``Erzeugung!P10`` (not split by carrier), the energy column
  ``O`` is the SUMIF by carrier; the weighted NEGF row reproduces the
  workbook's **copy-paste error** ``I21`` (uses the THGE weight column Y —
  ch05 §5.10) so the golden caches match, while the PEne row fixes the
  ``G22/F22`` error (ch05 §5.12-6) since the golden JSON does not cache that
  row.

The input model (:class:`AggregationInput`) deliberately takes the KPI
values through a :class:`KpiLookup` interface (the ``Res`` matrix is partly
climate-dependent — the Klimakälte/Heizwärme columns reference
``Qhc_Klimastat`` — so the matrix is not a static dataset table; the
dataset-backed :class:`DatasetResLookup` maps the Res columns to the V221
parameter ids established in ch02 and reads the backfilled profile values,
which carry the Zürich default of the station-dependent columns).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from energytools.engine.model import BuildingInput, RoomRow, ValueKind
from energytools.engine.native.ahu import (
    AhuAnnualResult,
    AhuInput,
    _round_excel,
    compute_fan_model,
)

__all__ = [
    "CARRIER_LABEL_TO_ROW",
    "DEFAULT_WEIGHTS",
    "NUTZUNGSGRAD_CATALOG",
    "RESULTATE_CARRIERS",
    "RESULTATE_USES",
    "RES_SELECTORS",
    "AggregationInput",
    "AggregationResult",
    "DatasetResLookup",
    "GenerationCatalog",
    "GenerationGroupInput",
    "GenerationGroupResult",
    "GenerationInput",
    "GeneratorResult",
    "GeneratorSpec",
    "KpiLookup",
    "KpiLookupError",
    "NutzungsgradCatalog",
    "ResMatrixKpiProvider",
    "RoomResult",
    "RoomTotals",
    "VentilationSystemResult",
    "VentilationTotals",
    "WeightTable",
    "aggregate",
    "compute_room_row",
    "res_column",
]

# ---------------------------------------------------------------------------
# Constants (workbook conventions)
# ---------------------------------------------------------------------------

#: The 8 Energieträger rows of the Resultate matrix (``Resultate!B7:B14``).
RESULTATE_CARRIERS: tuple[str, ...] = ("El", "HEL", "Gas", "Pell", "HSch", "StH", "Bio", "FW")

#: German catalogue labels (``Nutzungsgrad!F``) → Resultate row code.
CARRIER_LABEL_TO_ROW: dict[str, str] = {
    "Elektrizität": "El",
    "Heizöl EL": "HEL",
    "Erdgas": "Gas",
    "Pellets": "Pell",
    "Holzschnitzel": "HSch",
    "Stückholz": "StH",
    "Biogas": "Bio",
    "Fernwärme": "FW",
}

#: The 9 use columns of the Resultate matrix (D…U, power/energy pairs).
RESULTATE_USES: tuple[str, ...] = (
    "allg_gebaeudetechnik",
    "geraete",
    "prozessanlagen",
    "beleuchtung",
    "lueftung",
    "kuehlung",
    "heizung",
    "warmwasser",
    "total",
)

#: Res matrix column selectors (``Gebäude!F8:W8`` base + ch02 §2.3 offsets):
#: target column → (Standard, Zielwert, Bestand) Res column number.  The
#: Lüftung rows (N/O) reproduce the workbook's inconsistent offsets
#: (+6/+12 and +7/+14) verbatim — see the module docstring.
RES_SELECTORS: dict[str, tuple[int, int, int]] = {
    "F": (28, 35, 42),  # Geräte power      (AC/AJ/AQ)
    "G": (2, 10, 18),   # Geräte energy     (C/K/S)
    "H": (29, 36, 43),  # Prozessanlagen power (AD/AK/AR)
    "I": (3, 11, 19),   # Prozessanlagen energy (D/L/T)
    "J": (30, 37, 44),  # Beleuchtung power (AE/AL/AS)
    "K": (4, 12, 20),   # Beleuchtung energy (E/M/U)
    "N": (31, 37, 43),  # Lüftung power (AF/AL/AR — deviation, hits Beleuchtung/Prozess)
    "O": (5, 12, 19),   # Lüftung energy (F/M/T — deviation, hits Beleuchtung/Prozess)
    "Q": (32, 39, 46),  # Raumkühlung power (AG/AN/AU)
    "R": (6, 14, 22),   # Raumkühlung energy (G/O/W)
    "T": (33, 40, 47),  # Raumheizung power (AH/AO/AV)
    "U": (7, 15, 23),   # Raumheizung energy (H/P/X)
    "W": (8, 16, 24),   # Warmwasser energy (I/Q/Y)
}

#: WW power conversion constants (ch05 §5.5, ``Erzeugung!L25``).
WW_TEMP_RISE_K = 50.0  #: ΔT cold→hot water [K]
WW_SPECIFIC_HEAT = 4.186  #: c_w [kJ/(kg·K)]
KJ_PER_WH = 3.6  #: kJ → Wh


@dataclass(frozen=True)
class WeightTable:
    """The NEGF / PEne / THGE weight factors per Resultate carrier row."""

    negf: Mapping[str, float]
    pene: Mapping[str, float]
    thge: Mapping[str, float]


def _weight_table() -> WeightTable:
    negf = {"El": 2.0, "HEL": 1.0, "Gas": 1.0, "Pell": 0.7, "HSch": 0.7, "StH": 0.7, "Bio": 1.0, "FW": 0.6}
    pene = {"El": 2.69, "HEL": 1.22, "Gas": 1.06, "Pell": 0.2, "HSch": 0.06, "StH": 0.05, "Bio": 0.31, "FW": 0.55}
    thge = {"El": 0.139, "HEL": 0.298, "Gas": 0.228, "Pell": 0.034, "HSch": 0.022, "StH": 0.022, "Bio": 0.132, "FW": 0.1}
    return WeightTable(negf=negf, pene=pene, thge=thge)


#: Default weight factors (ch05 §5.8, ``Resultate!W7:Y17``): the current Swiss
#: NEGF / PEne / THGE values, keyed by the Resultate carrier codes.
DEFAULT_WEIGHTS = _weight_table()


# ---------------------------------------------------------------------------
# KPI lookup interface
# ---------------------------------------------------------------------------


class KpiLookupError(KeyError):
    """The KPI lookup cannot provide a requested room-use value."""


class KpiLookup:
    """The room-KPI interface (the ``Res`` matrix + the ``Std`` table).

    The workbook looks the per-use intensities up in the named range ``Res``
    (``KZ_Raum_2024!B7:AV51``) by the room-use *name*, and the ventilation /
    hot-water intensities in ``Std!B6:I50``.  The Klimakälte/Heizwärme
    columns of ``Res`` are climate-station-dependent formulas
    (``Qhc_Klimastat``), which is why the values are provided through an
    interface instead of being hard-coded.

    Implementations must raise :class:`KpiLookupError` for a use/column they
    cannot provide.
    """

    def res_value(self, room_use: str, res_col: int) -> float:
        """The ``Res`` matrix cell (use, column): W/m² or kWh/m² intensity."""
        raise NotImplementedError

    def hygienic_fresh_air(self, room_use: str) -> float:
        """``Std!D`` hygienic fresh-air rate [m³/(h·m²)]."""
        raise NotImplementedError

    def process_fresh_air(self, room_use: str) -> float:
        """``Std!E`` process fresh-air rate [m³/(h·m²)]."""
        raise NotImplementedError

    def ww_demand(self, room_use: str) -> float:
        """``Std!I`` hot-water demand [l/(d·m²)] (= Std!H / Std!C)."""
        raise NotImplementedError


@dataclass(frozen=True)
class ResMatrixKpiProvider(KpiLookup):
    """In-memory dict-backed implementation of :class:`KpiLookup`.

    ``values`` maps room-use name → Res column → intensity; the fresh-air and
    hot-water tables map room-use name → intensity.  A missing Res value
    raises :class:`KpiLookupError` (the matrix has no empty KPI cells), while
    a missing ``Std`` intensity is ``0.0`` — the workbook's ``VLOOKUP`` over
    an empty ``Std`` cell returns 0 (e.g. Parkhaus has no hygienic fresh air).
    """

    values: Mapping[str, Mapping[int, float]] = field(default_factory=dict)
    hygienic: Mapping[str, float] = field(default_factory=dict)
    process: Mapping[str, float] = field(default_factory=dict)
    ww: Mapping[str, float] = field(default_factory=dict)

    def res_value(self, room_use: str, res_col: int) -> float:
        try:
            return self.values[room_use][res_col]
        except KeyError:
            raise KpiLookupError(
                f"no Res value for room use {room_use!r}, column {res_col}"
            ) from None

    def hygienic_fresh_air(self, room_use: str) -> float:
        return self.hygienic.get(room_use, 0.0)

    def process_fresh_air(self, room_use: str) -> float:
        return self.process.get(room_use, 0.0)

    def ww_demand(self, room_use: str) -> float:
        return self.ww.get(room_use, 0.0)


#: Res column → V221 parameter id for the *energy* categories (ch02 §2.2/§2.4
#: correspondence with the Raumdatenblätter parameter catalogue).
_RES_COL_ENERGY_PARAM: dict[int, str] = {
    2: "1.1.3.8",  # Geräte
    3: "1.1.3.9",  # Prozessanlagen
    4: "1.1.4.13",  # Beleuchtung
    5: "EV",  # Lüftung
    6: "1.1.6.7",  # Klimakälte
    7: "1.1.7.9",  # Heizwärme
    8: "1.1.8.7",  # Warmwasser
}
#: Res column → V221 parameter id for the *power* categories (6 categories,
#: Warmwasser has no power column in the matrix).
_RES_COL_POWER_PARAM: dict[int, str] = {
    28: "1.1.3.3",  # Geräte
    29: "1.1.3.4",  # Prozessanlagen
    30: "1.1.4.10",  # Beleuchtung
    31: "pV",  # Lüftung
    32: "1.1.6.5",  # Klimakälte
    33: "FV,i",  # Heizwärme
}


def _energy_block_kind(res_col: int) -> tuple[str, int]:
    """Value kind + in-block offset of an energy column."""
    if 2 <= res_col <= 8:
        return "standard", res_col
    if 10 <= res_col <= 16:
        return "zielwert", res_col - 8
    return "bestand", res_col - 16


def _power_block_kind(res_col: int) -> tuple[str, int]:
    """Value kind + in-block offset of a power column."""
    if 28 <= res_col <= 33:
        return "standard", res_col
    if 35 <= res_col <= 40:
        return "zielwert", res_col - 7
    return "bestand", res_col - 14


class DatasetResLookup(KpiLookup):
    """Dataset-backed :class:`KpiLookup` over a V221 ``package.json``.

    The dataset structure (``room_uses[]``, ``profiles[]`` with
    ``nutzid → values[param_id][value_kind]``, ``parameters[]``) stores the
    room intensities under the Raumdaten parameter ids; the correspondence to
    the ``Res`` matrix columns is established in ch02 §2.2/§2.4 and encoded in
    :data:`_RES_COL_ENERGY_PARAM` / :data:`_RES_COL_POWER_PARAM` (the matrix
    blocks repeat the same parameters across the three value kinds).

    The V221 package carries the full KPI matrix (backfilled from the
    ``KZ_Raum_2024`` workbook matrix) and the ``Std`` intensities: the
    hygienic fresh air ``1.1.5.2`` and the process fresh air ``1.1.5.3`` read
    the Standard profile values, and the hot-water demand is derived as
    ``1.1.8.4 / 1.1.2.9`` (``Std!I = Std!H / Std!C``).  Room uses resolve by
    dataset name, SIA code or nutzid string.
    """

    def __init__(self, package: Mapping) -> None:
        room_uses = {u["nutzid"]: u["name"]["de"] for u in package["room_uses"]}
        self._name_by_nutzid = room_uses
        self._nutzid_by_name = {name: n for n, name in room_uses.items()}
        self._nutzid_by_code = {u["code"]: u["nutzid"] for u in package["room_uses"]}
        self._nutzid_by_str = {str(n): n for n in room_uses}
        self._profiles: dict[int, Mapping] = {
            p["nutzid"]: p["values"] for p in package["profiles"]
        }
        self._params: dict[str, Mapping] = {p["id"]: p for p in package["parameters"]}

    def _resolve_nutzid(self, room_use: str | int) -> int:
        """Room use → nutzid: dataset name, SIA code, or nutzid string."""
        if isinstance(room_use, int):
            return room_use
        key = str(room_use).strip()
        if key in self._nutzid_by_name:
            return self._nutzid_by_name[key]
        if key in self._nutzid_by_code:
            return self._nutzid_by_code[key]
        if key in self._nutzid_by_str:
            return self._nutzid_by_str[key]
        raise KpiLookupError(f"room use {room_use!r} not in dataset")

    def _param_id(self, res_col: int) -> str:
        if res_col in _RES_COL_ENERGY_PARAM:
            return _RES_COL_ENERGY_PARAM[res_col]
        if res_col in _RES_COL_POWER_PARAM:
            return _RES_COL_POWER_PARAM[res_col]
        raise KpiLookupError(f"Res column {res_col} has no dataset parameter mapping")

    def _profile_value(self, room_use: str, param_id: str, value_kind: str) -> float:
        nutzid = self._resolve_nutzid(room_use)
        values = self._profiles.get(nutzid, {})
        entry = values.get(param_id)
        if entry is None or value_kind not in entry:
            raise KpiLookupError(
                f"room use {room_use!r}: parameter {param_id!r} "
                f"has no {value_kind} value in the dataset"
            )
        return float(entry[value_kind]["value"])

    def res_value(self, room_use: str, res_col: int) -> float:
        # The matrix blocks repeat the same parameter ids; the value kind is
        # derived from the block the column belongs to.
        if 2 <= res_col <= 8 or 10 <= res_col <= 16 or 18 <= res_col <= 24:
            value_kind, offset = _energy_block_kind(res_col)
            param = _RES_COL_ENERGY_PARAM[offset]
        elif 28 <= res_col <= 33 or 35 <= res_col <= 40 or 42 <= res_col <= 47:
            value_kind, offset = _power_block_kind(res_col)
            param = _RES_COL_POWER_PARAM[offset]
        else:
            raise KpiLookupError(f"Res column {res_col} is not a KPI data column")
        return self._profile_value(room_use, param, value_kind)

    def hygienic_fresh_air(self, room_use: str) -> float:
        # A use without a hygienic fresh-air value (garage/parking, storage,
        # traffic areas) has no mechanical fresh-air demand — 0, not an error.
        nutzid = self._resolve_nutzid(room_use)
        entry = self._profiles.get(nutzid, {}).get("1.1.5.2", {}).get("standard")
        return float(entry["value"]) if entry else 0.0

    def process_fresh_air(self, room_use: str) -> float:
        nutzid = self._resolve_nutzid(room_use)
        entry = self._profiles.get(nutzid, {}).get("1.1.5.3", {}).get("standard")
        return float(entry["value"]) if entry else 0.0

    def ww_demand(self, room_use: str) -> float:
        # Std!I = Std!H / Std!C (l/(d·P) ÷ m²/P).  The dataset carries the WW
        # demand per person (1.1.8.4 = Std!H) and the Personenfläche
        # (1.1.2.9 = Std!C); a use without either has no hot-water demand
        # (the workbook's VLOOKUP over an empty Std cell returns 0).
        nutzid = self._resolve_nutzid(room_use)
        values = self._profiles.get(nutzid, {})
        ww_per_person = values.get("1.1.8.4", {}).get("standard")
        persons_area = values.get("1.1.2.9", {}).get("standard")
        if ww_per_person is None or persons_area is None or float(persons_area["value"]) == 0.0:
            return 0.0
        return float(ww_per_person["value"]) / float(persons_area["value"])


# ---------------------------------------------------------------------------
# Generation catalogue
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeneratorSpec:
    """One catalogue entry of ``Nutzungsgrad`` (name → code/η/carrier)."""

    name: str
    code: str
    eta_standard: float  #: Nutzungsgrad!E (COP for chillers/heat pumps)
    energy_carrier: str  #: Nutzungsgrad!F German label ("Elektrizität", …)


class GenerationCatalog:
    """The ``Nutzungsgrad`` catalogue lookup (by group and generator name).

    The workbook has three catalogue blocks (``Nutzungsgrad!C3:G8`` Kälte,
    ``C11:G27`` Wärme, ``C29:G42`` Warmwasser) — the same generator name can
    appear in several blocks with different efficiencies (e.g.
    "Pelletfeuerung " in both the Wärme and WW blocks), so the lookup is
    keyed by group kind *and* name.
    """

    def lookup(self, kind: str, name: str) -> GeneratorSpec:
        """Return the catalogue entry for a generator name in a group.

        Raises:
            KeyError: for unknown group/name combinations.
        """
        raise NotImplementedError


#: The ``Nutzungsgrad`` catalogue (``Nutzungsgrad!C3:G8`` / ``C11:G27`` /
#: ``C29:G42`` of the Gebaeude-Tool) — generator names (with the workbook's
#: trailing spaces verbatim), catalogue codes, standard Nutzungsgrad/COP
#: (``E``; an empty cell reads 0 — e.g. Solarenergie has no Nutzungsgrad) and
#: the Energieträger label (``F``).  Extracted from
#: ``.analysis/dumps/gebaeude/sheet_15_Nutzungsgrad.tsv``; the helper-energy
#: share (``G``, Hilfsenergie %) is not part of the aggregation port.
NUTZUNGSGRAD_CATALOG: dict[str, tuple[tuple[str, str, float, str], ...]] = {
    "cooling": (
        ("KE01", "Kompaktkältemaschine 7°C", 3.0, "Elektrizität"),
        ("KE02", "Kompaktkältemaschine 14°C", 4.0, "Elektrizität"),
        ("KE03", "Kältemaschine 7°C", 4.0, "Elektrizität"),
        ("KE04", "Kältemaschine 14°C", 7.5, "Elektrizität"),
        ("KE05", "Direktkühlung Erdreich", 15.0, "Elektrizität"),
        ("KE06", "Direktkühlung Grundwasser", 15.0, "Elektrizität"),
    ),
    "heating": (
        ("WE01", "Ölfeuerung kondensierend ", 0.8, "Heizöl EL"),
        ("WE02", "Gasfeuerung kondensierend ", 0.8, "Erdgas"),
        ("WE03", "Stückholzfeuerung", 0.6, "Holz"),
        ("WE04", "Hackschnitzelfeuerung ", 0.7, "Holzschnitzel"),
        ("WE05", "Pelletfeuerung ", 0.7, "Pellets"),
        ("WE06", "Fernwärme (CH-Durchschnitt) ", 0.98, "Fernwärme"),
        ("WE07", "Elektrospeicher-Zentralheizung ", 0.93, "Elektrizität"),
        ("WE08", "Elektro direkt ", 1.0, "Elektrizität"),
        ("WE09", "WKK, thermischer Nutzungsgrad ", 0.5, "Erdgas"),
        ("WE10", "Solarenergie thermisch", 0.0, "Sonne"),
        ("WE11", "Wärmepumpe Aussenluft 35°C", 3.0, "Elektrizität"),
        ("WE12", "Wärmepumpe Aussenluft 50°C", 2.2, "Elektrizität"),
        ("WE13", "Wärmepumpe Erdsonden 35°C", 4.3, "Elektrizität"),
        ("WE14", "Wärmepumpe Erdsonden 50°C", 3.1, "Elektrizität"),
        ("WE15", "Wärmepumpe Grundwasser 35°C", 4.3, "Elektrizität"),
        ("WE16", "Wärmepumpe Grundwasser 50°C", 3.1, "Elektrizität"),
    ),
    "ww": (
        ("W01", "Ölfeuerung kondensierend ", 0.75, "Heizöl EL"),
        ("W02", "Gasfeuerung kondensierend ", 0.75, "Erdgas"),
        ("W03", "Stückholzfeuerung", 0.55, "Holz"),
        ("W04", "Hackschnitzelfeuerung ", 0.6, "Holzschnitzel"),
        ("W05", "Pelletfeuerung ", 0.65, "Pellets"),
        ("W06", "Fernwärme (CH-Durchschnitt) ", 1.0, "Fernwärme"),
        ("W07", "Elekro-Wassererwärmer ", 1.0, "Elektrizität"),
        ("W08", "Gas-Wassererwärmer ", 0.65, "Erdgas"),
        ("W09", "Solarenergie thermisch", 0.0, "Sonne"),
        ("W10", "WKK, thermischer Nutzungsgrad ", 0.5, "Erdgas"),
        ("W11", "Wärmepumpe Aussenluft", 2.2, "Elektrizität"),
        ("W12", "Wärmepumpe Erdsonden", 2.4, "Elektrizität"),
        ("W13", "Wärmepumpe Grundwasser", 1.9, "Elektrizität"),
    ),
}


class NutzungsgradCatalog(GenerationCatalog):
    """Dataset-independent :class:`GenerationCatalog` over
    :data:`NUTZUNGSGRAD_CATALOG`.

    The ``Nutzungsgrad`` table is a Gebaeude model constant (not Raumdaten
    data), so the catalogue is built in — the same constants the workbook's
    ``Erzeugung`` VLOOKUPs read from ``Nutzungsgrad!C3:G42``.  ``lookup``
    matches the exact workbook name first and falls back to the catalogue
    code, so callers may pass either (the ``Erzeugung`` sheet keys by name,
    the input model ``catalog_code`` by code).
    """

    def __init__(self) -> None:
        self._by_name: dict[tuple[str, str], GeneratorSpec] = {}
        self._by_code: dict[tuple[str, str], GeneratorSpec] = {}
        for kind, rows in NUTZUNGSGRAD_CATALOG.items():
            for code, name, eta, carrier in rows:
                spec = GeneratorSpec(name=name, code=code, eta_standard=eta, energy_carrier=carrier)
                self._by_name[(kind, name)] = spec
                self._by_code[(kind, code)] = spec

    def lookup(self, kind: str, name: str) -> GeneratorSpec:
        try:
            return self._by_name[(kind, name)]
        except KeyError:
            pass
        try:
            return self._by_code[(kind, name)]
        except KeyError:
            raise KeyError(
                f"unknown generator {name!r} in group {kind!r} "
                f"(Nutzungsgrad codes: {sorted(code for code, _ in self._by_code if code[0] == kind)})"
            ) from None


@dataclass(frozen=True)
class GenerationInput:
    """One generator row of ``Erzeugung`` (rows 7–9, 16–18, 25–27).

    Coverage (F/G), losses (H/J) and the project efficiency (E) are inputs;
    the standard efficiency and the Energieträger come from the catalogue.
    """

    name: str
    coverage_power_pct: float = 0.0  #: F — Deckungsgrad Leistung [%]
    coverage_energy_pct: float = 0.0  #: G — Deckungsgrad Energie [%]
    losses_standard_pct: float = 0.0  #: H — Speicher-/Verteilverluste [%]
    losses_project_pct: float | None = None  #: J — project override
    eta_project: float | None = None  #: E — project Nutzungsgrad override


@dataclass(frozen=True)
class GenerationGroupInput:
    """One generation group: 3 generator rows (Kälte/Wärme/Warmwasser)."""

    kind: str  #: "cooling" | "heating" | "ww"
    generators: tuple[GenerationInput, ...] = ()


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoomResult:
    """One room row of ``Gebäude!F12:W32`` (kW / MWh / m³/h / l/d).

    Field names keep the workbook's column semantics: ``geraete_kw`` (F),
    ``geraete_mwh`` (G), ``prozessanlagen_kw`` (H), ``prozessanlagen_mwh``
    (I), ``beleuchtung_kw`` (J), ``beleuchtung_mwh`` (K),
    ``lueftung_volume_flow_m3h`` (M), ``lueftung_kw`` (N),
    ``lueftung_mwh`` (O), ``kuehlung_kw`` (Q), ``kuehlung_mwh`` (R),
    ``heizung_kw`` (T), ``heizung_mwh`` (U), ``warmwasser_l_d`` (V),
    ``warmwasser_mwh`` (W).
    """

    name: str
    room_use: str
    row: int
    ebf: bool
    ngf_m2: float
    share: float  #: E — Anteil an der NGF total (D/D35)
    geraete_kw: float
    geraete_mwh: float
    prozessanlagen_kw: float
    prozessanlagen_mwh: float
    beleuchtung_kw: float
    beleuchtung_mwh: float
    lueftung_volume_flow_m3h: float
    lueftung_kw: float
    lueftung_mwh: float
    kuehlung_kw: float
    kuehlung_mwh: float
    heizung_kw: float
    heizung_mwh: float
    warmwasser_l_d: float
    warmwasser_mwh: float


@dataclass(frozen=True)
class RoomTotals:
    """Building totals ``Gebäude!D33:W39`` (Rechenwert row 35)."""

    ngf_m2: float  #: D35 (NGF total)
    ebf_m2: float  #: D39
    gf_m2: float  #: D38
    share_sum: float  #: E33
    geraete_kw: float
    geraete_mwh: float
    prozessanlagen_kw: float
    prozessanlagen_mwh: float
    beleuchtung_kw: float
    beleuchtung_mwh: float
    lueftung_volume_flow_m3h: float  #: M35
    lueftung_kw: float  #: N35
    lueftung_mwh: float  #: O35
    kuehlung_kw: float  #: Q35
    kuehlung_mwh: float  #: R35
    heizung_kw: float  #: T35
    heizung_mwh: float  #: U35
    warmwasser_l_d: float  #: V35
    warmwasser_mwh: float  #: W35


@dataclass(frozen=True)
class VentilationSystemResult:
    """One system row of ``Lüftung!A7:Z22`` (the aggregated subset)."""

    id: str
    room_use: str
    volume_flow_m3h: float  #: C (SUMIF of the room flows)
    process_flow_m3h: float  #: D
    effective_flow_m3h: float  #: F (= C unless a project override exists)
    fan_power_kw: float  #: H = F·SFP/1000
    fan_energy_mwh: float  #: I (from the AHU annual result)
    full_load_hours: float  #: K = ROUND(I·1000/H, -1)
    luftkuehlung_kw: float  #: Q
    luftkuehlung_mwh: float  #: R
    lufterwaermung_kw: float  #: S
    lufterwaermung_mwh: float  #: T


@dataclass(frozen=True)
class VentilationTotals:
    """``Lüftung!C23:Z23`` totals."""

    volume_flow_m3h: float  #: C23
    process_flow_m3h: float  #: D23
    fan_power_kw: float  #: H23
    fan_energy_mwh: float  #: I23
    luftkuehlung_kw: float  #: Q23
    luftkuehlung_mwh: float  #: R23
    lufterwaermung_kw: float  #: S23
    lufterwaermung_mwh: float  #: T23


@dataclass(frozen=True)
class GeneratorResult:
    """One generator row of ``Erzeugung`` (L…Q + the inputs F/G/H)."""

    code: str
    name: str
    energy_carrier: str  #: R
    eta_standard: float  #: D
    eta_effective: float  #: IF(E≠"", E, D)
    coverage_power_pct: float  #: F
    coverage_energy_pct: float  #: G
    losses_pct: float  #: IF(J≠"", J, H)
    demand_power_kw: float  #: L (incl. losses)
    demand_energy_mwh: float  #: M (incl. losses)
    full_load_hours: float  #: N
    end_power_kw: float  #: P (Endenergie)
    end_energy_mwh: float  #: Q (Endenergie)


@dataclass(frozen=True)
class GenerationGroupResult:
    """One generation group of ``Erzeugung`` incl. the Total row."""

    kind: str
    demand_power_kw: float  #: source demand (Gebäude + Lüftung)
    demand_energy_mwh: float
    total_demand_power_kw: float  #: L10
    total_demand_energy_mwh: float  #: M10
    total_full_load_hours: float  #: N10
    total_end_power_kw: float  #: P10
    total_end_energy_mwh: float  #: Q10
    coverage_power_pct: float  #: F10 (sum of F)
    coverage_energy_pct: float  #: G10 (sum of G)
    generators: tuple[GeneratorResult, ...]


@dataclass(frozen=True)
class ResultateMatrix:
    """The ``Resultate!D7:U15`` matrix (use × carrier → kW/MWh).

    ``power`` and ``energy`` are indexed by use (``RESULTATE_USES``) then by
    carrier code (``RESULTATE_CARRIERS``); the extra key ``"Total"`` holds
    the carrier-total row 15.
    """

    power: Mapping[str, Mapping[str, float]]
    energy: Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class ResultateWeighted:
    """The weighted indicator rows ``Resultate!D21:U25``.

    ``energy_mwh`` and ``per_area_kwh_m2`` are indexed by indicator
    (``"negf"`` / ``"pene"`` / ``"thge"``) then by use.
    """

    energy_mwh: Mapping[str, Mapping[str, float]]
    per_area_kwh_m2: Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class RoomGenerationResult:
    """One room-level generator's share: the room demand it covers and its
    final (end) energy after catalogue efficiency and losses.

    Room-level generators (e.g. a bathroom electric heater, a room air
    conditioner) take their share of the *room's* heating/cooling/ww demand
    before the building-level generation groups see it; the remaining demand
    flows into the building groups.  The workbook has no room-level
    Erzeugung — this is an engine extension (the catalogue and the losses
    semantics are identical to the building-level path).
    """

    room: str  #: room name
    kind: str  #: heating | cooling | ww
    code: str  #: catalogue code (KE../WE../WW..)
    carrier: str  #: Energieträger label of the catalogue entry
    eta: float  #: catalogue efficiency (COP for chillers/heat pumps)
    coverage: float  #: 0..1 share of the room demand
    covered_power_kw: float  #: demand share incl. storage/distribution losses
    covered_energy_mwh: float
    end_power_kw: float  #: final power after eta
    end_energy_mwh: float


@dataclass(frozen=True)
class AggregationResult:
    """The complete aggregation: rooms, ventilation, generation, Resultate."""

    rooms: tuple[RoomResult, ...]
    room_totals: RoomTotals
    ventilation: tuple[VentilationSystemResult, ...]
    ventilation_totals: VentilationTotals
    generation: tuple[GenerationGroupResult, ...]
    resultate: ResultateMatrix
    resultate_weighted: ResultateWeighted
    room_generation: tuple[RoomGenerationResult, ...] = ()

    def as_dict(self) -> dict:
        """JSON-ready representation (nested dicts, German field names)."""
        return {
            "rooms": [r.__dict__ for r in self.rooms],
            "room_totals": self.room_totals.__dict__,
            "ventilation": [r.__dict__ for r in self.ventilation],
            "ventilation_totals": self.ventilation_totals.__dict__,
            "generation": [g.__dict__ for g in self.generation],
            "room_generation": [g.__dict__ for g in self.room_generation],
            "resultate": {
                "power": {u: dict(c) for u, c in self.resultate.power.items()},
                "energy": {u: dict(c) for u, c in self.resultate.energy.items()},
            },
            "resultate_weighted": {
                "energy_mwh": {i: dict(u) for i, u in self.resultate_weighted.energy_mwh.items()},
                "per_area_kwh_m2": {
                    i: dict(u) for i, u in self.resultate_weighted.per_area_kwh_m2.items()
                },
            },
        }


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------


def _zero_ahu() -> AhuAnnualResult:
    fan = compute_fan_model(AhuInput(volume_flow=0.0, fan_power_total=0.0))
    return AhuAnnualResult(
        luftkuehlung_kwh=0.0,
        luftkuehlung_kw=0.0,
        lufterwaermung_kwh=0.0,
        lufterwaermung_kw=0.0,
        erwaermung_befeuchtung_kwh=0.0,
        erwaermung_befeuchtung_kw=0.0,
        entfeuchtung_kuehlung_kwh=0.0,
        entfeuchtung_kuehlung_kw=0.0,
        entfeuchtung_erwaermung_kwh=0.0,
        entfeuchtung_erwaermung_kw=0.0,
        ventilator_kwh=0.0,
        ventilator_kw=0.0,
        total_kwh=0.0,
        total_kw=0.0,
        befeuchtungswasser_l=0.0,
        kondensat_l=0.0,
        k70=0.0,
        m70=0.0,
        fan=fan,
    )


_ZERO_AHU = _zero_ahu()


@dataclass(frozen=True)
class AggregationInput:
    """Everything the aggregation needs beyond :class:`BuildingInput`.

    Args:
        building: rooms + ventilation systems (the room KPI intensities and
            the Std intensities come from ``kpi_lookup``, not from the room
            fields).
        kpi_lookup: the ``Res`` matrix + ``Std`` table lookup.
        ahu_results: per-system :class:`AhuAnnualResult` keyed by LA id
            (LA01…LA16).  A missing id is treated as a zero AHU.
        generation_groups: the three generator groups (Kälte/Wärme/Warmwasser).
        generation_catalog: the ``Nutzungsgrad`` catalogue lookup.
        ag_power_kw: ``Gebäude!L58`` — the Allg. Gebäudetechnik power total
            (AG01–AG10, ch02 §2.8) — passed through, since the AG input block
            is not part of this module's scope.
        ag_energy_mwh: ``Gebäude!I58`` — the Allg. Gebäudetechnik energy total
            (AG01–AG10, ch02 §2.8) — passed through, since the AG input block
            is not part of this module's scope.
        construction_factor_pct: ``Gebäude!D37`` (default 10 %).
        aufheizzeit_h: ``Erzeugung!L29`` (default 6 h/d).
        weights: the Resultate weight factors (defaults: ch05 §5.8).
    """

    building: BuildingInput
    kpi_lookup: KpiLookup
    ahu_results: Mapping[str, AhuAnnualResult] = field(default_factory=dict)
    generation_groups: tuple[GenerationGroupInput, ...] = ()
    generation_catalog: GenerationCatalog | None = None
    ag_power_kw: float = 0.0
    ag_energy_mwh: float = 0.0
    construction_factor_pct: float = 10.0
    aufheizzeit_h: float = 6.0
    weights: WeightTable = field(default_factory=_weight_table)

    def __post_init__(self) -> None:
        if self.construction_factor_pct < 0:
            raise ValueError("construction_factor_pct must be >= 0")
        if self.aufheizzeit_h <= 0:
            raise ValueError("aufheizzeit_h must be > 0")
        if self.ag_power_kw < 0 or self.ag_energy_mwh < 0:
            raise ValueError("AG power/energy must not be negative")


# ---------------------------------------------------------------------------
# Res column selector
# ---------------------------------------------------------------------------


def res_column(target: str, value_kind: ValueKind) -> int:
    """The ``Res`` matrix column for a target column and value kind.

    Reproduces ``Gebäude!F9:W9`` (ch02 §2.3), including the documented
    Lüftung deviation of ``N9`` (+6/+12) and ``O9`` (+7/+14) — see
    :data:`RES_SELECTORS`.

    Raises:
        KeyError: for unknown target columns.
    """
    standard, zielwert, bestand = RES_SELECTORS[target]
    if value_kind is ValueKind.STANDARD:
        return standard
    if value_kind is ValueKind.ZIELWERT:
        return zielwert
    return bestand


# ---------------------------------------------------------------------------
# Room aggregation (ch02 §2.3–§2.7)
# ---------------------------------------------------------------------------


def _room_flow(room: RoomRow, lookup: KpiLookup) -> tuple[float, float, float]:
    """(hygienic flow, process flow, total flow) of a room, ch02 §2.5."""
    hygienic = lookup.hygienic_fresh_air(str(room.room_use_id)) * room.ngf
    process = lookup.process_fresh_air(str(room.room_use_id)) * room.ngf
    return hygienic, process, hygienic + process


def compute_room_row(
    room: RoomRow,
    value_kind: ValueKind,
    lookup: KpiLookup,
    total_ngf: float,
    row_index: int,
) -> RoomResult:
    """One room row ``Gebäude!F12:W32`` from the KPI lookup.

    Implements ch02 Formula 2 (KPI × NGF / 1000) with the gating semantics of
    ``IF(flag=FALSE,0,…)``: Lüftung counts only when a system is selected,
    Raumkühlung only when ``gekuehlt``, Raumheizung only when ``beheizt``.
    The gated lookups are skipped entirely (a gated-off room never queries
    the KPI matrix).  ``M`` (flow) and ``V`` (WW demand) follow ch02 Formula
    3/4 from the ``Std`` intensities.

    Raises:
        KpiLookupError: when the lookup cannot provide a needed intensity.
    """
    use = str(room.room_use_id)
    scale = room.ngf / 1000.0

    if room.ngf == 0.0:
        # Zero-area room: every cell is 0 (KPI × 0).  Skip the lookups so a
        # room that contributes nothing never needs the KPI matrix.
        return RoomResult(
            name=room.name,
            room_use=use,
            row=row_index,
            ebf=room.ebf,
            ngf_m2=0.0,
            share=0.0,
            geraete_kw=0.0,
            geraete_mwh=0.0,
            prozessanlagen_kw=0.0,
            prozessanlagen_mwh=0.0,
            beleuchtung_kw=0.0,
            beleuchtung_mwh=0.0,
            lueftung_volume_flow_m3h=0.0,
            lueftung_kw=0.0,
            lueftung_mwh=0.0,
            kuehlung_kw=0.0,
            kuehlung_mwh=0.0,
            heizung_kw=0.0,
            heizung_mwh=0.0,
            warmwasser_l_d=0.0,
            warmwasser_mwh=0.0,
        )

    geraete_kw = lookup.res_value(use, res_column("F", value_kind)) * scale
    geraete_mwh = lookup.res_value(use, res_column("G", value_kind)) * scale
    prozessanlagen_kw = lookup.res_value(use, res_column("H", value_kind)) * scale
    prozessanlagen_mwh = lookup.res_value(use, res_column("I", value_kind)) * scale
    beleuchtung_kw = lookup.res_value(use, res_column("J", value_kind)) * scale
    beleuchtung_mwh = lookup.res_value(use, res_column("K", value_kind)) * scale

    _, _, flow = _room_flow(room, lookup)
    warmwasser_l_d = lookup.ww_demand(use) * room.ngf
    warmwasser_mwh = lookup.res_value(use, res_column("W", value_kind)) * scale

    if room.lueftung_system is not None:
        lueftung_kw = lookup.res_value(use, res_column("N", value_kind)) * scale
        lueftung_mwh = lookup.res_value(use, res_column("O", value_kind)) * scale
    else:
        lueftung_kw = 0.0
        lueftung_mwh = 0.0

    if room.gekuehlt:
        kuehlung_kw = lookup.res_value(use, res_column("Q", value_kind)) * scale
        kuehlung_mwh = lookup.res_value(use, res_column("R", value_kind)) * scale
    else:
        kuehlung_kw = 0.0
        kuehlung_mwh = 0.0

    if room.beheizt:
        heizung_kw = lookup.res_value(use, res_column("T", value_kind)) * scale
        heizung_mwh = lookup.res_value(use, res_column("U", value_kind)) * scale
    else:
        heizung_kw = 0.0
        heizung_mwh = 0.0

    share = room.ngf / total_ngf if total_ngf else 0.0

    return RoomResult(
        name=room.name,
        room_use=use,
        row=row_index,
        ebf=room.ebf,
        ngf_m2=room.ngf,
        share=share,
        geraete_kw=geraete_kw,
        geraete_mwh=geraete_mwh,
        prozessanlagen_kw=prozessanlagen_kw,
        prozessanlagen_mwh=prozessanlagen_mwh,
        beleuchtung_kw=beleuchtung_kw,
        beleuchtung_mwh=beleuchtung_mwh,
        lueftung_volume_flow_m3h=flow,
        lueftung_kw=lueftung_kw,
        lueftung_mwh=lueftung_mwh,
        kuehlung_kw=kuehlung_kw,
        kuehlung_mwh=kuehlung_mwh,
        heizung_kw=heizung_kw,
        heizung_mwh=heizung_mwh,
        warmwasser_l_d=warmwasser_l_d,
        warmwasser_mwh=warmwasser_mwh,
    )


def _room_aggregation(
    building: BuildingInput,
    lookup: KpiLookup,
    construction_factor_pct: float,
) -> tuple[tuple[RoomResult, ...], RoomTotals]:
    """All room rows plus the totals row ``Gebäude!D33:W35`` (Rechenwert).

    The Rechenwert row equals the Total row (row 33) unless an external
    override (row 34) is present; the input model has no override cell, so
    ``D35 = D33`` etc.  EBF and GF follow ch02 §2.7.
    """
    total_ngf = sum(room.ngf for room in building.rooms)
    rooms = tuple(
        compute_room_row(room, building.value_kind, lookup, total_ngf, i)
        for i, room in enumerate(building.rooms, start=12)
    )

    def total(getter) -> float:
        return sum(getter(r) for r in rooms)

    ebf_sum = sum(r.ngf_m2 for r in rooms if r.ebf)
    factor = 1.0 + construction_factor_pct / 100.0

    totals = RoomTotals(
        ngf_m2=total_ngf,
        ebf_m2=ebf_sum * factor,
        gf_m2=total_ngf * factor,
        share_sum=total(getter=lambda r: r.share),
        geraete_kw=total(getter=lambda r: r.geraete_kw),
        geraete_mwh=total(getter=lambda r: r.geraete_mwh),
        prozessanlagen_kw=total(getter=lambda r: r.prozessanlagen_kw),
        prozessanlagen_mwh=total(getter=lambda r: r.prozessanlagen_mwh),
        beleuchtung_kw=total(getter=lambda r: r.beleuchtung_kw),
        beleuchtung_mwh=total(getter=lambda r: r.beleuchtung_mwh),
        lueftung_volume_flow_m3h=total(getter=lambda r: r.lueftung_volume_flow_m3h),
        lueftung_kw=total(getter=lambda r: r.lueftung_kw),
        lueftung_mwh=total(getter=lambda r: r.lueftung_mwh),
        kuehlung_kw=total(getter=lambda r: r.kuehlung_kw),
        kuehlung_mwh=total(getter=lambda r: r.kuehlung_mwh),
        heizung_kw=total(getter=lambda r: r.heizung_kw),
        heizung_mwh=total(getter=lambda r: r.heizung_mwh),
        warmwasser_l_d=total(getter=lambda r: r.warmwasser_l_d),
        warmwasser_mwh=total(getter=lambda r: r.warmwasser_mwh),
    )
    return rooms, totals


# ---------------------------------------------------------------------------
# Ventilation aggregation (ch02 §2.5 + ch04 §4.12 write-back)
# ---------------------------------------------------------------------------


def _ventilation_aggregation(
    building: BuildingInput,
    lookup: KpiLookup,
    rooms: Sequence[RoomResult],
    ahu_results: Mapping[str, AhuAnnualResult],
) -> tuple[tuple[VentilationSystemResult, ...], VentilationTotals]:
    """``Lüftung!A7:Z23`` — per-system rows and the totals row 23.

    C = SUMIF over the room flows, D = process flow (Σ Std!E·A over the
    rooms of the system), F = project override or C, H = F·SFP/1000,
    I/Q/R/S/T from the per-system :class:`AhuAnnualResult` (ch04 §4.12
    write-back), K = ROUND(I·1000/H, -1).
    """
    room_system = {room.name: room.lueftung_system for room in building.rooms}
    systems: list[VentilationSystemResult] = []
    for system in building.ventilation:
        volume = sum(
            r.lueftung_volume_flow_m3h for r in rooms if room_system.get(r.name) == system.id
        )
        process = 0.0
        for room in building.rooms:
            if room.lueftung_system == system.id:
                process += lookup.process_fresh_air(str(room.room_use_id)) * room.ngf
        effective = system.effective_volume_flow() or volume
        fan_power = effective * (system.sfp or 0.0) / 1000.0
        ahu = ahu_results.get(system.id, _ZERO_AHU)
        fan_energy = ahu.ventilator_kwh / 1000.0
        full_load_hours = _round_excel(fan_energy * 1000.0 / fan_power, -1) if fan_power else 0.0
        systems.append(
            VentilationSystemResult(
                id=system.id,
                room_use=system.room_use or "",
                volume_flow_m3h=volume,
                process_flow_m3h=process,
                effective_flow_m3h=effective,
                fan_power_kw=fan_power,
                fan_energy_mwh=fan_energy,
                full_load_hours=full_load_hours,
                luftkuehlung_kw=ahu.luftkuehlung_kw,
                luftkuehlung_mwh=ahu.luftkuehlung_kwh / 1000.0,
                lufterwaermung_kw=ahu.lufterwaermung_kw,
                lufterwaermung_mwh=ahu.lufterwaermung_kwh / 1000.0,
            )
        )
    result = tuple(systems)
    totals = VentilationTotals(
        volume_flow_m3h=sum(s.volume_flow_m3h for s in result),
        process_flow_m3h=sum(s.process_flow_m3h for s in result),
        fan_power_kw=sum(s.fan_power_kw for s in result),
        fan_energy_mwh=sum(s.fan_energy_mwh for s in result),
        luftkuehlung_kw=sum(s.luftkuehlung_kw for s in result),
        luftkuehlung_mwh=sum(s.luftkuehlung_mwh for s in result),
        lufterwaermung_kw=sum(s.lufterwaermung_kw for s in result),
        lufterwaermung_mwh=sum(s.lufterwaermung_mwh for s in result),
    )
    return result, totals


# ---------------------------------------------------------------------------
# Generation (ch05 §5.4–§5.6)
# ---------------------------------------------------------------------------


def _generation_group(
    group: GenerationGroupInput,
    catalog: GenerationCatalog,
    demand_power_kw: float,
    demand_energy_mwh: float,
    ww_demand_l_d: float = 0.0,
    aufheizzeit_h: float = 6.0,
) -> GenerationGroupResult:
    """One generation group incl. the Total row (ch05 §5.4–§5.6).

    The WW group converts the daily hot-water volume into a power demand
    (ch05 §5.5): ``V·4.186/3.6·50/t_Aufh/1000`` kW.
    """
    if group.kind == "ww":
        base_power = (
            ww_demand_l_d
            * WW_SPECIFIC_HEAT
            / KJ_PER_WH
            * WW_TEMP_RISE_K
            / aufheizzeit_h
            / 1000.0
        )
        base_energy = demand_energy_mwh
    else:
        base_power = demand_power_kw
        base_energy = demand_energy_mwh

    generators: list[GeneratorResult] = []
    for gen in group.generators:
        spec = catalog.lookup(group.kind, gen.name)
        losses = gen.losses_project_pct if gen.losses_project_pct is not None else gen.losses_standard_pct
        loss_factor = 1.0 + losses / 100.0
        demand_power = base_power * gen.coverage_power_pct / 100.0 * loss_factor
        demand_energy = base_energy * gen.coverage_energy_pct / 100.0 * loss_factor
        full_load_hours = demand_energy * 1000.0 / demand_power if demand_power else 0.0
        eta = gen.eta_project if gen.eta_project is not None else spec.eta_standard
        end_power = demand_power / eta if spec.eta_standard else 0.0
        end_energy = demand_energy / eta if spec.eta_standard else 0.0
        generators.append(
            GeneratorResult(
                code=spec.code,
                name=gen.name,
                energy_carrier=spec.energy_carrier,
                eta_standard=spec.eta_standard,
                eta_effective=eta,
                coverage_power_pct=gen.coverage_power_pct,
                coverage_energy_pct=gen.coverage_energy_pct,
                losses_pct=losses,
                demand_power_kw=demand_power,
                demand_energy_mwh=demand_energy,
                full_load_hours=full_load_hours,
                end_power_kw=end_power,
                end_energy_mwh=end_energy,
            )
        )
    result = tuple(generators)
    total_power = sum(g.demand_power_kw for g in result)
    total_energy = sum(g.demand_energy_mwh for g in result)
    total_end_power = sum(g.end_power_kw for g in result)
    total_end_energy = sum(g.end_energy_mwh for g in result)
    return GenerationGroupResult(
        kind=group.kind,
        demand_power_kw=base_power,
        demand_energy_mwh=base_energy,
        total_demand_power_kw=total_power,
        total_demand_energy_mwh=total_energy,
        total_full_load_hours=total_energy * 1000.0 / total_power if total_power else 0.0,
        total_end_power_kw=total_end_power,
        total_end_energy_mwh=total_end_energy,
        coverage_power_pct=sum(g.coverage_power_pct for g in result),
        coverage_energy_pct=sum(g.coverage_energy_pct for g in result),
        generators=result,
    )


# ---------------------------------------------------------------------------
# Resultate (ch05 §5.8–§5.10)
# ---------------------------------------------------------------------------


def _sumif(generators: Sequence[GeneratorResult], row: str, power: bool) -> float:
    """``SUMIF(Erzeugung!$R$…,$B7,…)`` — sum by Energieträger (ch05 §5.9).

    Unknown carrier labels (e.g. "Sonne" — not one of the 8 Resultate rows)
    simply do not match and contribute 0, like the workbook SUMIF.
    """
    total = 0.0
    for gen in generators:
        if CARRIER_LABEL_TO_ROW.get(gen.energy_carrier) == row:
            total += gen.end_power_kw if power else gen.end_energy_mwh
    return total


def _resultate_matrix(
    ag_power_kw: float,
    ag_energy_mwh: float,
    room_totals: RoomTotals,
    vent_totals: VentilationTotals,
    generation: Sequence[GenerationGroupResult],
) -> ResultateMatrix:
    """``Resultate!D7:U15`` (ch05 §5.8/§5.9).

    Power/energy pairs per use; Kühlung power is the group total (N7 =
    ``Erzeugung!P10``), Kühlung energy and Heizung/Warmwasser are the SUMIF
    by carrier.
    """
    by_kind = {g.kind: g for g in generation}
    cooling = by_kind.get("cooling")
    heating = by_kind.get("heating")
    ww = by_kind.get("ww")

    carriers = RESULTATE_CARRIERS
    power: dict[str, dict[str, float]] = {use: {c: 0.0 for c in carriers} for use in RESULTATE_USES}
    energy: dict[str, dict[str, float]] = {use: {c: 0.0 for c in carriers} for use in RESULTATE_USES}

    def set_el(use: str, p: float, e: float) -> None:
        power[use]["El"] = p
        energy[use]["El"] = e

    set_el("allg_gebaeudetechnik", ag_power_kw, ag_energy_mwh)
    set_el("geraete", room_totals.geraete_kw, room_totals.geraete_mwh)
    set_el("prozessanlagen", room_totals.prozessanlagen_kw, room_totals.prozessanlagen_mwh)
    set_el("beleuchtung", room_totals.beleuchtung_kw, room_totals.beleuchtung_mwh)
    set_el("lueftung", vent_totals.fan_power_kw, vent_totals.fan_energy_mwh)

    if cooling is not None:
        power["kuehlung"]["El"] = cooling.total_end_power_kw  # N7 = P10 (group total)
        for row in carriers:
            energy["kuehlung"][row] = _sumif(cooling.generators, row, power=False)
    if heating is not None:
        for row in carriers:
            power["heizung"][row] = _sumif(heating.generators, row, power=True)
            energy["heizung"][row] = _sumif(heating.generators, row, power=False)
    if ww is not None:
        for row in carriers:
            power["warmwasser"][row] = _sumif(ww.generators, row, power=True)
            energy["warmwasser"][row] = _sumif(ww.generators, row, power=False)

    for row in carriers:
        power["total"][row] = sum(power[use][row] for use in RESULTATE_USES[:-1])
        energy["total"][row] = sum(energy[use][row] for use in RESULTATE_USES[:-1])
    for use in RESULTATE_USES:
        power[use]["Total"] = sum(power[use][row] for row in carriers)
        energy[use]["Total"] = sum(energy[use][row] for row in carriers)

    return ResultateMatrix(power=power, energy=energy)


def _weighted_rows(
    matrix: ResultateMatrix,
    weights: WeightTable,
    ebf_m2: float,
) -> ResultateWeighted:
    """``Resultate!D21:U25`` weighted indicators (ch05 §5.10).

    Row 21 (NEGF) reproduces the workbook's copy-paste error at ``I21``
    (Prozessanlagen uses the THGE weight column Y — the golden caches depend
    on it).  Row 22 (PEne) fixes the ``G22`` error of the workbook (ch05
    §5.12-6).  The per-area mirrors (D21/F21/…) are E·1000/EBF.
    """
    uses = RESULTATE_USES[:-1]  # 8 use columns (without the Total column)
    negf: dict[str, float] = {}
    pene: dict[str, float] = {}
    thge: dict[str, float] = {}
    for use in uses:
        negf[use] = sum(matrix.energy[use][row] * weights.negf[row] for row in RESULTATE_CARRIERS)
        pene[use] = sum(matrix.energy[use][row] * weights.pene[row] for row in RESULTATE_CARRIERS)
        thge[use] = sum(matrix.energy[use][row] * weights.thge[row] for row in RESULTATE_CARRIERS)
    # Workbook copy-paste error: I21 (NEGF · Prozessanlagen) uses THGE weights.
    negf["prozessanlagen"] = thge["prozessanlagen"]
    # Porting fix (ch05 §5.12-6): G22/F22 (PEne · Geräte) repeated column E in
    # the workbook; the port uses the correct column G (recomputed above).

    negf["total"] = sum(negf[use] for use in uses)
    pene["total"] = sum(pene[use] for use in uses)
    thge["total"] = sum(thge[use] for use in uses)

    per_area: dict[str, dict[str, float]] = {}
    for name, row in (("negf", negf), ("pene", pene), ("thge", thge)):
        per_area[name] = (
            {use: value * 1000.0 / ebf_m2 for use, value in row.items()} if ebf_m2 else dict(row)
        )
    return ResultateWeighted(
        energy_mwh={"negf": negf, "pene": pene, "thge": thge}, per_area_kwh_m2=per_area
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def _room_generation_division(
    rooms: tuple[RoomResult, ...],
    building_rooms: tuple[object, ...],
    catalog: GenerationCatalog,
) -> tuple[tuple[RoomGenerationResult, ...], dict[str, tuple[float, float]]]:
    """Room-level generators: their covered demand and end energy per kind.

    Returns the per-generator results and, per kind, the total covered
    ``(power_kw, energy_mwh)`` that the building-level generation groups
    must not see again (their demand is reduced by it).
    """
    shares: list[RoomGenerationResult] = []
    covered: dict[str, list[float]] = {}
    for building_room, room in zip(building_rooms, rooms):
        for gen in getattr(building_room, "generations", ()):
            if gen.kind not in ("heating", "cooling", "ww"):
                continue
            if gen.kind == "heating":
                power, energy = room.heizung_kw, room.heizung_mwh
            elif gen.kind == "cooling":
                power, energy = room.kuehlung_kw, room.kuehlung_mwh
            else:
                power, energy = 0.0, room.warmwasser_mwh
            spec = catalog.lookup(gen.kind, gen.catalog_code)
            loss_factor = 1.0 + gen.losses
            covered_power = power * gen.coverage * loss_factor
            covered_energy = energy * gen.coverage * loss_factor
            eta = spec.eta_standard
            shares.append(
                RoomGenerationResult(
                    room=room.name,
                    kind=gen.kind,
                    code=spec.code,
                    carrier=spec.energy_carrier,
                    eta=eta,
                    coverage=gen.coverage,
                    covered_power_kw=covered_power,
                    covered_energy_mwh=covered_energy,
                    end_power_kw=covered_power / eta if eta else 0.0,
                    end_energy_mwh=covered_energy / eta if eta else 0.0,
                )
            )
            covered.setdefault(gen.kind, [0.0, 0.0])
            covered[gen.kind][0] += covered_power
            covered[gen.kind][1] += covered_energy
    return (
        tuple(shares),
        {kind: (values[0], values[1]) for kind, values in covered.items()},
    )


def aggregate(inp: AggregationInput) -> AggregationResult:
    """Run the full aggregation chain (rooms → ventilation → generation → Resultate).

    Raises:
        KpiLookupError: when the KPI lookup cannot provide a needed value.
        KeyError: when a generator name is absent from the catalogue.
    """
    rooms, room_totals = _room_aggregation(inp.building, inp.kpi_lookup, inp.construction_factor_pct)
    ventilation, vent_totals = _ventilation_aggregation(
        inp.building, inp.kpi_lookup, rooms, inp.ahu_results
    )

    room_generation: tuple[RoomGenerationResult, ...] = ()
    generation: list[GenerationGroupResult] = []
    if inp.generation_groups:
        catalog = inp.generation_catalog
        if catalog is None:
            raise ValueError("generation_catalog is required when generation groups are given")
        room_generation, room_covered = _room_generation_division(
            rooms, inp.building.rooms, catalog
        )
        for group in inp.generation_groups:
            if group.kind == "cooling":
                demand_power = room_totals.kuehlung_kw + vent_totals.luftkuehlung_kw
                demand_energy = room_totals.kuehlung_mwh + vent_totals.luftkuehlung_mwh
                ww_l_d = 0.0
            elif group.kind == "heating":
                demand_power = room_totals.heizung_kw + vent_totals.lufterwaermung_kw
                demand_energy = room_totals.heizung_mwh + vent_totals.lufterwaermung_mwh
                ww_l_d = 0.0
            elif group.kind == "ww":
                demand_power = 0.0  # converted inside _generation_group
                demand_energy = room_totals.warmwasser_mwh
                ww_l_d = room_totals.warmwasser_l_d
            else:  # pragma: no cover - validated by the caller
                raise ValueError(f"unknown generation group kind {group.kind!r}")
            covered_power, covered_energy = room_covered.get(group.kind, (0.0, 0.0))
            generation.append(
                _generation_group(
                    group,
                    catalog,
                    demand_power - covered_power,
                    demand_energy - covered_energy,
                    ww_demand_l_d=ww_l_d,
                    aufheizzeit_h=inp.aufheizzeit_h,
                )
            )

    matrix = _resultate_matrix(
        inp.ag_power_kw,
        inp.ag_energy_mwh,
        room_totals,
        vent_totals,
        generation,
    )
    weighted = _weighted_rows(matrix, inp.weights, room_totals.ebf_m2)

    return AggregationResult(
        rooms=rooms,
        room_totals=room_totals,
        ventilation=ventilation,
        ventilation_totals=vent_totals,
        generation=tuple(generation),
        room_generation=room_generation,
        resultate=matrix,
        resultate_weighted=weighted,
    )
