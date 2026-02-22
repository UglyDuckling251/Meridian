<p align="center">
  <img src="assets/logo.png" alt="Meridian" width="160">
</p>

<h1 align="center">Meridian</h1>

<p align="center">
  A fully customizable, all-in-one frontend for organizing and playing your ROM collection.<br>
  Your personal game library for all things emulators.
</p>

<p align="center">
  <a href="LICENSE">AGPL-3.0</a> · <a href="CHANGELOG.md">Changelog</a> · <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

> **Meridian does not include, distribute, or provide any means to download ROMs, BIOS files, or copyrighted game content.** Users are solely responsible for obtaining ROM files legally and in compliance with their local laws. Distributing copyrighted ROMs is illegal. The developers assume no liability for how users obtain or use ROM files.

## Features

- **Unified ROM Library** — Scan directories, index ROMs across 50+ platforms, browse in grid or list view, filter by favorites.
- **Managed Emulator Installs** — One-click install of standalone emulators and RetroArch cores directly from the Settings dialog. Meridian resolves the latest stable release from official sources automatically.
- **Controller Profile Sync** — Meridian pushes your controller bindings into emulator-native config formats at launch. Supported today for Cemu (XML profiles) and Eden (qt-config.ini), with the extension architecture open for more.
- **Metadata & Artwork Scraping** — Pull box art, screenshots, descriptions, and more from SteamGridDB. Configurable per-field, with region priority and resolution options.
- **Full Input Stack** — SDL2/XInput gamepad support via pygame, per-player binding configuration, keyboard navigation, and hot-plugging.
- **Ambient Audio** — Optional background audio layer with volume control and auto-mute when the window loses focus.
- **Deep Settings** — Sidebar-navigated Settings dialog covering General, Graphics, Performance, Input, Emulators, Audio, Networking, Scraper, and Advanced tabs.
- **Customizable UI** — Theme and density switching, custom stylesheets, QML-rendered animated background, configurable GPU backend (D3D11/OpenGL/Software).
- **Lightweight & Native** — Python + PySide6 (Qt 6). No browser engine, no Electron.

## Supported Systems

Meridian ships with system definitions and file-extension mappings for:

| | | |
|---|---|---|
| NES | SNES | Nintendo 64 |
| GameCube | Wii | Wii U |
| Nintendo Switch | Game Boy / Color / Advance | Virtual Boy |
| Nintendo DS | Nintendo 3DS | Pokemon Mini |
| Genesis / Mega Drive | Sega CD | 32X |
| Saturn | Dreamcast | Master System |
| Game Gear | SG-1000 | PlayStation 1/2/3 |
| PSP | PS Vita | Xbox |
| Xbox 360 | Atari 2600/5200/7800 | Lynx |
| Jaguar | Atari ST | TurboGrafx-16 |
| PC-FX | PC-98 | Neo Geo (Pocket / Arcade / CD) |
| MAME | 3DO | Vectrex |
| WonderSwan | MSX | ColecoVision |
| Intellivision | Odyssey 2 | Channel F |
| Commodore 64 | Amiga | Amstrad CPC |
| ZX Spectrum | MS-DOS | PC (Windows) |

## Emulator Catalog

Standalone emulators available through the built-in installer:

| Emulator | System(s) |
|----------|-----------|
| RetroArch + 80+ Libretro cores | Multi-system |
| Ryubing | Switch |
| Eden | Switch |
| PCSX2 | PS2 |
| DuckStation | PS1 |
| RPCS3 | PS3 |
| Cemu | Wii U |
| Dolphin (standalone via core) | GameCube / Wii |
| Azahar | 3DS |
| melonDS | DS |
| Xemu | Xbox |
| Xenia Canary | Xbox 360 |

All emulators are downloaded from their official release channels. Meridian does not bundle emulator binaries.

## Quick Start

**Requirements:** Windows 10 or later (64-bit), [Python 3.10+](https://www.python.org/downloads/) (make sure "Add Python to PATH" is checked during install), legally obtained ROMs.

```bash
git clone https://github.com/UglyDuckling251/Meridian.git
cd Meridian
```

Then double-click **`run.bat`**. On first launch it will automatically verify your Python version, install all required packages, and start Meridian. Dependencies are only reinstalled when `requirements.txt` changes.

### Dependencies

| Package | Purpose |
|---------|---------|
| PySide6 | Qt 6 GUI framework |
| pygame | SDL2 gamepad input and audio mixer |
| psutil | System/process info for performance settings |
| sounddevice | Audio device enumeration |
| numpy | Audio signal processing (ambient audio) |
| py7zr | Extracting `.7z` emulator archives |

## Project Status

Meridian is in active early development. The following subsystems are functional:

- Application shell with crash logging and debug log levels
- Full menu bar (File, Edit, View, Tools, Multiplayer, Account, Help)
- Settings dialog with sidebar navigation and per-section tabs
- Config persistence to `%APPDATA%/Meridian/settings.json`
- ROM directory scanning with grid/list browsing, favorites, sorting, and context menus
- Emulator install/update pipeline (GitHub releases + direct downloads + RetroArch buildbot)
- First-run setup handlers for 20+ emulators (firmware extraction, portable-mode init, key import)
- Controller profile sync extensions for Cemu and Eden
- SDL2 gamepad binding, hot-plug detection, per-player input config
- Ambient audio engine with numpy-based signal processing
- SteamGridDB metadata/artwork scraper integration
- Custom Qt stylesheet with theme and density support
- QML animated background with shader support

Work in progress: multiplayer lobby browser, update checker, and broader scraper source support.

## Emulator Installation

- **Install path:** `Meridian/emulators/<emulator-folder>/` (one emulator per subfolder).
- **Installer policy:** resolves the latest stable release at install time from official sources.
- **RetroArch:** installed as a base, then individual Libretro cores are added per system.
- **Extensions:** emulator-specific launch hooks live in `emulators/extensions/<emu_id>/` and run automatically before each game launch to sync controller profiles and other settings.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All PRs target the `dev` branch. Do not submit contributions that reference pirated content — they will be rejected.

## License

[AGPL-3.0](LICENSE). Modified versions must be released under the same license.

## Acknowledgments

Inspired by [ES-DE](https://es-de.org/), [Playnite](https://playnite.link/), [LaunchBox](https://www.launchbox-app.com/), and [Pegasus](https://pegasus-frontend.org/).

Bundled fonts: [Ubuntu](https://design.ubuntu.com/font) (UFL 1.0), [Roboto](https://fonts.google.com/specimen/Roboto) (OFL 1.1), [Work Sans](https://fonts.google.com/specimen/Work+Sans) (OFL 1.1). Icons: [Lucide](https://lucide.dev/) (ISC).
