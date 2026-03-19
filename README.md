# 🔧 Smart File Collector (sfc)

Maintained and optimized for macOS by @polatsakarya35 | Based on the original engine by @Heysh1n.

A zero-dependency CLI/TUI tool that collects project source code into a single
structured text file — built specifically for feeding codebases into AI chats
(ChatGPT, Claude, Gemini).

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#)

---

## The Problem

Manually copying dozens of source files into an AI chat is painful:

- 📁 Project structure context is lost
- 🗑️ Junk files (`.git`, `node_modules`, `.env`) pollute the context
- ✂️ Character limits break long messages
- ⏱️ The whole process takes forever

## The Solution

```bash
python -m sfc
# → Interactive TUI opens
# → Select files with arrow keys + space
# → Press Enter → structured output + clipboard
```

One command. Smart filtering. Auto-split. Clipboard copy. Done.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Zero dependencies** | Pure Python 3.10+ stdlib. No pip install needed. |
| **Cross-platform** | Linux, macOS, Windows. Native TUI on all three. |
| **Interactive TUI** | Arrow-key navigation, checkboxes, scrollable lists via `curses`/`msvcrt`. |
| **Smart ignoring** | 80+ built-in ignore rules. Fully customisable in Settings. |
| **Auto-split** | Splits output into parts when exceeding character limits. |
| **Native clipboard** | `pbcopy` · `clip.exe` · `wl-copy` · `xclip` · `xsel` — no pyperclip. |
| **Presets** | Save & reuse file selections per project. |
| **Self-updater** | One-click update from GitHub inside the TUI. |
| **Persistent config** | Platform-aware path (`~/Library/Application Support/sfc` on macOS, XDG/APPDATA on others). |
| **Dynamic collect** | Uncheck files in the final review before generating output. |

---

## 🆕 What's New in v3.0.0 (macOS Edition)

- ✨ macOS Edition features developed by Polat Sakarya.
- **Native macOS config integration:** settings now default to
  `~/Library/Application Support/sfc/cfg.setting.json` on macOS, while
  preserving XDG fallback and existing Windows/Linux behavior.
- **Faster project scanning on APFS:** file traversal moved from `os.walk` to
  `os.scandir`-based recursion for lower overhead and improved scan speed on
  large trees.
- **More robust `pbcopy` for large outputs:** clipboard copy now uses a safer
  stdin streaming path on macOS, improving stability for 100K+ character
  payloads.
- **TUI rendering hardening on macOS terminals:** unicode width handling and
  resize redraw behavior were improved for cleaner rendering in Terminal.app and
  iTerm2.
- **Manual validation guide added:** reproducible macOS checks are documented in
  `docs/macos-manual-test.md` (config path, updater, large clipboard copy, TUI
  resize scenarios).
- **Maintenance credits:** macOS edition maintenance is led by Polat Sakarya,
  based on the original project engine by Heysh1n.

---

## 📦 Installation

### Quick (any OS)

```bash
# macOS (Optimized Edition)
git clone https://github.com/polatsakarya35/sfc-mac-edition.git

# Windows / Linux (Original Edition)
git clone https://github.com/Heysh1n/sfc.git

cd sfc
python /path/to/sfc
```

### Linux / macOS

```bash
# Run directly
python3 -m sfc

# Or build a portable single-file archive
python3 build.py
./dist/sfc.pyz

# Install globally
cp dist/sfc.pyz ~/.local/bin/sfc
chmod +x ~/.local/bin/sfc
sfc  # works from anywhere
```

**Clipboard (Linux only):**

```bash
# Wayland
sudo apt install wl-clipboard

# X11
sudo apt install xclip
```

### Windows

```powershell
python -m sfc

# Or build
python build.py
python dist\sfc.pyz
```

Clipboard works automatically via `clip.exe`.

---

## 🚀 Quick Start

### Interactive Mode (TUI)

```bash
python -m sfc
```

Opens a full-screen terminal interface:

```
  === Smart File Collector v3.0.0 ===
  [D] my-project  |  [F] 42 files
------------------------------------------------------------
 > [D]  Browse & Select
   [?]  Search by pattern
   [>]  Quick pick (paste paths)
   [=]  Collect ALL files
   [B]  Presets
   [T]  View tree
   [S]  Settings
   [H]  Help
   [U]  Check for updates
  ------------------------------
   [v]  Collect selected (0)
   [E]  Preview selected
   [X]  Clear selection
  ------------------------------
   [x]  Exit

  Up/Down:navigate  ENTER:select  q:quit
```

**Controls:**

| Key | Action |
|-----|--------|
| ↑ / ↓ | Navigate |
| SPACE | Toggle checkbox |
| ENTER | Select / confirm |
| ESC | Go back |
| q | Quit |

### CLI Mode (Scripting)

```bash
# Collect everything
sfc all -o context.txt

# Pick specific files or patterns
sfc pick src/main.py "src/config/*" "*.json"

# Show tree with sizes
sfc tree -s

# Find files
sfc find "*.service.ts"

# Read paths from file
sfc from paths.txt

# Manage presets
sfc preset save backend "src/models/*" "src/db/*"
sfc preset backend
sfc preset list
```

---

