"""Persistence of calculation results (doc part 04 §4.4, ``CalculationStore``).

In-memory when ``directory`` is ``None``, otherwise every result is also
written as one JSON file (``<result_id>.json``) so a fresh process can reload
results — the backing store of ``GET /calculations/{result_id}``.
"""

from __future__ import annotations

import json
from pathlib import Path

from energytools.engine.errors import CalculationError
from energytools.engine.result import Results

__all__ = ["CalculationStore"]


class CalculationStore:
    """Persistence of calculation results by ``result_id``.

    Args:
        directory: Optional directory for on-disk persistence; ``None`` =
            in-memory only.
    """

    def __init__(self, directory: str | None = None) -> None:
        self.directory = directory
        self._memory: dict[str, Results] = {}
        if directory is not None:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def save(self, result: Results) -> None:
        """Store a result (memory, and a JSON file when a directory is set).

        Raises:
            OSError: on write failure.
            ValueError: for unsafe result ids in directory mode.
        """
        if self.directory is not None:
            if not result.result_id or Path(result.result_id).name != result.result_id:
                raise ValueError(f"unsafe result_id {result.result_id!r} for file storage")
            target = Path(self.directory) / f"{result.result_id}.json"
            target.write_text(json.dumps(result.as_dict(), ensure_ascii=True), encoding="utf-8")
        self._memory[result.result_id] = result

    def get(self, result_id: str) -> Results:
        """The stored result.

        Falls back to the on-disk JSON file when the id is not in memory.

        Raises:
            CalculationError: unknown id (or corrupt stored file).
        """
        result = self._memory.get(result_id)
        if result is not None:
            return result
        if self.directory is not None:
            path = Path(self.directory) / f"{result_id}.json"
            if path.is_file():
                try:
                    return Results.from_dict(json.loads(path.read_text(encoding="utf-8")))
                except (ValueError, KeyError, TypeError) as exc:
                    raise CalculationError(
                        f"stored result {result_id!r} is corrupt", {"result_id": result_id}
                    ) from exc
        raise CalculationError(f"unknown result id {result_id!r}", {"result_id": result_id})

    def list(self, limit: int = 100) -> list[str]:
        """Newest-first result ids (at most ``limit``).

        When running with a directory, ids persisted by this process come
        from memory; otherwise the directory's files (by modification time).
        """
        if self._memory:
            ids = list(reversed(self._memory))
        elif self.directory is not None:
            files = sorted(
                Path(self.directory).glob("*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            ids = [path.stem for path in files]
        else:
            ids = []
        return ids[:limit]
