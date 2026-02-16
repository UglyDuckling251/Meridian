import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFontDatabase, QSurfaceFormat

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

    On Windows 11 we force **Direct3D 11** via Qt's RHI (Rendering Hardware
    Interface).  D3D11 uses the GPU's native 10-/16-bit pipeline for
    compositing, which eliminates the gradient banding that OpenGL's
    default 8-bit framebuffer produces on desktop Windows.
    """
    import sys

    # -- RHI backend selection ------------------------------------------
    if sys.platform == "win32":
        # D3D11 gives the best colour depth on modern Windows.
        os.environ["QSG_RHI_BACKEND"] = "d3d11"
    elif cfg.gpu_accelerated_ui:
        os.environ.setdefault("QSG_RHI_BACKEND", "opengl")
    else:
        os.environ.pop("QSG_RHI_BACKEND", None)

    # Share GL contexts (needed for any RHI backend)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

    # -- Surface format ------------------------------------------------
    fmt = QSurfaceFormat()
    fmt.setSwapInterval(1 if cfg.vsync else 0)
    # Request the deepest colour channels the driver can provide.
    fmt.setRedBufferSize(10)
    fmt.setGreenBufferSize(10)
    fmt.setBlueBufferSize(10)
    fmt.setAlphaBufferSize(8)
    # Request stronger MSAA so rounded QML primitives render cleaner.
    fmt.setSamples(8)
    QSurfaceFormat.setDefaultFormat(fmt)


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
