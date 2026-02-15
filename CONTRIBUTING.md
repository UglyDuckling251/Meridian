<p align="center">
  <img src="assets/logo.png" alt="Meridian" width="80">
</p>

# Contributing to Meridian

> **Do not** submit code, assets, or links that reference pirated content or ROM download sites. Violations result in an immediate ban. Emulation is legal — piracy is not.

## Getting Started

```bash
git clone https://github.com/UglyDuckling251/Meridian.git
cd Meridian
pip install -r requirements.txt
python main.py
```

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases. Do not target PRs here. |
| `dev`  | Active development. All PRs go here. |

## Submitting Changes

1. Fork the repo and branch from `dev`.
2. Make focused, atomic commits with clear messages.
3. Test thoroughly.
4. Open a PR against `dev` with a summary, related issues, and screenshots for UI changes.

## Reporting Bugs

[Open an issue](https://github.com/UglyDuckling251/Meridian/issues/new) with: steps to reproduce, expected vs. actual behaviour, OS/Python version, and any logs or screenshots.

## Style

- Python 3.10+, [PEP 8](https://peps.python.org/pep-0008/), 4-space indent.
- Type hints where practical. `snake_case` functions, `PascalCase` classes.
- Docstrings on public APIs. Comments explain *why*, not *what*.

## License

Contributions are licensed under [AGPL-3.0](LICENSE).
