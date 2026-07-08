"""Output helpers for reproducible LunaLink evidence bundles."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pandas as pd


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output = Path(path)
    ensure_directory(output.parent)
    output.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")
    return output


def write_dataframe(path: str | Path, dataframe: pd.DataFrame) -> Path:
    output = Path(path)
    ensure_directory(output.parent)
    dataframe.to_csv(output, index=False)
    return output

