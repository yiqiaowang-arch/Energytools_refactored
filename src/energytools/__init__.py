"""energytools — SIA 2024 energy tools as a Python library.

This is the *packaging scaffold*: a minimal, installable and importable
placeholder distribution. The real modules (``energytools.common``,
``energytools.raumdaten``, ``energytools.gebaeude``, ``energytools.export``,
``energytools.api``, ``energytools.mcp``) land as the refactoring progresses;
see the architecture documentation and ``docs/installation.md``.
"""

__version__ = "0.1.0"

__all__ = ["__version__", "get_version"]


def get_version() -> str:
    """Return the library version (single source: :data:`__version__`)."""
    return __version__
