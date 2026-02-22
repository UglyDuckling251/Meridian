# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFont, QFontDatabase, QSurfaceFormat

from meridian.core.config import Config
from meridian.ui.main_window import MainWindow
from meridian.ui.style import set_theme, set_density, build_stylesheet

_ROOT = Path(__file__).resolve().parent.parent
_LOGO = _ROOT / "assets" / "logo.png"
_FONTS_DIR = _ROOT / "assets" / "fonts"


def _apply_surface_settings(cfg: Config) -> None:
    """Configure the rendering backend, VSync, and GPU acceleration.

    These settings MUST be applied before QApplication.__init__ because they
    affect the underlying surface format and RHI backend used by Qt.
    """
    import sys

    # -- RHI backend selection ------------------------------------------
    backend = cfg.gpu_backend  # "Auto", "OpenGL", "Software"

    if backend == "Software":
        os.environ.pop("QSG_RHI_BACKEND", None)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
    elif backend == "OpenGL":
        os.environ["QSG_RHI_BACKEND"] = "opengl"
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, False)
    else:
        # Auto — use D3D11 on Windows for best colour depth, OpenGL elsewhere
        if sys.platform == "win32":
            os.environ["QSG_RHI_BACKEND"] = "d3d11"
        elif cfg.gpu_accelerated_ui:
            os.environ.setdefault("QSG_RHI_BACKEND", "opengl")
        else:
            os.environ.pop("QSG_RHI_BACKEND", None)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, False)

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

    # -- Surface format ------------------------------------------------
    fmt = QSurfaceFormat()
    fmt.setSwapInterval(1 if cfg.vsync else 0)

    if backend != "Software":
        fmt.setRedBufferSize(10)
        fmt.setGreenBufferSize(10)
        fmt.setBlueBufferSize(10)
        fmt.setAlphaBufferSize(8)
        fmt.setSamples(8 if cfg.gpu_accelerated_ui else 4)
        if backend == "OpenGL":
            fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
            fmt.setVersion(3, 3)
            fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)

    QSurfaceFormat.setDefaultFormat(fmt)


def apply_rendering_settings(cfg: Config) -> None:
    """Apply text anti-aliasing, animation speed, and image scaling settings.

    Safe to call at any point after QApplication has been created.
    """
    app = QApplication.instance()
    if not app:
        return

    # -- Animation speed -----------------------------------------------
    # Reduced motion overrides animation speed to disable all effects.
    speed = cfg.ui_animation_speed
    enable_anims = speed != "Instant" and not cfg.reduced_motion
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateMenu, enable_anims)
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, enable_anims)
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, enable_anims)
    app.setEffectEnabled(Qt.UIEffect.UI_FadeMenu, enable_anims)
    app.setEffectEnabled(Qt.UIEffect.UI_FadeTooltip, enable_anims)

    # -- Text anti-aliasing --------------------------------------------
    font = app.font()
    mode = cfg.text_rendering
    if mode == "Subpixel":
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    elif mode == "Greyscale":
        font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    else:  # None
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
    app.setFont(font)


class MeridianApp:
    """Top-level application controller for Meridian."""

    def __init__(self, argv: list[str]):
        # Surface settings must be applied before QApplication is created
        cfg = Config.load()
        _apply_surface_settings(cfg)

        self._qt = QApplication(argv)
        self._qt.setApplicationName("Meridian")
        self._qt.setOrganizationName("Meridian")
        self._qt.setWindowIcon(QIcon(str(_LOGO)))

        # Register bundled Ubuntu font family
        self._load_fonts()

        # Build the stylesheet
        set_theme(cfg.theme)
        set_density(cfg.ui_scale)
        self._qt.setStyleSheet(build_stylesheet(
            bold=cfg.bold_text,
            font_size_label=cfg.font_size_label,
            font_override=cfg.font_family,
            high_contrast=cfg.high_contrast,
        ))

        apply_rendering_settings(cfg)

        self._window = MainWindow()

    @staticmethod
    def _load_fonts():
        """Register all bundled font families from assets/fonts/."""
        if _FONTS_DIR.exists():
            for ttf in _FONTS_DIR.rglob("*.ttf"):
                QFontDatabase.addApplicationFont(str(ttf))

    def run(self) -> int:
        """Show the main window and enter the Qt event loop."""
        cfg = Config.load()
        if cfg.start_maximized:
            self._window.showMaximized()
        else:
            self._window.show()
        return self._qt.exec()
