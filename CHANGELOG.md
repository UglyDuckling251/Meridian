# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Added
- **Eden controller profile sync** — new emulator extension (`emulators/extensions/eden/`) that converts Meridian player bindings into Eden's `qt-config.ini` format at launch, with adapter, config I/O, and full test suite.
- Ambient audio engine with numpy-based signal processing and per-source volume control.
- Audio device enumeration and channel mode settings (stereo/mono).
- Multiplayer browser dialog (UI scaffold).
- QML animated background with GLSL fragment shader support (`flag1998.frag`).
- Ambient sound assets.
- Console logo asset packs (black, white, colorful variants).
- Account dialog for future profile/sign-in workflow.
- Shared dialog utilities module (`meridian/ui/dialogs.py`).

### Changed
- Expanded emulator catalog with standalone entries for Ryubing, Eden, PCSX2, DuckStation, RPCS3, Cemu, Azahar, Citra, melonDS, DeSmuME, Xemu, and Xenia, plus 80+ RetroArch Libretro cores.
- Extended first-run setup handlers to cover 25+ emulators (firmware extraction, portable mode, key import).
- Broadened system definitions to 50+ platforms with file-extension mappings.
- Improved GPU backend selection (Auto/D3D11/OpenGL/Software) with 10-bit colour and MSAA surface formats.

## [0.1.0-dev] — 2026-02-16

Initial development build.

### Added
- PySide6 application shell with crash logging (`cache/latest.log`) and configurable debug log levels.
- Main window with 16:9 aspect lock, title bar icon, and Meridian branding.
- Menu bar: File, Edit, View, Tools, Multiplayer, Account, Help — with keyboard shortcuts throughout.
- Settings dialog with sidebar navigation (General, Graphics, Performance, Input, Emulators, Audio, Networking, Scraper, Tools, Advanced) and subcategory tabs.
- Config persistence to `%APPDATA%/Meridian/settings.json` via a dataclass-backed JSON store.
- ROM directory scanning with grid and list view modes, sorting (title/platform/added/played/count), favorites, hidden games, and right-click context menus.
- Emulator install pipeline — download and extract from GitHub Releases, direct URLs, and the RetroArch buildbot, with `.7z` and `.zip` support.
- Cemu controller profile sync extension (`emulators/extensions/cemu/`) — converts Meridian player bindings to Cemu XML profiles and writes per-game INI assignments.
- SDL2 gamepad input via pygame — binding configuration, hot-plug detection, per-player profiles, stick/trigger/hat/button support.
- SteamGridDB scraper integration with configurable content fields, artwork types, region priority, and API key management.
- Meridian colour palette and full Qt widget stylesheet with theme and density support.
- Bundled fonts: Ubuntu, Roboto, Work Sans. Icons: Lucide SVG set.
- `run.bat` Windows launcher.
- Project documentation: README, CONTRIBUTING, CHANGELOG, SECURITY, LICENSE (AGPL-3.0).
