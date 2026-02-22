<p align="center">
  <img src="assets/logo.png" alt="Meridian" width="80">
</p>

# Contributing to Meridian

> **Do not** submit code, assets, or links that reference pirated content or ROM download sites. Violations result in an immediate ban. Emulation is legal — piracy is not.

## Getting Started

1. Fork the repository and clone your fork:

```bash
git clone https://github.com/<your-username>/Meridian.git
cd Meridian
```

2. Double-click **`run.bat`**. It automatically checks your Python version, installs all dependencies from `requirements.txt`, and starts the app. No manual `pip install` needed.

   If you prefer to manage dependencies yourself:

```bash
pip install -r requirements.txt
python main.py
```

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases. Do not target PRs here. |
| `dev`  | Active development. **All PRs go here.** |

Always branch from `dev` and open your PR against `dev`.

## Project Layout

```
Meridian/
├── main.py                     # Entry point, crash logger, debug logging
├── run.bat                     # Windows launcher
├── meridian/
│   ├── app.py                  # QApplication setup, surface/font config
│   ├── core/
│   │   ├── config.py           # Config dataclass, system/emulator catalogs
│   │   ├── emulator_install.py # Download & extract pipeline
│   │   ├── emulator_setup.py   # First-run setup + launch hooks per emulator
│   │   ├── input_manager.py    # SDL2 gamepad polling via pygame
│   │   ├── audio_manager.py    # Audio device management
│   │   └── ambient_audio.py    # Background audio engine (numpy)
│   └── ui/
│       ├── main_window.py      # Main window, ROM browser, game context menus
│       ├── menu_bar.py         # Full menu bar (File/Edit/View/Tools/…)
│       ├── settings_dialog.py  # Multi-tab settings dialog
│       ├── style.py            # Stylesheet, theme, density helpers
│       ├── background.py       # QML animated background
│       ├── icons.py            # Lucide SVG icon helpers
│       └── dialogs.py          # Shared dialog utilities
├── emulators/
│   └── extensions/
│       ├── cemu/               # Cemu controller profile sync
│       └── eden/               # Eden controller profile sync
├── assets/                     # Fonts, logos, QML shaders, sounds
└── cache/                      # Runtime cache (box art, logs) — gitignored
```

## Submitting Changes

1. **Branch** from `dev` with a descriptive name (`fix/crash-on-scan`, `feature/scraper-retry`).
2. Make focused, atomic commits with clear messages.
3. Run the application and verify your changes work.
4. If you touched an emulator extension, run its tests:

```bash
python -m pytest emulators/extensions/<emu_id>/tests/ -v
```

5. Open a PR against `dev` with:
   - A summary of what changed and why.
   - Links to related issues.
   - Screenshots or short recordings for UI changes.

## Reporting Bugs

[Open an issue](https://github.com/UglyDuckling251/Meridian/issues/new) with:

- Steps to reproduce.
- Expected vs. actual behaviour.
- OS version and Python version.
- Crash log from `cache/latest.log` or debug log from `cache/meridian_debug.log` if available.

## Emulator Extensions

Meridian auto-discovers emulator-specific logic from `emulators/extensions/<emu_id>/`. If you want to add support for a new emulator's controller profile format:

1. Create `emulators/extensions/<emu_id>/` with an `__init__.py`.
2. Implement a `configure_input(player_settings, exe_path, game_path)` function.
3. Meridian calls this automatically before each game launch for that emulator.
4. Add tests under `emulators/extensions/<emu_id>/tests/`.

See the `cemu` and `eden` extensions for reference implementations.

## Code Style

- **Python 3.10+** — use modern syntax (`match`, `X | Y` unions, etc.) where it improves clarity.
- **[PEP 8](https://peps.python.org/pep-0008/)** — 4-space indent, 88-char soft line limit.
- **Type hints** where practical. `snake_case` for functions/variables, `PascalCase` for classes.
- **Docstrings** on public APIs. Comments explain *why*, not *what*.
- **No unnecessary dependencies** — the project deliberately keeps its dependency list small.

## License

By contributing, you agree that your work is licensed under [AGPL-3.0](LICENSE).
