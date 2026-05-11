from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    for path in (root, src):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
