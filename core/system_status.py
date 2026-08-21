from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from core.data import DATA_FILE, MAX_AUTOMATIC_BACKUPS, data


PERSISTENT_DISK_BYTES = 1024 ** 3
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _bytes(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _group_sizes(source):
    groups = {"Habitory": 0, "未来決算": 0, "店舗管理": 0, "スケジュール": 0, "その他": 0}
    for key, value in source.items():
        size = _bytes({key: value})
        lowered = key.lower()
        if key in {"users", "workout"} or any(word in lowered for word in ("habit", "nutrition", "reading", "hydration")):
            groups["Habitory"] += size
        elif any(word in lowered for word in ("schedule", "calendar", "event")):
            groups["スケジュール"] += size
        elif any(word in lowered for word in ("store", "shift", "inventory", "handover", "checklist")):
            groups["店舗管理"] += size
        elif any(word in lowered for word in ("business", "financial", "sales", "purchase", "staffing", "annual")):
            groups["未来決算"] += size
        else:
            groups["その他"] += size
    return groups


def _write_test(directory: Path):
    try:
        directory.mkdir(parents=True, exist_ok=True)
        descriptor, filename = tempfile.mkstemp(prefix=".rbase-health-", dir=directory)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write("ok")
            handle.flush()
            os.fsync(handle.fileno())
        Path(filename).unlink(missing_ok=True)
        return True, "保存先へ正常に書き込めます"
    except OSError as error:
        return False, f"保存テストに失敗しました: {error}"


def _application_size():
    total = 0
    for target in (PROJECT_ROOT / "core", PROJECT_ROOT / "pages", PROJECT_ROOT / "static"):
        if not target.exists():
            continue
        total += sum(path.stat().st_size for path in target.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    for name in ("main.py", "requirements.txt"):
        path = PROJECT_ROOT / name
        if path.exists():
            total += path.stat().st_size
    return total


def get_system_status():
    path = Path(DATA_FILE)
    directory = path.parent
    backups = sorted(directory.glob(f"{path.name}.backup.*"), key=lambda item: item.stat().st_mtime, reverse=True)
    file_size = path.stat().st_size if path.exists() else 0
    backup_size = sum(item.stat().st_size for item in backups)
    used = file_size + backup_size
    capacity = PERSISTENT_DISK_BYTES
    percent = used / capacity * 100 if capacity else 0
    writable, write_message = _write_test(directory)
    latest = backups[0] if backups else None
    return {
        "path": str(path),
        "file_size": file_size,
        "backup_size": backup_size,
        "used": used,
        "capacity": capacity,
        "percent": percent,
        "writable": writable,
        "write_message": write_message,
        "backup_count": len(backups),
        "backup_limit": MAX_AUTOMATIC_BACKUPS,
        "latest_backup": datetime.fromtimestamp(latest.stat().st_mtime) if latest else None,
        "last_saved": datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else None,
        "groups": _group_sizes(data.data),
        "application_size": _application_size(),
    }
