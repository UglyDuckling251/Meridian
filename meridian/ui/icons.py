# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

"""
Lucide icon rendering for Meridian.

Stores Lucide SVG path data inline and renders them as QIcons / QPixmaps
via PySide6's QSvgRenderer.  Icons can be rendered at any size and colour.

Source: https://lucide.dev/icons/
License: ISC (https://github.com/lucide-icons/lucide/blob/main/LICENSE)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QByteArray, QRectF
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QImage
from PySide6.QtSvg import QSvgRenderer


# -- SVG path data (Lucide, 24x24 viewBox) --------------------------------

_ICONS: dict[str, str] = {
    "settings": (
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0'
        'l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51'
        'a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2'
        ' 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0'
        ' 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73'
        '-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73'
        'l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2'
        ' 0 0 0-2-2z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "trash-2": (
        '<path d="M3 6h18"/>'
        '<path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>'
        '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>'
        '<line x1="10" x2="10" y1="11" y2="17"/>'
        '<line x1="14" x2="14" y1="11" y2="17"/>'
    ),
    "refresh-cw": (
        '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
        '<path d="M21 3v5h-5"/>'
        '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
        '<path d="M8 16H3v5"/>'
    ),
    "download": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" x2="12" y1="15" y2="3"/>'
    ),
    "wifi": (
        '<path d="M12 20h.01"/>'
        '<path d="M2 8.82a15 15 0 0 1 20 0"/>'
        '<path d="M5 12.859a10 10 0 0 1 14 0"/>'
        '<path d="M8.5 16.429a5 5 0 0 1 7 0"/>'
    ),
    "wifi-off": (
        '<path d="M12 20h.01"/>'
        '<path d="M8.5 16.429a5 5 0 0 1 7 0"/>'
        '<path d="M5 12.859a10 10 0 0 1 5.17-2.69"/>'
        '<path d="M19 12.859a10 10 0 0 0-2.007-1.523"/>'
        '<path d="M2 8.82a15 15 0 0 1 4.177-2.643"/>'
        '<path d="M22 8.82a15 15 0 0 0-11.288-3.764"/>'
        '<path d="m2 2 20 20"/>'
    ),
    "circle-check": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": (
        '<path d="M18 6 6 18"/>'
        '<path d="m6 6 12 12"/>'
    ),
    "package": (
        '<path d="M16.5 9.4 7.55 4.24"/>'
        '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8'
        'a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
        '<polyline points="3.29 7 12 12 20.71 7"/>'
        '<line x1="12" x2="12" y1="22" y2="12"/>'
    ),
    "heart": (
        '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2'
        '-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>'
    ),
    "users": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "code": (
        '<polyline points="16 18 22 12 16 6"/>'
        '<polyline points="8 6 2 12 8 18"/>'
    ),
    "external-link": (
        '<path d="M15 3h6v6"/>'
        '<path d="M10 14 21 3"/>'
        '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    ),
    "arrow-up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    "arrow-down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "minus": '<path d="M5 12h14"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "alert-triangle": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16'
        'a2 2 0 0 0 1.73-3"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "monitor": (
        '<rect width="20" height="14" x="2" y="3" rx="2"/>'
        '<line x1="8" x2="16" y1="21" y2="21"/>'
        '<line x1="12" x2="12" y1="17" y2="21"/>'
    ),
    "gamepad-2": (
        '<line x1="6" x2="10" y1="11" y2="11"/>'
        '<line x1="8" x2="8" y1="9" y2="13"/>'
        '<line x1="15" x2="15.01" y1="12" y2="12"/>'
        '<line x1="18" x2="18.01" y1="10" y2="10"/>'
        '<path d="M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152'
        'C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414'
        'A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3'
        ' 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151'
        'A4 4 0 0 0 17.32 5z"/>'
    ),
    "cpu": (
        '<rect width="16" height="16" x="4" y="4" rx="2"/>'
        '<rect width="6" height="6" x="9" y="9" rx="1"/>'
        '<path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/>'
        '<path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/>'
        '<path d="M9 2v2"/><path d="M9 20v2"/>'
    ),
    "zap": (
        '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02'
        'A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46'
        'l1.92-6.02A1 1 0 0 0 11 14z"/>'
    ),
    "plug": (
        '<path d="M12 22v-5"/>'
        '<path d="M9 8V2"/>'
        '<path d="M15 8V2"/>'
        '<path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>'
    ),
}


# -- Rendering -------------------------------------------------------------

def _build_svg(icon_name: str, color: str, stroke_width: float = 2.0) -> bytes:
    """Build a complete SVG document for the given Lucide icon name."""
    paths = _ICONS.get(icon_name, "")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{stroke_width}" stroke-linecap="round" '
        f'stroke-linejoin="round">{paths}</svg>'
    )
    return svg.encode("utf-8")


def icon(name: str, size: int = 16, color: str = "#CDD2DA") -> QIcon:
    """Return a QIcon rendered from a Lucide icon at the given size and colour."""
    return QIcon(pixmap(name, size, color))


def pixmap(name: str, size: int = 16, color: str = "#CDD2DA") -> QPixmap:
    """Return a QPixmap rendered from a Lucide icon at the given size and colour."""
    svg_data = _build_svg(name, color)
    renderer = QSvgRenderer(QByteArray(svg_data))

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    return QPixmap.fromImage(img)
