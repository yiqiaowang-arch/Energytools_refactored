"""energytools — SIA 2024 energy tools as a Python library.

Reimplements the two SIA 2024 workbooks (``2024_Raumdatenblätter_dfi_V221``
and ``2024_Gebaeude-Tool_dfi``) as a layered Python library. This root module
exposes the distribution version (:data:`__version__`) and the structured
version info (:func:`get_version`); the actual modules live in the
``energytools.common``, ``energytools.raumdaten``, ``energytools.gebaeude``,
``energytools.export``, ``energytools.api`` and ``energytools.mcp`` packages
(see the architecture documentation and ``docs/installation.md``).
"""

from __future__ import annotations

from pathlib import Path

from energytools.common.versioning import VersionInfo, VersionResolver

__version__ = "0.1.0"

__all__ = ["__version__", "get_version"]


def _data_dir() -> Path:
    """Return the repository ``data`` directory of a source checkout.

    When the library is installed as a wheel the directory does not exist and
    the version resolver simply reports empty dataset/model axes.
    """
    return Path(__file__).resolve().parents[2] / "data"


def get_version() -> VersionInfo:
    """Return the structured version info of the installed library.

    The library version plus the latest installed dataset and model releases
    and the latest installed climate version — a convenience wrapper around
    :meth:`VersionResolver.current`. Dataset and model releases are read from
    the ``data/datasets`` and ``data/models`` manifest directories of a
    source checkout; when nothing is installed, the corresponding axes are
    empty strings.

    Returns:
        A :class:`VersionInfo` (``dataset``, ``model``, ``implementation``,
        ``climate``).
    """
    resolver = VersionResolver.from_installed(
        dataset_dir=_data_dir() / "datasets",
        model_dir=_data_dir() / "models",
        implementation_version=__version__,
    )
    return resolver.current()
