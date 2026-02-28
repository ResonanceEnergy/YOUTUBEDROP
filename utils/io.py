from __future__ import annotations

import os, json, uuid, re, shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

import yaml
from rich.console import Console

console = Console()


def env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def save_json(path: Path, data: dict) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\-_.]+", "-", text.strip()).strip("-").lower()
    return re.sub(r"-{2,}", "-", text)


def data_root() -> Path:
    return ensure_dir(Path(os.getenv("DATA_ROOT", "./data")))


def ncl_root() -> Path:
    return ensure_dir(Path(os.getenv("NCL_ROOT", "./ncl_out")))


def temp_root() -> Path:
    return ensure_dir(Path(os.getenv("TEMP_ROOT", "./.tmp")))


def video_dir(video_id: str) -> Path:
    return ensure_dir(data_root() / "videos" / video_id)


def artifacts_dir(video_id: str) -> Path:
    return ensure_dir(data_root() / "artifacts" / video_id)


def day_bucket() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def log_info(msg: str):
    console.log(f"[bold cyan]INFO[/]: {msg}")


def log_warn(msg: str):
    console.log(f"[bold yellow]WARN[/]: {msg}")


def log_err(msg: str):
    console.log(f"[bold red]ERROR[/]: {msg}")
