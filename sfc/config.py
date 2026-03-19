"""Persistent configuration (platform-aware) and per-project presets."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields as dc_fields
from pathlib import Path
from typing import Any

from .version import APP_NAME
from .patterns import (
    DEFAULT_IGNORE_DIRS,
    DEFAULT_IGNORE_FILES,
    DEFAULT_IGNORE_EXTENSIONS,
)


# ── Platform config directory ───────────────────────────────────────

def _config_dir() -> Path:
    """Platform-aware config directory with safe fallbacks."""
    if os.name == "nt":
        base: str = os.environ.get("APPDATA", "")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    xdg: str = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg:
        return Path(xdg) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".config" / APP_NAME


def config_path() -> Path:
    """Full path to the global settings file."""
    return _config_dir() / "cfg.setting.json"


# ── AppConfig dataclass ─────────────────────────────────────────────

@dataclass
class AppConfig:
    """All user-facing settings.  Serialised as JSON."""

    output: str = "collected_output.txt"
    max_chars: int = 90_000
    show_tree: bool = True
    auto_copy: bool = False
    page_size: int = 20
    ignore_dirs: list[str] = field(
        default_factory=lambda: sorted(DEFAULT_IGNORE_DIRS),
    )
    ignore_files: list[str] = field(
        default_factory=lambda: sorted(DEFAULT_IGNORE_FILES),
    )
    ignore_extensions: list[str] = field(
        default_factory=lambda: sorted(DEFAULT_IGNORE_EXTENSIONS),
    )

    # ── post-init validation ──

    def __post_init__(self) -> None:
        if not isinstance(self.ignore_dirs, list):
            self.ignore_dirs = sorted(DEFAULT_IGNORE_DIRS)
        if not isinstance(self.ignore_files, list):
            self.ignore_files = sorted(DEFAULT_IGNORE_FILES)
        if not isinstance(self.ignore_extensions, list):
            self.ignore_extensions = sorted(DEFAULT_IGNORE_EXTENSIONS)
        try:
            self.max_chars = max(1_000, int(self.max_chars))
        except (TypeError, ValueError):
            self.max_chars = 90_000
        try:
            self.page_size = max(5, min(100, int(self.page_size)))
        except (TypeError, ValueError):
            self.page_size = 20

    # ── convenience accessors ──

    def ignore_dirs_set(self) -> set[str]:
        return set(self.ignore_dirs)

    def ignore_files_set(self) -> set[str]:
        return set(self.ignore_files)

    def ignore_ext_set(self) -> set[str]:
        return set(self.ignore_extensions)

    def reset_ignores(self) -> None:
        """Restore all three ignore lists to built-in defaults."""
        self.ignore_dirs = sorted(DEFAULT_IGNORE_DIRS)
        self.ignore_files = sorted(DEFAULT_IGNORE_FILES)
        self.ignore_extensions = sorted(DEFAULT_IGNORE_EXTENSIONS)


# ── Global config persistence ───────────────────────────────────────

def load_config() -> AppConfig:
    """Load from disk or create defaults (auto-saves on first run)."""
    fp: Path = config_path()
    if not fp.exists():
        cfg = AppConfig()
        save_config(cfg)
        return cfg
    try:
        raw: dict[str, Any] = json.loads(fp.read_text("utf-8"))
        valid_keys: set[str] = {f.name for f in dc_fields(AppConfig)}
        kw: dict[str, Any] = {k: v for k, v in raw.items() if k in valid_keys}
        return AppConfig(**kw)
    except Exception:
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    """Write current config to disk (creates parent dirs)."""
    fp: Path = config_path()
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(
        json.dumps(asdict(cfg), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ── Per-project presets ─────────────────────────────────────────────

_PRESETS_FILE: str = ".sfc-presets.json"


def presets_file(root: Path) -> Path:
    """Return preset file path for a given project root."""
    return root / _PRESETS_FILE


def load_presets(root: Path) -> dict[str, list[str]]:
    fp: Path = presets_file(root)
    if not fp.exists():
        return {}
    try:
        data: Any = json.loads(fp.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_presets(data: dict[str, list[str]], root: Path) -> None:
    fp: Path = presets_file(root)
    fp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )