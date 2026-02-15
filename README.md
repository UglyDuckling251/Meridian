# Meridian

A fully customizable, all-in-one frontend for organizing and playing your ROM collection.

Meridian is a native desktop application for Windows that gives you a single, unified interface to browse, manage, and launch games across every emulated platform. Think of it as your personal game library — one app to find any game and play it instantly through the emulator of your choice.

## Features

- **Unified ROM Library** — Scan and index ROM files across multiple directories and platforms into one searchable collection.
- **Emulator Integration** — Configure and launch any emulator (RetroArch, Dolphin, PCSX2, and more) directly from the app with per-system defaults.
- **Metadata Scraping** — Automatically fetch box art, screenshots, descriptions, genres, and release info for your games.
- **Collections & Favorites** — Organize games into custom collections, mark favorites, and track play history.
- **Fully Customizable** — Themes, layouts, and display options to make the frontend your own.
- **Controller & Keyboard Support** — Navigate the entire interface without a mouse.
- **Lightweight & Native** — Built with Python and Qt, not a web browser. Fast startup, low resource usage.

## Getting Started

### Prerequisites

- **Windows 10/11** (64-bit)
- **Python 3.10+**
- One or more emulators installed on your system

### Installation

```bash
git clone https://github.com/UglyDuckling251/Meridian.git
cd Meridian
pip install -r requirements.txt
```

### Running

Double-click `run.bat` or run from the command line:

```bash
python main.py
```

## Project Status

Meridian is in **early development**. The core application window and framework are in place. Active work is underway on the system browser, game grid, emulator configuration, and metadata scraping.

See the [Changelog](CHANGELOG.md) for a detailed history of what has been implemented so far.

## Contributing

Contributions are welcome. Please read the [Contributing Guide](CONTRIBUTING.md) before submitting a pull request.

## License

Meridian is licensed under the [GNU Affero General Public License v3.0](LICENSE). You are free to use, modify, and distribute this software under the terms of the AGPL-3.0. Any modified versions must also be made available under the same license. See the [LICENSE](LICENSE) file for the full text.

## Acknowledgments

Meridian is inspired by projects like [ES-DE](https://es-de.org/), [Playnite](https://playnite.link/), [LaunchBox](https://www.launchbox-app.com/), and [Pegasus](https://pegasus-frontend.org/). We stand on the shoulders of the emulation community.
