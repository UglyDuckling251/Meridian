# Meridian

A fully customizable, all-in-one frontend for organizing and playing your ROM collection.

Meridian is a native desktop application for Windows that gives you a single, unified interface to browse, manage, and launch games across every emulated platform. Your personal, all in one game library for all things emulators.

> **Legal Notice:** Meridian is a game launcher and library organizer. It does **not** download, host, distribute, or include any ROMs, BIOS files, firmware, or copyrighted game data of any kind. Users are solely responsible for ensuring that any ROM files used with Meridian are obtained **legally** and in full compliance with the laws of their jurisdiction. Please respect the intellectual property rights of game developers and publishers.

## Features

- **Unified ROM Library** — Scan and index ROM files across multiple directories and platforms into one searchable collection.
- **Emulator Integration** — Configure and launch any emulator (RetroArch, Dolphin, PCSX2, and more) directly from the app with per-system defaults.
- **Metadata Scraping** — Automatically fetch box art, screenshots, descriptions, genres, and release info for your games.
- **Collections & Favorites** — Organize games into custom collections, mark favorites, and track play history.
- **Fully Customizable** — Themes, layouts, and display options to make the frontend your own.
- **Controller & Keyboard Support** — Navigate the entire interface without a mouse.
- **Lightweight & Native** — Built with Python and Qt, not a web browser. Fast startup, low resource usage.

## Legal Disclaimer

Meridian is **strictly a frontend application**. It provides an interface for organizing and launching games through third-party emulators. Meridian does not facilitate, encourage, or condone software piracy in any form.

- **Meridian does not include, bundle, or distribute any ROMs, BIOS files, or copyrighted game content.**
- **Meridian does not provide any means to download, share, or acquire ROMs.**
- **Users must only use ROM files that they have legally obtained** — for example, by dumping games from physical media that they personally own, or by using legally purchased digital copies where applicable.
- **Distributing copyrighted ROMs is illegal.** The unauthorized copying and distribution of copyrighted software is a violation of intellectual property law in most jurisdictions worldwide.
- **The developers and contributors of Meridian assume no responsibility or liability for how users obtain or use ROM files.**

By using Meridian, you acknowledge and agree that it is your sole responsibility to comply with all applicable local, national, and international laws regarding ROM files and emulation.

## Getting Started

### Prerequisites

- **Windows 10/11** (64-bit)
- **Python 3.10+**
- One or more emulators installed on your system
- **Legally obtained ROM files** from platforms you own

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

**Important:** Do not submit any contributions that include, reference, or link to pirated content, ROM download sites, or any other illegally distributed copyrighted material. Such contributions will be rejected immediately and may result in a ban from the project.

## License

Meridian is licensed under the [GNU Affero General Public License v3.0](LICENSE). You are free to use, modify, and distribute this software under the terms of the AGPL-3.0. Any modified versions must also be made available under the same license. See the [LICENSE](LICENSE) file for the full text.

## Acknowledgments

Meridian is inspired by projects like [ES-DE](https://es-de.org/), [Playnite](https://playnite.link/), [LaunchBox](https://www.launchbox-app.com/), and [Pegasus](https://pegasus-frontend.org/). We stand on the shoulders of the emulation community.
