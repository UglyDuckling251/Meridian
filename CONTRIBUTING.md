# Contributing to Meridian

Thank you for your interest in contributing to Meridian. This document outlines the process and guidelines for contributing to the project.

## Important Legal Notice

Meridian is a game launcher and library organizer. It does **not** download, host, distribute, or include any ROMs, BIOS files, firmware, or copyrighted game data.

**All contributors must adhere to the following rules:**

- **Do not** submit any code, assets, links, or documentation that includes, references, or directs users to pirated content or ROM download sites.
- **Do not** include any copyrighted game content (ROMs, BIOS files, firmware, box art ripped from copyrighted sources without permission, etc.) in any pull request.
- **Do not** add features whose primary purpose is to facilitate the downloading, sharing, or illegal distribution of copyrighted material.
- **Any contribution that violates these rules will be rejected immediately** and may result in a permanent ban from the project.

Emulation itself is legal. Piracy is not. Please respect the intellectual property rights of game developers and publishers.

## Code of Conduct

By participating in this project, you agree to treat all contributors and community members with respect. Harassment, discrimination, and toxic behavior will not be tolerated.

## How to Contribute

### Reporting Bugs

If you find a bug, please [open an issue](https://github.com/UglyDuckling251/Meridian/issues/new) with the following information:

- A clear and descriptive title.
- Steps to reproduce the issue.
- Expected behavior vs. actual behavior.
- Your OS version and Python version.
- Screenshots or error logs, if applicable.

### Suggesting Features

Feature suggestions are welcome. Please [open an issue](https://github.com/UglyDuckling251/Meridian/issues/new) with:

- A clear description of the feature and the problem it solves.
- Any relevant examples, mockups, or references.
- Whether you are willing to help implement it.

**Note:** Feature suggestions that involve downloading, distributing, or linking to copyrighted content will not be considered.

### Submitting Code

1. **Fork** the repository and create your branch from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes.** Keep commits focused and atomic. Write clear commit messages.

3. **Test your changes** thoroughly before submitting.

4. **Open a pull request** against the `dev` branch (not `main`). Include:
   - A summary of what was changed and why.
   - Any related issue numbers (e.g., `Closes #12`).
   - Screenshots for UI changes.

### Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only. Do not target PRs here. |
| `dev`  | Active development. All pull requests should target this branch. |

## Development Setup

```bash
git clone https://github.com/UglyDuckling251/Meridian.git
cd Meridian
pip install -r requirements.txt
python main.py
```

### Project Structure

```
Meridian/
├── main.py                  # Application entry point
├── run.bat                  # Windows launcher
├── requirements.txt         # Python dependencies
└── meridian/
    ├── app.py               # QApplication wrapper
    └── ui/
        └── main_window.py   # Main window (16:9 ratio lock, DWM title bar)
```

## Style Guidelines

- **Language**: Python 3.10+
- **Formatting**: Follow [PEP 8](https://peps.python.org/pep-0008/). Use 4-space indentation.
- **Type Hints**: Use type annotations where practical.
- **Naming**: `snake_case` for functions and variables, `PascalCase` for classes.
- **Docstrings**: All public classes and functions should have docstrings.
- **Comments**: Explain *why*, not *what*. Avoid redundant comments.

## License

By contributing to Meridian, you agree that your contributions will be licensed under the [GNU Affero General Public License v3.0](LICENSE).
