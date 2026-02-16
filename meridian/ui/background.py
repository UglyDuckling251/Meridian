"""
Background widget for Meridian's main window.

Renders through **Qt Quick's GPU scene graph** (via ``QQuickWidget``) so
that all gradients and colour blending happen at the GPU's native
precision — typically 10- or 16-bit on Windows 11 with the D3D11 RHI
backend — eliminating the 8-bit banding produced by the QPainter raster
engine.

Supports three visual modes controlled from Python:

* **None** — solid theme base colour.
* **Image** — GPU-scaled image fill (aspect-crop).
* **Animation** — procedural backgrounds (Waves, Starscape) driven
  by a QML timer.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQuickWidgets import QQuickWidget

from meridian.ui.style import active_theme

_QML_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "qml" / "Background.qml"
_ALLOWED_ANIMATIONS = {"waves", "starscape"}


class BackgroundWidget(QQuickWidget):
    """GPU-rendered background using a QML scene.

    Drop-in replacement for the former ``QWidget`` + ``QPainter``
    implementation.  The public API (``set_mode``, ``set_fps``) is
    unchanged so that ``MainWindow`` doesn't need modifications.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.setClearColor(QColor(active_theme().bg_base))
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setSource(QUrl.fromLocalFile(str(_QML_PATH)))

        # Log QML errors to stderr for debugging
        self.statusChanged.connect(self._on_status)

    # -- public API (unchanged from the old widget) --------------------

    def set_mode(
        self,
        mode: str,
        image_path: str = "",
        animation: str = "",
        reduced_motion: bool = False,
    ) -> None:
        root = self.rootObject()
        if root is None:
            return

        t = active_theme()
        root.setProperty("mode", mode)
        root.setProperty("bgBase", QColor(t.bg_base))
        root.setProperty("accent1", QColor(t.accent_primary))
        root.setProperty("accent2", QColor(t.accent_secondary))
        root.setProperty("imagePath",
                         image_path.replace("\\", "/") if image_path else "")
        anim = animation.lower() if animation else ""
        if mode == "Animation" and anim not in _ALLOWED_ANIMATIONS:
            anim = "waves"
        root.setProperty("animType", anim)
        root.setProperty("reducedMotion", reduced_motion)

    def set_fps(self, fps: int) -> None:
        root = self.rootObject()
        if root is not None:
            root.setProperty("fps", max(5, fps))

    # -- internals -----------------------------------------------------

    def _on_status(self, status):
        if status == QQuickWidget.Status.Error:
            for err in self.errors():
                print(f"[Background QML] {err.toString()}")
