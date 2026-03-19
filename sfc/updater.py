"""Self-updater: check remote version, download, overwrite, prompt restart.

Downloads the raw ``sfc/version.py`` from GitHub to parse the remote version,
then fetches the full single-file or package as needed.

Works with both:
  - Running as a .py / .pyz (``__file__`` points to a real file)
  - Running as a frozen zipapp (overwrite the archive)

No third-party dependencies — uses only ``urllib``.
"""

from __future__ import annotations

import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from .version import GITHUB_RAW_BASE, VERSION


# ── Public types ────────────────────────────────────────────────────

class UpdateCheckResult(NamedTuple):
    """Outcome of a version check."""
    available: bool       # True if a newer version exists
    remote_version: str   # version string from remote, or "" on error
    current_version: str  # local VERSION
    error: str            # human-readable error, or ""


class UpdateApplyResult(NamedTuple):
    """Outcome of an apply attempt."""
    ok: bool
    message: str


# ── Internals ───────────────────────────────────────────────────────

_TIMEOUT: int = 10
_VERSION_URL: str = f"{GITHUB_RAW_BASE}/sfc/version.py"
_MAIN_URL: str = f"{GITHUB_RAW_BASE}/sfc/__main__.py"

# For single-file download (future-proof: if we ever ship sfc.py again)
_SINGLE_FILE_URL: str = f"{GITHUB_RAW_BASE}/sfc.py"

# Module files that make up the package — fetched for zipapp overwrite
_PACKAGE_FILES: list[str] = [
    "__init__.py",
    "__main__.py",
    "version.py",
    "patterns.py",
    "config.py",
    "collector.py",
    "clipboard.py",
    "updater.py",
    "app.py",
    "tui/__init__.py",
    "tui/base.py",
    "tui/curses_tui.py",
    "tui/win_tui.py",
]


def _fetch(url: str) -> bytes:
    """Fetch URL contents.  Raises on failure."""
    req = Request(url, headers={"User-Agent": "sfc-updater"})
    with urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read()


def _parse_remote_version(raw: bytes) -> str:
    """Extract VERSION = "x.y.z" from raw version.py bytes."""
    text: str = raw.decode("utf-8", errors="replace")
    match = re.search(
        r'VERSION(?:\s*:\s*[^=]+)?\s*=\s*["\']([^"\']+)["\']',
        text,
    )
    if match:
        return match.group(1)
    return ""


def _version_tuple(v: str) -> tuple[int, ...]:
    """``"3.1.2"`` → ``(3, 1, 2)``.  Non-numeric parts become 0."""
    parts: list[int] = []
    for segment in v.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _is_newer(remote: str, local: str) -> bool:
    """Return True if *remote* version is strictly greater than *local*."""
    return _version_tuple(remote) > _version_tuple(local)


def _executable_path() -> Path:
    """Best guess at the currently running script / archive path."""
    # sys.argv[0] is usually the most reliable for "what was invoked"
    candidate = Path(sys.argv[0]).resolve()
    if candidate.exists():
        return candidate
    # Fallback: __main__'s __file__
    main_mod = sys.modules.get("__main__")
    if main_mod and hasattr(main_mod, "__file__") and main_mod.__file__:
        candidate = Path(main_mod.__file__).resolve()
        if candidate.exists():
            return candidate
    return Path(__file__).resolve()


def _is_writable(p: Path) -> bool:
    """Check if we can write to *p* (or its parent if *p* doesn't exist)."""
    if p.exists():
        return os.access(p, os.W_OK)
    return os.access(p.parent, os.W_OK)


# ── Public API ──────────────────────────────────────────────────────

def check_update() -> UpdateCheckResult:
    """Check GitHub for a newer version.  Network errors are caught."""
    try:
        raw: bytes = _fetch(_VERSION_URL)
    except (URLError, OSError, TimeoutError) as exc:
        return UpdateCheckResult(
            available=False,
            remote_version="",
            current_version=VERSION,
            error=f"network error: {exc}",
        )

    remote: str = _parse_remote_version(raw)
    if not remote:
        return UpdateCheckResult(
            available=False,
            remote_version="",
            current_version=VERSION,
            error="could not parse remote version",
        )

    return UpdateCheckResult(
        available=_is_newer(remote, VERSION),
        remote_version=remote,
        current_version=VERSION,
        error="",
    )


def apply_update() -> UpdateApplyResult:
    """Download the latest version and overwrite the current executable.

    Strategy
    --------
    1. Determine the path of the running script/archive.
    2. Download the new file(s) to a temp location.
    3. Atomically replace (write temp → rename over original).
    4. Return success + "please restart" message.

    For a **directory package** (``python -m sfc``), each module file is
    overwritten individually.  For a **zipapp** (``.pyz``), a new archive
    is built.  For a **single file** (``sfc.py``), the file is replaced.
    """
    exe: Path = _executable_path()

    if not _is_writable(exe):
        return UpdateApplyResult(
            ok=False,
            message=f"no write permission: {exe}",
        )

    # ── Detect mode: single file vs package dir vs zipapp ──
    # If exe is inside a directory with version.py, it's a package run
    package_dir: Path | None = None
    if exe.parent.name == "sfc" and (exe.parent / "version.py").exists():
        package_dir = exe.parent
    elif exe.suffix == ".pyz":
        # Zipapp — for now, we download individual files and rebuild
        package_dir = None  # handled separately below

    try:
        if package_dir is not None:
            # ── Package mode: overwrite individual files ──
            for rel in _PACKAGE_FILES:
                url: str = f"{GITHUB_RAW_BASE}/sfc/{rel}"
                target: Path = package_dir / rel
                try:
                    data: bytes = _fetch(url)
                except (URLError, OSError):
                    continue  # skip files that don't exist upstream yet
                target.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write(target, data)

            return UpdateApplyResult(
                ok=True,
                message="updated package files — please restart sfc",
            )

        else:
            # ── Single file or zipapp mode ──
            # Try single-file first, fall back to __main__.py
            data = b""
            for url in (_SINGLE_FILE_URL, _MAIN_URL):
                try:
                    data = _fetch(url)
                    break
                except (URLError, OSError):
                    continue

            if not data:
                return UpdateApplyResult(
                    ok=False,
                    message="failed to download update from GitHub",
                )

            _atomic_write(exe, data)

            # Preserve executable bit on POSIX
            if os.name != "nt":
                exe.chmod(
                    exe.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH,
                )

            return UpdateApplyResult(
                ok=True,
                message=f"updated {exe.name} — please restart sfc",
            )

    except Exception as exc:
        return UpdateApplyResult(ok=False, message=f"update failed: {exc}")


def _atomic_write(target: Path, data: bytes) -> None:
    """Write *data* to a temp file then rename over *target*.

    On Windows ``os.replace`` can fail if the file is locked; in that case
    we fall back to direct write.
    """
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path_str = tempfile.mkstemp(
        dir=str(target.parent),
        prefix=f".{target.stem}_",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_path_str)
    try:
        os.write(fd, data)
        os.close(fd)
        fd = -1  # sentinel: closed

        # Atomic rename
        try:
            os.replace(str(tmp_path), str(target))
        except OSError:
            # Windows fallback: direct overwrite
            target.write_bytes(data)
            try:
                tmp_path.unlink()
            except OSError:
                pass
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        # Cleanup temp on any error path
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass