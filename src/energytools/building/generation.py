"""Generation — one generator (Erzeugung) attached to a building or a room."""

from __future__ import annotations


class Generation:
    """One generator of the ``Nutzungsgrad`` catalogue.

    Args:
        catalog_code: Catalogue code (``"WE02"`` gas boiler, ``"W13"``
            electric hot water, ``"KE06"`` compression chiller, ...).
        coverage: Deckungsgrad 0-1 — the share of the demand this
            generator covers (the rest falls to the other generators of
            the same kind).
        losses: Speicher-/Verteilverluste 0-1 (added to the demand before
            the efficiency is applied).
        kind: ``"heating" | "cooling" | "ww"`` — optional, resolved from
            the catalogue when ``None``.
    """

    def __init__(
        self,
        catalog_code: str,
        coverage: float = 1.0,
        losses: float = 0.0,
        kind: str | None = None,
    ) -> None:
        if not 0.0 <= coverage <= 1.0:
            raise ValueError(f"Deckungsgrad {coverage} outside 0-1")
        if not 0.0 <= losses <= 1.0:
            raise ValueError(f"Speicher-/Verteilverluste {losses} outside 0-1")
        self.catalog_code = catalog_code
        self.coverage = coverage
        self.losses = losses
        self.kind = kind

    def __repr__(self) -> str:
        return f"Generation({self.catalog_code}, coverage={self.coverage}, losses={self.losses})"
