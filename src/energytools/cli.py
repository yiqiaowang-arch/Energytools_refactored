"""Minimal placeholder CLI for the energytools scaffold.

The real CLI (subcommands ``versions``, ``export``, ``serve``, ``mcp``)
arrives with the full implementation; for now this entry point exists so
that every installation method (pip / uv / pixi / conda) has a console
script to smoke-test: ``energytools --version``.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from energytools import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="energytools",
        description="SIA 2024 energy tools (Raumdatenblaetter, Gebaeude-Tool) as a Python library.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (console script ``energytools``)."""
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