## 🎯 CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| *(none)* | Launch interactive TUI |
| `all` | Collect all project files |
| `pick [files...]` | Collect by path or glob pattern |
| `pick -` | Interactive multi-line path input |
| `tree` | Display project structure |
| `find <pattern>` | Find files matching a glob |
| `from <file>` | Read paths from a text file |
| `preset <action>` | Save / load / delete presets |

### Flags

| Flag | Description | Default |
|------|-------------|---------|
| `-p, --path` | Target root directory | `.` |
| `-o, --output` | Output filename | `collected_output.txt` |
| `-c, --chars` | Max chars per part | `90000` |
| `--no-tree` | Exclude tree from output | off |
| `-i, --ignore` | Extra dirs to ignore | `[]` |
| `-V, --version` | Print version | — |

---

## 🎮 TUI Screens

### Browse & Select

Select individual files with checkboxes:

| Key | Action |
|-----|--------|
| SPACE | Toggle file checkbox |
| / | Filter by substring |
| a | Select all visible |
| n | Deselect all visible |
| p | Select by glob pattern |
| c | Clear filter |
| ENTER | Done → back to menu |

### Collect Flow

Before generating output, a **review screen** lets you dynamically
uncheck files:

```
  [v] Collect — 5 files
  Uncheck items to exclude before collecting
------------------------------------------------------------
 [x]  src/main.py
 [x]  src/config/settings.py
 [ ]  src/tests/test_main.py        <-- excluded
 [x]  README.md
 [x]  pyproject.toml

  SPACE:toggle  ENTER:collect  ESC:cancel
```

### Settings

Persistent configuration with three ignore list editors:

- **Settings → Ignoring → Directories** — folder names to skip
- **Settings → Ignoring → Files** — exact filenames to skip
- **Settings → Ignoring → Extensions** — suffixes to skip
- **Reset to defaults** — restore built-in rules

Config saved at:

| OS | Path |
|----|------|
| Linux/macOS | `~/.config/sfc/cfg.setting.json` |
| Windows | `%APPDATA%\sfc\cfg.setting.json` |

---

## 📄 Output Format

```
══════════════
📋 my-project [pick]
📅 18.03.2026 14:39:48
📄 Files: 3
══════════════

┌────────────
│ 🗂️  STRUCTURE
├────────────
│ 📦 my-project/
│ ├── 📂 src/
│ │   ├── 📄 main.py
│ │   └── 📄 utils.py
│ └── 📄 README.md
└────────────

┌─── 📄 [1/3] src/main.py
def main():
    print("Hello AI!")
└────────────────────────────────────────

┌─── 📄 [2/3] src/utils.py
def helper():
    return 42
└────────────────────────────────────────

┌─── 📄 [3/3] README.md
# My Project
└────────────────────────────────────────

═════
✅ End
═════
```

**Auto-split:** When output exceeds the character limit (default 90K),
files are automatically split into `_p1.txt`, `_p2.txt`, etc.

---

## 🔖 Presets

Save file selections for repeated use:

```bash
# Save
sfc preset save api "src/routes/*" "src/middleware/*"

# Use
sfc preset api

# List
sfc preset list

# Delete
sfc preset delete api
```

Stored per-project in `.sfc-presets.json`.

---

## 🔄 Self-Updater

In TUI: **Main Menu → Check for updates**

- Checks `raw.githubusercontent.com` for newer version
- Downloads and overwrites module files atomically
- Prompts to restart
- No sudo required (unless installed in system dirs)

---

## 💡 Tips for AI Workflows

1. **Don't send everything.** Fixing a DB bug?
   ```bash
   sfc pick "src/db/*" "src/models/*"
   ```

2. **Use character limits.** Large project?
   ```bash
   sfc all -c 50000
   ```
   Feed parts sequentially: *"Here's part 1/3..."*

3. **Quick Pick from AI output.** AI says "check these files"?
   Copy the list → TUI → Quick Pick → paste → collect.

4. **Combine with git:**
   ```bash
   git diff --name-only > changed.txt
   sfc from changed.txt
   ```

5. **Save frequent selections:**
   ```bash
   sfc preset save backend "src/models/*" "src/services/*"
   ```

---

## 🏗️ Architecture

```
sfc/
├── __init__.py          # Package marker
├── __main__.py          # Entry point
├── version.py           # Version constant
├── patterns.py          # Default ignores, glob helpers
├── config.py            # Persistent JSON config
├── collector.py         # File scanner, tree, output
├── clipboard.py         # Native clipboard integration
├── updater.py           # Self-update from GitHub
├── app.py               # CLI + TUI controller
└── tui/
    ├── __init__.py      # Platform detection
    ├── base.py          # Key enum, abstract engine
    ├── curses_tui.py    # Linux/macOS engine
    └── win_tui.py       # Windows engine
```

**Zero** external dependencies. **Zero** circular imports.

---

## 📋 Requirements

- Python 3.10+
- Terminal with at least 80×24 (for TUI)
- **Linux clipboard:** `xclip`, `xsel`, or `wl-copy`
- **macOS clipboard:** built-in (`pbcopy`)
- **Windows clipboard:** built-in (`clip.exe`)

---

## 🔨 Building

```bash
# Build portable .pyz archive
python build.py

# Output: dist/sfc.pyz
# Run:    ./dist/sfc.pyz  or  python dist/sfc.pyz

# Clean build artifacts
python build.py clean
```

---

## 📜 License

MIT License — © 2026 Heysh1n & Contributors
