"""Raw-document storage abstraction."""

from __future__ import annotations

from pathlib import Path
import shutil


class LocalObjectStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, source: Path, *, key: str) -> Path:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        return target
