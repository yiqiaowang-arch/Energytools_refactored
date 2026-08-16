"""``NativeBackend`` — the pure-Python runtime backend of the calculation engine.

The native backend (doc part 04 §5.3) plugs the verified native model —
psychrometrics (:mod:`energytools.engine.native.psychrometrics`), the AHU
temperature-bin engine (:mod:`energytools.engine.native.ahu`) and the building
aggregation / ``Resultate`` summary (:mod:`energytools.engine.native.aggregation`)
— into the :class:`~energytools.engine.backends.EngineBase` contract and
consumes the real V221 dataset (``energytools.raumdaten``) as its data source:

- the room KPI intensities come from the dataset profiles (the ``Res`` matrix
  backfilled into the V221 package, see ``verify/backfill_v221_kpi.py``);
- the ventilation systems drive one :class:`AhuInput` each, with the station
  climate (temperature-bin hours, per-bin humidity, pressure) read from
  ``ds.climate`` and the full-load hours from the ``Volll_Lüft`` table;
- the generators resolve through the built-in ``Nutzungsgrad`` catalogue
  (:class:`NutzungsgradCatalog`).

Every input maps to workbook semantics verbatim (Lüftung, Erzeugung,
Resultate, Energieträger, Deckungsgrad, Speicher-/Verteilverluste); the
``assumptions``/``warnings`` document where the input model or the dataset
defaults deviate from a full workbook session.
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import energytools
from energytools.engine.backends import WORKBOOK, EngineBase
from energytools.engine.model import (
    BuildingInput,
    EnergyCarrier,
    GenerationSystem,
    ValidationReport,
    VentilationSystem,
    VersionInfo,
)
from energytools.engine.native.aggregation import (
    AggregationInput,
    DatasetResLookup,
    GenerationGroupInput,
    GenerationInput,
    NutzungsgradCatalog,
    aggregate,
)
from energytools.engine.native.ahu import AhuAnnualResult, AhuInput, compute_ahu_annual
from energytools.engine.result import CalculationTrace, Results, TraceStep
from energytools.raumdaten.dataset import load_dataset

__all__ = ["NativeBackend"]

#: VentilationSystem regulation (workbook label) → AhuInput regulation (the
#: ahu module uses the German Std labels "einstufig"/"zweistufig"/"stufenlos").
_REGULATION_TO_AHU = {
    "1-stufig": "einstufig",
    "2-stufig": "zweistufig",
    "stufenlos": "stufenlos",
}

#: Resultate carrier rows → :class:`EnergyCarrier` codes (Pell/HSch/StH all
#: map to wood; Bio has no dedicated member).
_RESULTATE_ROW_TO_CARRIER = {
    "El": EnergyCarrier.ELECTRICITY,
    "HEL": EnergyCarrier.HEATING_OIL,
    "Gas": EnergyCarrier.NATURAL_GAS,
    "Pell": EnergyCarrier.WOOD,
    "HSch": EnergyCarrier.WOOD,
    "StH": EnergyCarrier.WOOD,
    "Bio": EnergyCarrier.OTHER,
    "FW": EnergyCarrier.DISTRICT_HEATING,
}

#: AhuInput defaults of the example system LA01 (Zürich-MeteoSchweiz) —
#: documented in :class:`AhuInput`; used when a system field is absent.
_AHU_DEFAULT_T_SUPPLY_SUMMER = 20.0
_AHU_DEFAULT_T_SUPPLY_WINTER = 21.0
_AHU_DEFAULT_WRG = 0.8
_AHU_DEFAULT_PRESSURE = 948.225968475814

#: The climate-station id of the KPI-matrix default (the workbook was saved
#: with Zürich-MeteoSchweiz selected; the Klimakälte/Heizwärme profile values
#: carry that station's `Qhc_Klimastat` cache).
KPI_DEFAULT_CLIMATE_STATION = 40


class NativeBackend(EngineBase):
    """The native (pure-Python) calculation backend (``name`` = ``"native"``).

    Args:
        dataset_dir: Directory of the installed dataset packages (defaults to
            ``"data/datasets"``); the release is loaded on first ``calculate``
            and cached per backend instance.
        implementation_version: Overrides the library version in
            ``Results.backend`` (defaults to ``energytools.__version__``).
    """

    name = "native"

    def __init__(
        self,
        dataset_dir: str | Path = "data/datasets",
        implementation_version: str | None = None,
    ) -> None:
        """See the class docstring."""
        self.dataset_dir = str(dataset_dir)
        self.version = implementation_version or energytools.__version__
        self._datasets: dict[str, Any] = {}

    # -- dataset access -----------------------------------------------------

    def _dataset(self, release_id: str) -> Any:
        """The frozen dataset of a release, loaded on demand and cached."""
        if release_id not in self._datasets:
            self._datasets[release_id] = load_dataset(release_id, path=self.dataset_dir)
        return self._datasets[release_id]

    # -- EngineBase contract ------------------------------------------------

    def validate(self, input_: BuildingInput, dataset: str) -> ValidationReport:
        """Domain validation plus the dataset availability check.

        Reports a hard error when the release is not installed (the dataset is
        required for the native calculation) and the capability warning for
        station-dependent KPI columns when the building's station is not the
        KPI default.
        """
        report = input_.validate()
        warnings = list(report.warnings)
        errors = list(report.errors)
        if dataset:
            try:
                self._dataset(dataset)
            except Exception as exc:  # DatasetNotFoundError / validation errors
                errors.append(f"dataset release {dataset!r} unavailable: {exc}")
        if input_.climate_station_id != KPI_DEFAULT_CLIMATE_STATION:
            warnings.append(
                f"native backend: the Klimakälte/Heizwärme KPI columns of the "
                f"dataset carry the {KPI_DEFAULT_CLIMATE_STATION} "
                "(Zürich-MeteoSchweiz) default; the building uses station "
                f"{input_.climate_station_id}"
            )
        return ValidationReport(errors=tuple(errors), warnings=tuple(warnings))

    def calculate(self, input_: BuildingInput, dataset: str, model_release: str) -> Results:
        """Run the native calculation chain and build the full ``Results``.

        Chain: validate → rooms (dataset KPI lookup) → ventilation (AHU
        temperature-bin engine per system) → generation (Nutzungsgrad
        catalogue) → resultate (energytools.engine.native.aggregation).
        The ``versions`` quadruple built here is provisional (climate
        ``"unknown"``); the engine replaces it after the call.
        """
        report = input_.validate()
        result_id = str(uuid.uuid4())
        ds = self._dataset(dataset)
        package = ds.to_package_dict()
        lookup = DatasetResLookup(package)
        catalog = NutzungsgradCatalog()

        # -- per-system AHU (Lüftung → Berechnung LU) ------------------------
        ahu_results: dict[str, AhuAnnualResult] = {}
        ahu_assumptions: list[str] = []
        for system in input_.ventilation:
            ahu_input, assumptions = self._ahu_input(ds, input_, system, lookup)
            ahu_results[system.id] = compute_ahu_annual(ahu_input)
            ahu_assumptions.extend(assumptions)

        # -- generation groups (Erzeugung → Nutzungsgrad) --------------------
        generation_groups = self._generation_groups(input_.generation, catalog)

        # -- aggregation (rooms → ventilation → generation → Resultate) -----
        result = aggregate(
            AggregationInput(
                building=input_,
                kpi_lookup=lookup,
                ahu_results=ahu_results,
                generation_groups=generation_groups,
                generation_catalog=catalog,
            )
        )

        # -- results assembly ------------------------------------------------
        per_room = {r.name: dataclasses.asdict(r) for r in result.rooms}
        per_system = {s.id: dataclasses.asdict(s) for s in result.ventilation}
        per_carrier = self._per_carrier(result)
        totals = self._totals(result, input_)

        assumptions = self._assumptions(input_, ahu_assumptions)
        warnings = list(report.warnings)
        if input_.climate_station_id != KPI_DEFAULT_CLIMATE_STATION:
            warnings.append(
                f"Klimakälte/Heizwärme KPI columns use the dataset's "
                f"{KPI_DEFAULT_CLIMATE_STATION} (Zürich-MeteoSchweiz) default; "
                f"the building uses station {input_.climate_station_id}"
            )

        intermediates = {
            "sources": {
                "rooms": "Gebäude (KPI matrix KZ_Raum_2024)",
                "ventilation": "Lüftung",
                "ahu": "Berechnung LU (temperature-bin method)",
                "generation": "Erzeugung",
                "catalog": "Nutzungsgrad",
                "resultate": "Resultate",
                "workbook": WORKBOOK,
            },
            "ahu": {
                system_id: {
                    "luftkuehlung_kwh": ahu.luftkuehlung_kwh,
                    "luftkuehlung_kw": ahu.luftkuehlung_kw,
                    "lufterwaermung_kwh": ahu.lufterwaermung_kwh,
                    "lufterwaermung_kw": ahu.lufterwaermung_kw,
                    "ventilator_kwh": ahu.ventilator_kwh,
                    "ventilator_kw": ahu.ventilator_kw,
                    "total_kwh": ahu.total_kwh,
                    "total_kw": ahu.total_kw,
                }
                for system_id, ahu in ahu_results.items()
            },
            "resultate": {
                "power": {u: dict(c) for u, c in result.resultate.power.items()},
                "energy": {u: dict(c) for u, c in result.resultate.energy.items()},
            },
            "resultate_weighted": {
                "energy_mwh": {
                    i: dict(u) for i, u in result.resultate_weighted.energy_mwh.items()
                },
                "per_area_kwh_m2": {
                    i: dict(u) for i, u in result.resultate_weighted.per_area_kwh_m2.items()
                },
            },
        }

        trace = CalculationTrace(
            result_id=result_id,
            steps=(
                TraceStep(
                    id="validate",
                    kind="validation",
                    label="Input validation (Gebäude sheet)",
                    inputs={
                        "climate_station_id": input_.climate_station_id,
                        "rooms": len(input_.rooms),
                        "value_kind": input_.value_kind.value,
                    },
                    outputs={
                        "valid": report.valid,
                        "errors": list(report.errors),
                        "warnings": list(report.warnings),
                    },
                    provenance={"workbook": WORKBOOK, "sheet": "Gebäude"},
                ),
                TraceStep(
                    id="rooms",
                    kind="kpi",
                    label="Room KPIs (KPI matrix KZ_Raum_2024)",
                    inputs={"rooms": [room.name for room in input_.rooms]},
                    outputs={"rooms": [r.name for r in result.rooms]},
                    formula="KPI intensity × NGF / 1000 (ch02 §2.3–§2.6)",
                    provenance={"workbook": WORKBOOK, "sheet": "KZ_Raum_2024"},
                ),
                TraceStep(
                    id="ventilation",
                    kind="kpi",
                    label="Lüftung systems",
                    inputs={"systems": [system.id for system in input_.ventilation]},
                    outputs=per_system,
                    formula="Projekt → Prozess → Standard flow priority; F·SFP/1000",
                    provenance={"workbook": WORKBOOK, "sheet": "Lüftung"},
                ),
                TraceStep(
                    id="ahu",
                    kind="physics",
                    label="AHU temperature-bin engine (Berechnung LU)",
                    inputs={
                        "systems": [system.id for system in input_.ventilation],
                        "climate_station_id": input_.climate_station_id,
                    },
                    outputs={
                        system_id: {
                            "luftkuehlung_kwh": ahu.luftkuehlung_kwh,
                            "lufterwaermung_kwh": ahu.lufterwaermung_kwh,
                            "ventilator_kwh": ahu.ventilator_kwh,
                        }
                        for system_id, ahu in ahu_results.items()
                    },
                    formula="Temperature-bin method (ch04, formulas 1–10)",
                    provenance={"workbook": WORKBOOK, "sheet": "Berechnung LU"},
                ),
                TraceStep(
                    id="generation",
                    kind="kpi",
                    label="Erzeugung systems",
                    inputs={
                        "systems": [system.id for system in input_.generation],
                        "catalog": "Nutzungsgrad",
                    },
                    outputs={"groups": [g.kind for g in result.generation]},
                    formula="demand × Deckungsgrad × (1 + losses) / η (ch05 §5.4–§5.6)",
                    provenance={"workbook": WORKBOOK, "sheet": "Erzeugung"},
                ),
                TraceStep(
                    id="resultate",
                    kind="aggregation",
                    label="Resultate per Energieträger",
                    inputs={"carriers": sorted(per_carrier)},
                    outputs=per_carrier,
                    formula="SUMIF by Energieträger (ch05 §5.8–§5.10)",
                    provenance={"workbook": WORKBOOK, "sheet": "Resultate"},
                ),
            ),
        )

        return Results(
            result_id=result_id,
            versions=VersionInfo(
                dataset=dataset,
                model=model_release,
                implementation=self.version,
                climate="unknown",
            ),
            inputs_hash=input_.inputs_hash(),
            input_=input_,
            backend=f"{self.name}@{self.version}",
            per_room=per_room,
            per_system=per_system,
            per_carrier=per_carrier,
            totals=totals,
            intermediates=intermediates,
            assumptions=assumptions,
            warnings=tuple(warnings),
            overridden_values=(),
            computed_at=datetime.now(timezone.utc),
            trace=trace,
        )

    # -- AHU input construction ---------------------------------------------

    def _resolve_nutzid(self, ds: Any, use: str | int | None) -> int | None:
        """Resolve a room-use reference (name, SIA code or nutzid) → nutzid."""
        if use is None:
            return None
        if isinstance(use, int):
            return use
        key = str(use).strip()
        for room_use in ds.room_uses():
            if room_use.name.de == key or room_use.code == key or str(room_use.nutzid) == key:
                return room_use.nutzid
        return None

    def _ahu_input(
        self,
        ds: Any,
        building: BuildingInput,
        system: VentilationSystem,
        lookup: DatasetResLookup,
    ) -> tuple[AhuInput, list[str]]:
        """Build the :class:`AhuInput` of one system from inputs + climate.

        Volume flow: ``effective_volume_flow()`` (Projekt → Prozess →
        Standard), falling back to the hygienic+process flow of the rooms on
        the system.  Fan power: ``fan_power``, falling back to ``F·SFP/1000``.
        Full-load hours: the system value, falling back to the dataset
        ``Volll_Lüft`` table by room use × regulation.  Climate: the station's
        temperature-bin hours, per-bin humidity ratio and pressure.
        """
        assumptions: list[str] = []

        volume_flow = system.effective_volume_flow()
        if volume_flow is None:
            volume_flow = sum(
                lookup.hygienic_fresh_air(str(room.room_use_id)) * room.ngf
                + lookup.process_fresh_air(str(room.room_use_id)) * room.ngf
                for room in building.rooms
                if room.lueftung_system == system.id
            )
            assumptions.append(
                f"system {system.id}: no project volume flow; using the room "
                f"hygienic+process flow {volume_flow:.3f} m³/h"
            )
        sfp = system.sfp if system.sfp is not None else 0.8
        fan_power = system.fan_power
        if fan_power is None:
            fan_power = volume_flow * sfp / 1000.0
            assumptions.append(
                f"system {system.id}: no fan power; derived as V·SFP/1000 = "
                f"{fan_power:.6f} kW"
            )

        regulation = _REGULATION_TO_AHU.get(system.regulation or "", "einstufig")
        full_load_hours = system.full_load_hours
        if full_load_hours is None:
            nutzid = self._resolve_nutzid(ds, system.room_use)
            if nutzid is not None:
                try:
                    full_load_hours = ds.full_load_hours().hours(
                        nutzid, system.regulation or "1-stufig"
                    )
                except Exception:
                    full_load_hours = None
            if full_load_hours is None:
                full_load_hours = 3900.0
                assumptions.append(
                    f"system {system.id}: no full-load hours resolvable; using 3900 h/a"
                )
            else:
                assumptions.append(
                    f"system {system.id}: full-load hours {full_load_hours} h/a "
                    f"from the Volll_Lüft table"
                )

        station = ds.climate().station(building.climate_station_id)
        pressure = _AHU_DEFAULT_PRESSURE
        if station.winter_design.get("pressure") is not None:
            pressure = float(station.winter_design["pressure"].value)
        else:
            assumptions.append(
                f"station {station.id}: no pressure in the dataset; using the "
                f"Zürich default {pressure} mbar"
            )
        if station.temperature_bins is not None:
            bin_hours = tuple(float(bin_.hours) for bin_ in station.temperature_bins)
        else:
            bin_hours = (0.0,) * 61
            assumptions.append(
                f"station {station.id}: no temperature bins in the dataset; "
                "using zero bin hours"
            )
        if station.bin_humidity_ratio is not None:
            bin_humidity_ratio = tuple(float(x) for x in station.bin_humidity_ratio)
        else:
            bin_humidity_ratio = (0.0,) * 61
            assumptions.append(
                f"station {station.id}: no per-bin humidity in the dataset; "
                "using dry air (x = 0 g/kg)"
            )

        t_supply_summer = (
            system.kuehlfall_t
            if system.kuehlfall_t is not None
            else _AHU_DEFAULT_T_SUPPLY_SUMMER
        )
        t_supply_winter = (
            system.heizfall_t
            if system.heizfall_t is not None
            else _AHU_DEFAULT_T_SUPPLY_WINTER
        )
        if system.kuehlfall_t is None:
            assumptions.append(
                f"system {system.id}: no Kühlfall setpoint; using {t_supply_summer} °C"
            )
        if system.heizfall_t is None:
            assumptions.append(
                f"system {system.id}: no Heizfall setpoint; using {t_supply_winter} °C"
            )
        wrg = system.wrg if system.wrg is not None else _AHU_DEFAULT_WRG
        if system.wrg is None:
            assumptions.append(
                f"system {system.id}: no WRG ratio; using {wrg} (example default)"
            )

        return (
            AhuInput(
                system_name=system.id,
                volume_flow=volume_flow,
                sfp=sfp,
                fan_power_total=fan_power,
                regulation=regulation,
                full_load_hours=full_load_hours,
                wrg_efficiency=wrg,
                t_supply_summer=t_supply_summer,
                t_supply_winter=t_supply_winter,
                pressure=pressure,
                bin_hours=bin_hours,
                bin_humidity_ratio=bin_humidity_ratio,
            ),
            assumptions,
        )

    # -- generation mapping --------------------------------------------------

    @staticmethod
    def _generation_groups(
        systems: tuple[GenerationSystem, ...], catalog: NutzungsgradCatalog
    ) -> tuple[GenerationGroupInput, ...]:
        """``GenerationSystem`` rows → the three :class:`GenerationGroupInput`.

        The input model carries one Deckungsgrad and one Speicher-/
        Verteilverluste value, applied to both the power and the energy
        coverage and as the standard losses (no project overrides).
        """
        groups: list[GenerationGroupInput] = []
        for kind in ("cooling", "heating", "ww"):
            generators: list[GenerationInput] = []
            for system in systems:
                if system.kind != kind:
                    continue
                spec = catalog.lookup(kind, system.catalog_code)
                generators.append(
                    GenerationInput(
                        name=spec.name,
                        coverage_power_pct=system.coverage * 100.0,
                        coverage_energy_pct=system.coverage * 100.0,
                        losses_standard_pct=system.losses * 100.0,
                    )
                )
            if generators:
                groups.append(GenerationGroupInput(kind=kind, generators=tuple(generators)))
        return tuple(groups)

    # -- results helpers -----------------------------------------------------

    @staticmethod
    def _per_carrier(result: Any) -> dict[str, float]:
        """Total Endenergie per :class:`EnergyCarrier` from the Resultate rows.

        The Resultate matrix rows (``El``/``HEL``/…/``FW``) merge into the
        carrier codes (Pell + HSch + StH → ``holz``); the energy of the
        carrier-total row is used.
        """
        merged: dict[str, float] = {}
        for row in result.resultate.energy["total"]:
            if row == "Total":
                continue
            carrier = _RESULTATE_ROW_TO_CARRIER[row]
            merged[carrier.value] = merged.get(carrier.value, 0.0) + result.resultate.energy[
                "total"
            ][row]
        return {key: round(value, 6) for key, value in merged.items()}

    def _totals(self, result: Any, input_: BuildingInput) -> dict[str, float]:
        """The building totals: rooms, Lüftung, generation Endenergie."""
        rt = result.room_totals
        vt = result.ventilation_totals
        generation_energy = {
            group.kind: group.total_end_energy_mwh for group in result.generation
        }
        return {
            "ngf_m2": rt.ngf_m2,
            "ebf_m2": rt.ebf_m2,
            "gf_m2": rt.gf_m2,
            "rooms": len(input_.rooms),
            "ventilation_systems": len(input_.ventilation),
            "geraete_kw": rt.geraete_kw,
            "geraete_mwh": rt.geraete_mwh,
            "prozessanlagen_kw": rt.prozessanlagen_kw,
            "prozessanlagen_mwh": rt.prozessanlagen_mwh,
            "beleuchtung_kw": rt.beleuchtung_kw,
            "beleuchtung_mwh": rt.beleuchtung_mwh,
            "lueftung_kw": rt.lueftung_kw,
            "lueftung_mwh": rt.lueftung_mwh,
            "kuehlung_kw": rt.kuehlung_kw,
            "kuehlung_mwh": rt.kuehlung_mwh,
            "heizung_kw": rt.heizung_kw,
            "heizung_mwh": rt.heizung_mwh,
            "warmwasser_mwh": rt.warmwasser_mwh,
            "fan_power_kw": vt.fan_power_kw,
            "fan_energy_mwh": vt.fan_energy_mwh,
            "luftkuehlung_kw": vt.luftkuehlung_kw,
            "luftkuehlung_mwh": vt.luftkuehlung_mwh,
            "lufterwaermung_kw": vt.lufterwaermung_kw,
            "lufterwaermung_mwh": vt.lufterwaermung_mwh,
            "kuehlung_endenergie_mwh": generation_energy.get("cooling", 0.0),
            "heizung_endenergie_mwh": generation_energy.get("heating", 0.0),
            "warmwasser_endenergie_mwh": generation_energy.get("ww", 0.0),
            "endenergie_total_mwh": result.resultate.energy["total"]["Total"],
        }

    @staticmethod
    def _assumptions(input_: BuildingInput, ahu_assumptions: list[str]) -> tuple[str, ...]:
        """The native-engine assumptions (dataset + model defaults)."""
        return (
            "Native backend: psychrometrics (FeuchteLuft_Formeln.bas), the AHU "
            "temperature-bin engine (Berechnung LU), the building aggregation "
            "(KZ_Raum_2024/Lüftung/Erzeugung/Resultate) and the Nutzungsgrad "
            "generation catalogue are the ported workbook model.",
            "The Klimakälte/Heizwärme KPI columns of the dataset carry the "
            f"{KPI_DEFAULT_CLIMATE_STATION} (Zürich-MeteoSchweiz) default of the "
            "Qhc_Klimastat reference; other climate stations use these values "
            "for the room Raumkühlung/Raumheizung intensities.",
            "The AHU fan full-load hours on an electricity basis (K69) default "
            "to the air-volume full-load hours (K68) — exact for einstufig "
            "regulation, an approximation for zweistufig/stufenlos.",
            "AhuInput IST-block parameters (temperature curves, coils, "
            "humidification, motor classes, fresh-air ratios) use the example "
            "system LA01 (Zürich-MeteoSchweiz) defaults documented in AhuInput.",
            "GenerationSystem.coverage applies to both the Leistungs- and the "
            "Energie-Deckungsgrad; GenerationSystem.losses is the standard "
            "Speicher-/Verteilverluste (no project overrides E/J).",
            "Allg. Gebäudetechnik (AG01–AG10) is 0 — the input model has no AG "
            "block; construction factor 10 % and Aufheizzeit 6 h/d are the "
            "aggregation defaults.",
        ) + tuple(ahu_assumptions)
