"""Load editable default treatment seed data.

The runtime Treatment table is the source of truth after the first launch. This
module only controls what gets inserted into an empty or newly created database.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.config import get_appdata_dir, resource_path
from app.modules.treatments import rules


DEFAULT_TREATMENTS_FILENAME = "default_treatments.json"
DEFAULT_TREATMENTS_ENV = "DOSU_TREATMENT_DEFAULTS_PATH"


def bundled_default_treatments_path() -> Path:
    return resource_path(f"app/data/{DEFAULT_TREATMENTS_FILENAME}")


def user_default_treatments_path() -> Path:
    override = os.environ.get(DEFAULT_TREATMENTS_ENV)
    if override:
        return Path(override)
    return get_appdata_dir() / DEFAULT_TREATMENTS_FILENAME


def ensure_user_default_treatments_file() -> Path:
    path = user_default_treatments_path()
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    bundled = bundled_default_treatments_path()
    path.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def load_default_treatments() -> list[dict[str, Any]]:
    """Return validated seed rows from the user-editable JSON defaults file."""
    path = ensure_user_default_treatments_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return _normalize_rows(raw)
    except Exception:
        raw = json.loads(bundled_default_treatments_path().read_text(encoding="utf-8"))
        return _normalize_rows(raw)


def default_treatment_tuples() -> tuple[tuple[str, str, str, int, str, int, bool], ...]:
    """Backward-compatible tuple format for older imports/tests."""
    return tuple(
        (
            row["code"],
            row["name"],
            row["short"],
            row["default_minutes"],
            row["role"],
            row["count_increment"],
            row["show_in_patient"],
        )
        for row in load_default_treatments()
    )


def _normalize_rows(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("default treatments JSON must be a list")

    rows: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    seen_shorts: set[str] = set()
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("default treatment entries must be objects")

        code = _required_text(item, "code")
        short = _required_text(item, "short")
        if code in seen_codes:
            raise ValueError(f"duplicate treatment code: {code}")
        if short in seen_shorts:
            raise ValueError(f"duplicate treatment short: {short}")
        seen_codes.add(code)
        seen_shorts.add(short)

        role = str(item.get("role") or rules.ROLE_THERAPIST).strip()
        if role not in rules.ROLE_VALUES:
            raise ValueError(f"invalid treatment role: {role}")

        rows.append(
            {
                "code": code,
                "name": _required_text(item, "name"),
                "short": short,
                "default_minutes": max(5, _int(item.get("default_minutes"), 30)),
                "role": role,
                "count_increment": max(0, _int(item.get("count_increment"), 1)),
                "show_in_patient": bool(item.get("show_in_patient", False)),
                "active": bool(item.get("active", True)),
                "sort_order": _int(item.get("sort_order"), idx + 1) or (idx + 1),
            }
        )
    return rows


def _required_text(item: dict[str, Any], key: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise ValueError(f"default treatment '{key}' is required")
    return value


def _int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


__all__ = [
    "DEFAULT_TREATMENTS_ENV",
    "DEFAULT_TREATMENTS_FILENAME",
    "bundled_default_treatments_path",
    "user_default_treatments_path",
    "ensure_user_default_treatments_file",
    "load_default_treatments",
    "default_treatment_tuples",
]
