# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_CACHE_DIR = _ROOT / "cache"
_CRASH_LOG = _CACHE_DIR / "latest.log"


def _install_crash_logger() -> None:
    """Replace the default exception hook so unhandled errors are written
    to ``cache/latest.log`` before the process terminates."""
    _original_hook = sys.excepthook

    def _crash_hook(exc_type, exc_value, exc_tb):
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            header = (
                f"Meridian crash log\n"
                f"==================\n"
                f"Timestamp : {timestamp}\n"
                f"Python    : {sys.version}\n"
                f"Platform  : {sys.platform}\n"
                f"Exception : {exc_type.__name__}: {exc_value}\n"
                f"\n"
            )
            _CRASH_LOG.write_text(header + tb_text, encoding="utf-8")
        except Exception:
            pass
        _original_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _crash_hook


def _apply_debug_logging() -> None:
    """Configure Python logging based on the user's debug settings."""
    import logging
    try:
        from meridian.core.config import Config
        cfg = Config.load()
        if cfg.debug_logging:
            level = getattr(logging, cfg.debug_log_level, logging.WARNING)
            log_file = _CACHE_DIR / "meridian_debug.log"
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            logging.basicConfig(
                level=level,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                handlers=[
                    logging.FileHandler(str(log_file), encoding="utf-8"),
                    logging.StreamHandler(sys.stderr),
                ],
                force=True,
            )
        else:
            logging.basicConfig(level=logging.WARNING, force=True)
    except Exception:
        logging.basicConfig(level=logging.WARNING, force=True)


def main():
    _install_crash_logger()
    _apply_debug_logging()
    from meridian.app import MeridianApp
    app = MeridianApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
