# Changelog

All notable changes to Meridian will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffolding with Python and PySide6 (Qt6).
- Native application window with "Meridian" title and black taskbar icon.
- 16:9 aspect ratio lock enforced via Windows `WM_SIZING` (flicker-free resizing).
- White (light) title bar forced through the Windows DWM API.
- Dark canvas background for future game UI.
- `run.bat` launcher for quick startup on Windows.
- `.gitignore`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, and `SECURITY.md`.
