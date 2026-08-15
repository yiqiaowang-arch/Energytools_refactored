"""Tests for the energytools.common.errors exception hierarchy.

Every documented exception is verified: message format, structured
``details`` payload and the flat inheritance contract (catch the precise type
or the base ``EnergyToolsError``).
"""

from __future__ import annotations

import pytest

from energytools.common import errors
from energytools.common.errors import (
    BackendError,
    CalculationError,
    CalculationInputError,
    DatasetNotFoundError,
    DatasetValidationError,
    EnergyToolsError,
    ExcelBackendError,
    ExportError,
    ModelVersionMismatchError,
    PsychrometricError,
    UnitError,
    UnknownClimateStationError,
    UnknownLanguageError,
    UnknownParameterError,
    UnknownRoomUseError,
    UnknownValueKindError,
)

ALL_EXCEPTIONS = [
    EnergyToolsError,
    DatasetNotFoundError,
    DatasetValidationError,
    UnknownRoomUseError,
    UnknownParameterError,
    UnknownClimateStationError,
    UnknownLanguageError,
    UnknownValueKindError,
    CalculationInputError,
    CalculationError,
    ModelVersionMismatchError,
    BackendError,
    ExcelBackendError,
    ExportError,
    UnitError,
    PsychrometricError,
]


def test_all_documented_exceptions_are_public() -> None:
    for exc in ALL_EXCEPTIONS:
        assert getattr(errors, exc.__name__) is exc
    assert set(errors.__all__) == {exc.__name__ for exc in ALL_EXCEPTIONS}


def test_energy_tools_error_message_and_details() -> None:
    exc = EnergyToolsError("boom", {"symbol": "X1"})
    assert str(exc) == "boom"
    assert exc.message == "boom"
    assert exc.details == {"symbol": "X1"}


def test_energy_tools_error_details_defaults_to_none() -> None:
    assert EnergyToolsError("boom").details is None


def test_hierarchy_flat_by_design() -> None:
    # Every subclass derives from EnergyToolsError.
    for exc in ALL_EXCEPTIONS:
        assert issubclass(exc, EnergyToolsError)
        assert issubclass(exc, Exception)
    # ExcelBackendError is the only documented intermediate subclass.
    assert issubclass(ExcelBackendError, BackendError)
    assert BackendError.__mro__[1] is EnergyToolsError


@pytest.mark.parametrize(
    ("exception_type", "args", "expected_message"),
    [
        (DatasetNotFoundError, ("V199",), "Dataset release 'V199' not found"),
        (DatasetValidationError, ("release V221 invalid",), "release V221 invalid"),
        (
            UnknownRoomUseError,
            (99, "V221"),
            "Room use '99' not found in release 'V221'",
        ),
        (
            UnknownRoomUseError,
            ("1.01", "V221"),
            "Room use '1.01' not found in release 'V221'",
        ),
        (
            UnknownParameterError,
            ("9.9.9", "V221"),
            "Parameter '9.9.9' not found in release 'V221'",
        ),
        (
            UnknownClimateStationError,
            (41, "V221"),
            "Climate station '41' not found in release 'V221'",
        ),
        (
            UnknownClimateStationError,
            ("7", "V221"),
            "Climate station '7' not found in release 'V221'",
        ),
        (
            UnknownLanguageError,
            ("en",),
            "Unknown language 'en' (expected de, fr or it)",
        ),
        (
            UnknownValueKindError,
            ("optimal",),
            "Unknown value kind 'optimal' (expected standard, zielwert or bestand)",
        ),
        (CalculationInputError, ("negative area",), "negative area"),
        (CalculationError, ("numeric failure",), "numeric failure"),
        (ModelVersionMismatchError, ("incompatible versions",), "incompatible versions"),
        (BackendError, ("backend failed",), "backend failed"),
        (ExcelBackendError, ("COM denied",), "COM denied"),
        (ExportError, ("unsupported format",), "unsupported format"),
        (UnitError, ("cannot convert",), "cannot convert"),
        (PsychrometricError, ("rh > 100",), "rh > 100"),
    ],
)
def test_exception_messages(
    exception_type: type[EnergyToolsError], args: tuple[object, ...], expected_message: str
) -> None:
    exc = exception_type(*args)
    assert str(exc) == expected_message
    assert exc.details is None


def test_exceptions_carry_structured_details() -> None:
    exc = DatasetValidationError("release V221 invalid", {"errors": ["Qhc row 5: missing value"]})
    assert exc.details == {"errors": ["Qhc row 5: missing value"]}

    exc = CalculationError("step failed", {"step": "ahu:LA03", "system": "LA01"})
    assert exc.details == {"step": "ahu:LA03", "system": "LA01"}

    exc = UnitError("cannot convert", {"from": "kWh", "to": "m2"})
    assert exc.details == {"from": "kWh", "to": "m2"}

    exc = ModelVersionMismatchError(
        "model 1.0.0 does not support dataset V222",
        {"dataset": "V222", "model": "1.0.0", "climate": "meteoschweiz-2024"},
    )
    assert exc.details == {"dataset": "V222", "model": "1.0.0", "climate": "meteoschweiz-2024"}


def test_catch_base_type() -> None:
    with pytest.raises(EnergyToolsError) as exc_info:
        raise DatasetNotFoundError("V199")
    assert exc_info.value.details is None


def test_catch_backend_base_type() -> None:
    with pytest.raises(BackendError) as exc_info:
        raise ExcelBackendError("workbook copy missing", {"workbook": "out/V221.xlsm"})
    assert exc_info.value.details == {"workbook": "out/V221.xlsm"}
