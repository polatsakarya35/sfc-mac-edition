"""Cross-platform clipboard copy using only OS-native tools.

Supported backends (tried in order):
  Windows  → clip.exe
  macOS    → pbcopy
  Linux    → wl-copy (Wayland), xclip (X11), xsel (X11 fallback)

No third-party dependencies.  No sudo required.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import NamedTuple

_DEFAULT_TIMEOUT_SEC: int = 5
_MACOS_TIMEOUT_SEC: int = 20


class ClipboardResult(NamedTuple):
    """Outcome of a clipboard copy attempt."""
    ok: bool
    backend: str  # tool name that succeeded, or "" on failure
    error: str    # human-readable error, or "" on success


def _is_wayland() -> bool:
    """Detect active Wayland session."""
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def _is_x11() -> bool:
    """Detect active X11 session."""
    return bool(os.environ.get("DISPLAY"))


def _run(cmd: list[str], data: bytes, timeout_sec: int = _DEFAULT_TIMEOUT_SEC) -> bool:
    """Run *cmd*, pipe *data* to stdin, return success bool."""
    try:
        proc = subprocess.run(
            cmd,
            input=data,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_sec,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _try_tool(
    tool: str,
    args: list[str],
    data: bytes,
    timeout_sec: int = _DEFAULT_TIMEOUT_SEC,
) -> bool:
    """Check if *tool* exists on PATH, then run with *args*."""
    if shutil.which(tool) is None:
        return False
    return _run([tool] + args, data, timeout_sec=timeout_sec)


def _run_pbcopy_stream(data: bytes) -> str | None:
    """macOS pbcopy via stdin pipe; returns error text, or None on success."""
    if shutil.which("pbcopy") is None:
        return "pbcopy not found"
    try:
        proc = subprocess.Popen(  # noqa: S603 - constant executable name
            ["pbcopy"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        return f"pbcopy start failed: {exc}"

    try:
        _, stderr = proc.communicate(input=data, timeout=_MACOS_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        return "pbcopy timeout"
    except OSError as exc:
        proc.kill()
        return f"pbcopy io error: {exc}"

    if proc.returncode == 0:
        return None

    err_text = stderr.decode("utf-8", errors="replace").strip()
    return err_text or "pbcopy failed"


def copy_to_clipboard(text: str) -> ClipboardResult:
    """Copy *text* to the system clipboard.

    Returns a :class:`ClipboardResult` indicating success/failure and which
    backend was used.
    """
    if not text:
        return ClipboardResult(ok=False, backend="", error="empty text")

    # ── Windows ─────────────────────────────────────────────────
    if sys.platform == "win32":
        # clip.exe expects UTF-16 LE on stdin for full Unicode support
        data = text.encode("utf-16-le")
        # Fallback: utf-8 if utf-16 fails (very old Windows)
        if _try_tool("clip", [], data):
            return ClipboardResult(ok=True, backend="clip.exe", error="")
        # Try utf-8 as last resort
        if _try_tool("clip", [], text.encode("utf-8")):
            return ClipboardResult(ok=True, backend="clip.exe", error="")
        return ClipboardResult(
            ok=False, backend="", error="clip.exe failed or not found",
        )

    data_utf8: bytes = text.encode("utf-8")

    # ── macOS ───────────────────────────────────────────────────
    if sys.platform == "darwin":
        pb_err = _run_pbcopy_stream(data_utf8)
        if pb_err is None:
            return ClipboardResult(ok=True, backend="pbcopy", error="")
        return ClipboardResult(ok=False, backend="", error=pb_err)

    # ── Linux / BSD ─────────────────────────────────────────────

    # 1) Wayland
    if _is_wayland():
        if _try_tool("wl-copy", [], data_utf8):
            return ClipboardResult(ok=True, backend="wl-copy", error="")
        # Wayland session but wl-copy missing — try X11 tools via XWayland
        if _is_x11():
            if _try_tool("xclip", ["-selection", "clipboard"], data_utf8):
                return ClipboardResult(ok=True, backend="xclip", error="")
            if _try_tool("xsel", ["--clipboard", "--input"], data_utf8):
                return ClipboardResult(ok=True, backend="xsel", error="")
        return ClipboardResult(
            ok=False, backend="",
            error="Wayland: wl-copy not found; install wl-clipboard",
        )

    # 2) X11
    if _is_x11():
        if _try_tool("xclip", ["-selection", "clipboard"], data_utf8):
            return ClipboardResult(ok=True, backend="xclip", error="")
        if _try_tool("xsel", ["--clipboard", "--input"], data_utf8):
            return ClipboardResult(ok=True, backend="xsel", error="")
        return ClipboardResult(
            ok=False, backend="",
            error="X11: install xclip or xsel",
        )

    # 3) No display server (SSH, TTY, container)
    return ClipboardResult(
        ok=False, backend="",
        error="no display server detected (no WAYLAND_DISPLAY or DISPLAY)",
    )


def available_backend() -> str | None:
    """Return the name of the first usable clipboard tool, or *None*.

    Useful for showing status in the TUI without actually copying anything.
    """
    if sys.platform == "win32":
        return "clip.exe" if shutil.which("clip") else None
    if sys.platform == "darwin":
        return "pbcopy" if shutil.which("pbcopy") else None

    if _is_wayland() and shutil.which("wl-copy"):
        return "wl-copy"
    if _is_x11():
        if shutil.which("xclip"):
            return "xclip"
        if shutil.which("xsel"):
            return "xsel"
    return None