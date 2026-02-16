"""
Centralised theme engine for Meridian.

Every colour, font, and dimension token used anywhere in the app lives here.
Themes are defined as ``Theme`` dataclass instances.  The active theme can be
switched at runtime and the stylesheet rebuilt instantly.

Usage
-----
    from meridian.ui.style import active_theme, set_theme, build_stylesheet, THEMES

    t = active_theme()          # current Theme object
    t.bg_base                   # e.g. "#0D1017"
    set_theme("Light")          # switch globally
    build_stylesheet()          # returns QSS for the active theme
"""

from __future__ import annotations

from dataclasses import dataclass


# ======================================================================
# Theme dataclass
# ======================================================================

@dataclass(frozen=True)
class Theme:
    name: str

    # Backgrounds
    bg_base:     str   # deepest background
    bg_surface:  str   # menu bar / panels
    bg_elevated: str   # dropdowns / floating panels
    bg_hover:    str   # hover highlight
    bg_pressed:  str   # active / pressed

    # Foregrounds
    fg_primary:   str  # main body text
    fg_secondary: str  # hints, captions
    fg_disabled:  str  # greyed-out

    # Borders
    border: str

    # Accents
    accent_primary:   str  # main accent (selections, links)
    accent_secondary: str  # secondary accent (active states)

    # Font (each theme owns its font; Ubuntu is the project default)
    font_family: str = "Ubuntu"
    font_size:   str = "9pt"


# ======================================================================
# Theme definitions  (15 themes)
# ======================================================================

THEMES: dict[str, Theme] = {

    # -- Default (Meridian) — cool blue-tinted dark --------------------
    "Default": Theme(
        name="Default",
        bg_base="#0D1017", bg_surface="#131820", bg_elevated="#1A2028",
        bg_hover="#1C2B36", bg_pressed="#233540",
        fg_primary="#CDD2DA", fg_secondary="#6E7A8A", fg_disabled="#384050",
        border="#1E2430",
        accent_primary="#3D7A9E", accent_secondary="#3A8A72",
    ),

    # -- Light — clean white -------------------------------------------
    "Light": Theme(
        name="Light",
        bg_base="#F5F6F8", bg_surface="#EBEDF0", bg_elevated="#FFFFFF",
        bg_hover="#D8DCE2", bg_pressed="#C8CDD4",
        fg_primary="#1E2128", fg_secondary="#5A6270", fg_disabled="#B0B6C0",
        border="#D0D4DA",
        accent_primary="#2E7BBF", accent_secondary="#2E9E72",
    ),

    # -- Dark — neutral dark (no blue tint) ----------------------------
    "Dark": Theme(
        name="Dark",
        bg_base="#141414", bg_surface="#1C1C1C", bg_elevated="#242424",
        bg_hover="#2E2E2E", bg_pressed="#383838",
        fg_primary="#D4D4D4", fg_secondary="#808080", fg_disabled="#4A4A4A",
        border="#2A2A2A",
        accent_primary="#4A9ECC", accent_secondary="#4AAA88",
    ),

    # -- Pearl White — warm off-white, gold accents --------------------
    "Pearl White": Theme(
        name="Pearl White",
        bg_base="#FAF8F5", bg_surface="#F0EDE8", bg_elevated="#FFFFFF",
        bg_hover="#E8E2D8", bg_pressed="#DDD5C8",
        fg_primary="#2C2620", fg_secondary="#7A7060", fg_disabled="#C0B8AA",
        border="#DDD6CA",
        accent_primary="#B8860B", accent_secondary="#8B7355",
    ),

    # -- Midnight Black — OLED black, cool blue accents ----------------
    "Midnight Black": Theme(
        name="Midnight Black",
        bg_base="#000000", bg_surface="#0A0A10", bg_elevated="#121218",
        bg_hover="#1A1A28", bg_pressed="#222236",
        fg_primary="#C8CCE0", fg_secondary="#606880", fg_disabled="#303848",
        border="#181828",
        accent_primary="#4488CC", accent_secondary="#3388AA",
    ),

    # -- Silver — medium gray, steel blue accents ----------------------
    "Silver": Theme(
        name="Silver",
        bg_base="#E0E2E6", bg_surface="#D0D2D8", bg_elevated="#EAECF0",
        bg_hover="#C0C4CC", bg_pressed="#B0B4BC",
        fg_primary="#20242A", fg_secondary="#5A5E68", fg_disabled="#A0A4AA",
        border="#C4C8D0",
        accent_primary="#4A6E8E", accent_secondary="#4A8A7A",
    ),

    # -- Blood — dark with deep red accents ----------------------------
    "Blood": Theme(
        name="Blood",
        bg_base="#100808", bg_surface="#180E0E", bg_elevated="#221414",
        bg_hover="#361818", bg_pressed="#441C1C",
        fg_primary="#DCC8C8", fg_secondary="#8A6868", fg_disabled="#4A3030",
        border="#2A1818",
        accent_primary="#AA2222", accent_secondary="#882222",
    ),

    # -- Atomic Purple — dark purple, violet accents -------------------
    "Atomic Purple": Theme(
        name="Atomic Purple",
        bg_base="#0E0A14", bg_surface="#14101C", bg_elevated="#1C1626",
        bg_hover="#2A2040", bg_pressed="#362A50",
        fg_primary="#D0C8E0", fg_secondary="#7A6E96", fg_disabled="#403660",
        border="#201830",
        accent_primary="#8844CC", accent_secondary="#6644AA",
    ),

    # -- 1998 — retro Windows 98 vibes ---------------------------------
    "1998": Theme(
        name="1998",
        bg_base="#C0C0C0", bg_surface="#D4D0C8", bg_elevated="#FFFFFF",
        bg_hover="#B0B0A8", bg_pressed="#A0A098",
        fg_primary="#000000", fg_secondary="#444444", fg_disabled="#888888",
        border="#808080",
        accent_primary="#000080", accent_secondary="#008080",
        font_family="MS Sans Serif",
    ),

    # -- Console — black terminal with neon green, monospace font ------
    "Console": Theme(
        name="Console",
        bg_base="#000000", bg_surface="#040A04", bg_elevated="#0A140A",
        bg_hover="#0A2A0A", bg_pressed="#0A3A0A",
        fg_primary="#00FF41", fg_secondary="#00AA2A", fg_disabled="#004A10",
        border="#003A10",
        accent_primary="#00FF41", accent_secondary="#00CC33",
        font_family="Consolas",
    ),

    # -- PlayStation — dark navy, PS blue ------------------------------
    "PlayStation": Theme(
        name="PlayStation",
        bg_base="#0A0E18", bg_surface="#101828", bg_elevated="#182038",
        bg_hover="#1C2C4A", bg_pressed="#243660",
        fg_primary="#D0D8E8", fg_secondary="#6878A0", fg_disabled="#344060",
        border="#1A2438",
        accent_primary="#0070D1", accent_secondary="#00439C",
    ),

    # -- Nintendo — white/light gray, Nintendo red ---------------------
    "Nintendo": Theme(
        name="Nintendo",
        bg_base="#F2F2F2", bg_surface="#E8E8E8", bg_elevated="#FFFFFF",
        bg_hover="#D8D8D8", bg_pressed="#C8C8C8",
        fg_primary="#1A1A1A", fg_secondary="#666666", fg_disabled="#AAAAAA",
        border="#D0D0D0",
        accent_primary="#E60012", accent_secondary="#C8102E",
    ),

    # -- XBOX — dark with Xbox green -----------------------------------
    "XBOX": Theme(
        name="XBOX",
        bg_base="#0A0C0A", bg_surface="#101810", bg_elevated="#182018",
        bg_hover="#1C2E1C", bg_pressed="#243824",
        fg_primary="#D0D8D0", fg_secondary="#688A68", fg_disabled="#344834",
        border="#1A2A1A",
        accent_primary="#107C10", accent_secondary="#0E6A0E",
    ),

    # -- Sega — dark blue, Sega blue -----------------------------------
    "Sega": Theme(
        name="Sega",
        bg_base="#080C18", bg_surface="#0E1628", bg_elevated="#162040",
        bg_hover="#1A2C5A", bg_pressed="#203670",
        fg_primary="#C8D4F0", fg_secondary="#6070A8", fg_disabled="#303C68",
        border="#142040",
        accent_primary="#1760C0", accent_secondary="#1050A0",
    ),

    # -- Arcade — black, neon accents ----------------------------------
    "Arcade": Theme(
        name="Arcade",
        bg_base="#050505", bg_surface="#0C0C0C", bg_elevated="#161616",
        bg_hover="#222222", bg_pressed="#2C2C2C",
        fg_primary="#E0E0E0", fg_secondary="#808080", fg_disabled="#404040",
        border="#1A1A1A",
        accent_primary="#FFD700", accent_secondary="#FF00AA",
    ),
}

THEME_NAMES: list[str] = list(THEMES.keys())


# ======================================================================
# Active theme state
# ======================================================================

_active: Theme = THEMES["Default"]


def active_theme() -> Theme:
    """Return the current global theme."""
    return _active


def set_theme(name: str) -> Theme:
    """Set the active theme by name.  Returns the new theme."""
    global _active
    _active = THEMES.get(name, THEMES["Default"])
    return _active


# ======================================================================
# Backward-compatible module-level aliases
# These are updated by _sync_aliases() whenever set_theme() won't help
# (they're snapshots, not live).  Prefer active_theme().attr in new code.
# ======================================================================

BG_BASE = _active.bg_base
BG_SURFACE = _active.bg_surface
BG_ELEVATED = _active.bg_elevated
BG_HOVER = _active.bg_hover
BG_PRESSED = _active.bg_pressed
FG_PRIMARY = _active.fg_primary
FG_SECONDARY = _active.fg_secondary
FG_DISABLED = _active.fg_disabled
BORDER = _active.border
ACCENT_BLUE = _active.accent_primary
ACCENT_GREEN = _active.accent_secondary


# ======================================================================
# Dimensions (theme-independent)
# ======================================================================

_BAR_PADDING_V = "3px"
_BAR_PADDING_H = "7px"
_ITEM_PADDING_V = "4px"
_ITEM_PADDING_H = "20px"
_SEPARATOR_H = "1px"
_MENU_RADIUS = "4px"


# ======================================================================
# Stylesheet builder
# ======================================================================

_density: int = 3  # 1-5, default middle


def set_density(level: int) -> None:
    """Set the global UI density (1=compact, 5=spacious)."""
    global _density
    _density = max(1, min(5, level))


def get_density() -> int:
    return _density


_FONT_SIZE_MAP = {
    "Small": "8pt",
    "Medium": "9pt",
    "Large": "10pt",
    "Extra Large": "11pt",
}


def _is_dark(t: Theme) -> bool:
    """Return True if the theme's base background is dark."""
    c = int(t.bg_base.lstrip("#"), 16)
    r, g, b = (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF
    return (r * 0.299 + g * 0.587 + b * 0.114) < 128


def _hc_overrides(t: Theme) -> str:
    """Return extra QSS rules that boost contrast for accessibility."""
    dark = _is_dark(t)
    fg = "#FFFFFF" if dark else "#000000"
    fg2 = "#C0C0C0" if dark else "#333333"
    dis = "#808080"
    bdr = t.fg_secondary
    acc = t.accent_primary

    return f"""
    /* ================================================================= */
    /*  High-contrast overrides                                           */
    /* ================================================================= */

    /* Stronger text */
    QWidget       {{ color: {fg}; }}
    QLabel        {{ color: {fg}; }}
    QMenuBar::item {{ color: {fg2}; }}
    QMenuBar::item:selected {{ color: {fg}; }}
    QLabel#sectionLabel {{ color: {fg2}; }}
    QLabel#emptyMessage {{ color: {fg2}; }}
    QLabel#footerVersion {{ color: {fg2}; }}
    QPushButton#footerButton {{ color: {fg2}; }}
    QPushButton#footerButton:hover {{ color: {fg}; }}
    QPushButton#linkButton {{ color: {fg2}; }}
    QPushButton#linkButton:hover {{ color: {acc}; }}

    /* Thicker, more visible borders */
    QMenuBar      {{ border-bottom: 2px solid {bdr}; }}
    QMenu         {{ border: 2px solid {bdr}; }}
    QToolTip      {{ border: 2px solid {bdr}; }}
    QPushButton   {{ border: 2px solid {bdr}; }}
    QPushButton:hover {{ border-color: {acc}; }}
    QLineEdit     {{ border: 2px solid {bdr}; }}
    QLineEdit:focus {{ border: 2px solid {acc}; }}
    QComboBox     {{ border: 2px solid {bdr}; }}
    QComboBox:hover {{ border-color: {acc}; }}
    QSpinBox      {{ border: 2px solid {bdr}; }}
    QSpinBox:hover {{ border-color: {acc}; }}
    QListWidget   {{ border: 2px solid {bdr}; }}
    QTabWidget::pane {{ border: 2px solid {bdr}; border-top: none; }}
    QTabBar::tab  {{ border: 2px solid {bdr}; border-bottom: none; }}
    QGroupBox     {{ border: 2px solid {bdr}; }}
    QCheckBox::indicator {{ border: 2px solid {fg2}; }}
    QCheckBox::indicator:hover {{ border-color: {acc}; }}

    /* Stronger disabled state */
    QPushButton:disabled {{ color: {dis}; border-color: {dis}; }}
    QCheckBox:disabled {{ color: {dis}; }}
    QLineEdit::placeholder {{ color: {dis}; }}
    QComboBox:disabled {{ color: {dis}; }}

    /* More visible focus / selection */
    QListWidget::item:selected {{ background-color: {acc}; color: #FFFFFF; }}
    QMenu::item:selected {{ background-color: {acc}; color: #FFFFFF; }}
    QListWidget#settingsSidebar::item:selected {{
        border-left: 4px solid {acc}; color: {fg};
    }}

    /* Visible scroll bar handles */
    QScrollBar::handle:vertical   {{ background-color: {fg2}; }}
    QScrollBar::handle:horizontal {{ background-color: {fg2}; }}
    """


def build_stylesheet(
    theme: Theme | None = None,
    *,
    bold: bool = False,
    font_size_label: str = "Medium",
    font_override: str | None = None,
    high_contrast: bool = False,
) -> str:
    """Return the complete application QSS for the given (or active) theme."""
    t = theme or _active

    # Density multiplier: level 1=0.6, 2=0.8, 3=1.0, 4=1.2, 5=1.5
    dm = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.2, 5: 1.5}.get(_density, 1.0)

    def dp(base: int) -> str:
        """Scale a base pixel value by density and return as 'Npx'."""
        return f"{max(1, round(base * dm))}px"

    # Font size from label
    font_sz = _FONT_SIZE_MAP.get(font_size_label, t.font_size)
    font_wt = "font-weight: 600;" if bold else ""
    # Themes with locked fonts — their identity depends on a specific typeface
    font_fam = t.font_family if t.name in ("1998", "Console") else (font_override or t.font_family)

    return f"""

    /* ================================================================= */
    /*  Global defaults                                                   */
    /* ================================================================= */

    * {{
        font-family: "{font_fam}";
        font-size: {font_sz};
        {font_wt}
    }}


    /* ================================================================= */
    /*  Menu bar                                                          */
    /* ================================================================= */

    QMenuBar {{
        background-color: {t.bg_surface};
        color: {t.fg_primary};
        border-bottom: {_SEPARATOR_H} solid {t.border};
        padding: 0px; spacing: 0px;
    }}
    QMenuBar::item {{
        background: transparent; color: {t.fg_secondary};
        padding: {_BAR_PADDING_V} {_BAR_PADDING_H}; margin: 0px;
    }}
    QMenuBar::item:selected {{ background-color: {t.bg_hover}; color: {t.fg_primary}; }}
    QMenuBar::item:pressed  {{ background-color: {t.bg_pressed}; color: #FFFFFF; }}

    /* ================================================================= */
    /*  Dropdown menus                                                    */
    /* ================================================================= */

    QMenu {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
        border: {_SEPARATOR_H} solid {t.border};
        border-radius: {_MENU_RADIUS}; padding: 4px 0px;
    }}
    QMenu::item {{
        padding: {_ITEM_PADDING_V} {_ITEM_PADDING_H};
        margin: 0px 4px; border-radius: 3px;
    }}
    QMenu::item:selected {{ background-color: {t.bg_hover}; color: #FFFFFF; }}
    QMenu::item:disabled {{ color: {t.fg_disabled}; }}
    QMenu::separator {{
        height: {_SEPARATOR_H}; background-color: {t.border}; margin: 4px 12px;
    }}
    QMenu::right-arrow {{ width: 12px; height: 12px; }}

    /* ================================================================= */
    /*  Tooltips                                                          */
    /* ================================================================= */

    QToolTip {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
        border: {_SEPARATOR_H} solid {t.border}; padding: 4px 8px;
    }}

    /* ================================================================= */
    /*  Base widget backgrounds  (prevent native gray bleed-through)      */
    /* ================================================================= */

    QMainWindow   {{ background-color: {t.bg_base}; color: {t.fg_primary}; }}
    QDialog       {{ background-color: {t.bg_base}; color: {t.fg_primary}; }}
    QScrollArea   {{ background-color: {t.bg_base}; border: none; }}
    QScrollArea > QWidget > QWidget {{ background-color: {t.bg_base}; }}

    /* Child widgets inherit parent background by default */
    QWidget       {{ color: {t.fg_primary}; }}
    QLabel        {{ background: transparent; }}
    QFrame        {{ background: transparent; }}

    /* ================================================================= */
    /*  Tabs                                                              */
    /* ================================================================= */

    QTabWidget::pane {{
        background-color: {t.bg_surface};
        border: {_SEPARATOR_H} solid {t.border}; border-top: none;
        border-radius: 0px 0px {_MENU_RADIUS} {_MENU_RADIUS};
    }}
    QTabBar::tab {{
        background-color: {t.bg_base}; color: {t.fg_secondary};
        border: {_SEPARATOR_H} solid {t.border}; border-bottom: none;
        padding: 5px 16px; margin-right: 2px;
        border-radius: {_MENU_RADIUS} {_MENU_RADIUS} 0px 0px;
    }}
    QTabBar::tab:selected       {{ background-color: {t.bg_surface}; color: {t.fg_primary}; }}
    QTabBar::tab:hover:!selected {{ background-color: {t.bg_elevated}; color: {t.fg_primary}; }}

    /* ================================================================= */
    /*  Group boxes                                                       */
    /* ================================================================= */

    QGroupBox {{
        background-color: transparent; color: {t.fg_secondary};
        border: {_SEPARATOR_H} solid {t.border}; border-radius: {_MENU_RADIUS};
        margin-top: {dp(14)}; padding: {dp(14)} {dp(10)} {dp(10)} {dp(10)};
        font-size: 8pt; font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; subcontrol-position: top left;
        left: 10px; padding: 0px 4px; color: {t.fg_secondary};
    }}

    /* ================================================================= */
    /*  Buttons                                                           */
    /* ================================================================= */

    QPushButton {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
        border: {_SEPARATOR_H} solid {t.border}; border-radius: 3px;
        padding: {dp(4)} {dp(14)}; min-height: {dp(20)};
    }}
    QPushButton:hover   {{ background-color: {t.bg_hover}; border-color: {t.accent_primary}; color: #FFFFFF; }}
    QPushButton:pressed  {{ background-color: {t.bg_pressed}; }}
    QPushButton:disabled {{ color: {t.fg_disabled}; border-color: {t.border}; }}

    /* Primary (Save) */
    QPushButton#primaryButton {{
        background-color: {t.accent_primary}; color: #FFFFFF;
        border: none; padding: 3px 24px; border-radius: 3px; font-weight: 600;
    }}
    QPushButton#primaryButton:hover   {{ background-color: {t.accent_secondary}; }}
    QPushButton#primaryButton:pressed  {{ background-color: {t.bg_pressed}; }}
    QPushButton#primaryButton:disabled {{ background-color: {t.fg_disabled}; color: {t.bg_base}; }}

    /* Cancel */
    QPushButton#cancelButton {{
        background-color: transparent; color: {t.fg_secondary};
        border: {_SEPARATOR_H} solid {t.border}; border-radius: 3px;
        padding: 3px 24px; font-weight: 400;
    }}
    QPushButton#cancelButton:hover   {{ color: {t.fg_primary}; border-color: {t.fg_secondary}; }}
    QPushButton#cancelButton:pressed  {{ background-color: {t.bg_pressed}; }}

    /* ================================================================= */
    /*  Check boxes                                                       */
    /* ================================================================= */

    QCheckBox {{ color: {t.fg_primary}; spacing: 6px; }}
    QCheckBox:disabled {{ color: {t.fg_disabled}; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 2px solid {t.fg_secondary}; border-radius: 3px;
        background-color: {t.bg_elevated};
    }}
    QCheckBox::indicator:checked {{
        background-color: {t.accent_primary}; border-color: {t.accent_primary};
        image: none;
    }}
    QCheckBox::indicator:unchecked {{
        background-color: {t.bg_elevated}; border-color: {t.fg_secondary};
    }}
    QCheckBox::indicator:hover {{ border-color: {t.accent_primary}; }}
    QCheckBox::indicator:disabled {{
        background-color: {t.bg_surface}; border-color: {t.fg_disabled};
    }}
    QCheckBox::indicator:checked:disabled {{
        background-color: {t.fg_disabled}; border-color: {t.fg_disabled};
    }}

    /* ================================================================= */
    /*  Line edits                                                        */
    /* ================================================================= */

    QLineEdit {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
        border: {_SEPARATOR_H} solid {t.border}; border-radius: 3px;
        padding: {dp(4)} {dp(8)};
        selection-background-color: {t.accent_primary}; selection-color: #FFFFFF;
    }}
    QLineEdit:focus       {{ border-color: {t.accent_primary}; }}
    QLineEdit::placeholder {{ color: {t.fg_disabled}; }}

    /* ================================================================= */
    /*  List widgets                                                      */
    /* ================================================================= */

    QListWidget {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
        border: {_SEPARATOR_H} solid {t.border}; border-radius: 3px; outline: none;
    }}
    QListWidget::item          {{ padding: {dp(4)} {dp(8)}; border-radius: 2px; }}
    QListWidget::item:selected {{ background-color: {t.bg_hover}; color: #FFFFFF; }}
    QListWidget::item:hover:!selected {{ background-color: {t.bg_surface}; }}
    QListWidget::item:alternate {{ background-color: rgba(128, 128, 128, 5%); }}
    QListWidget#gamesList {{
        background-color: transparent;
        border: none;
    }}
    QListWidget#gamesList::item {{
        background-color: rgba(0, 0, 0, 40);
        margin: 1px 6px;
    }}
    QListWidget#gamesList::item:selected {{
        background-color: {t.bg_hover};
    }}

    /* ================================================================= */
    /*  Labels                                                            */
    /* ================================================================= */

    QLabel {{ color: {t.fg_primary}; }}
    QLabel#sectionLabel {{ color: {t.fg_secondary}; font-size: 8pt; font-weight: 600; }}
    QLabel#creditsSectionHeader {{ color: {t.accent_primary}; font-size: 9pt; font-weight: 700; }}
    QLabel#creditsPersonName {{ font-weight: 600; }}

    /* ================================================================= */
    /*  Dialog button box                                                 */
    /* ================================================================= */

    QDialogButtonBox > QPushButton {{ min-width: 72px; }}

    /* ================================================================= */
    /*  Scroll bars                                                       */
    /* ================================================================= */

    QScrollBar:vertical {{
        background: {t.bg_base}; width: 6px; margin: 0px; padding: 0px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {t.border}; border-radius: 3px; min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background-color: {t.fg_disabled}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {t.bg_base}; }}

    QScrollBar:horizontal {{
        background: {t.bg_base}; height: 6px; margin: 0px; padding: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {t.border}; border-radius: 3px; min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{ background-color: {t.fg_disabled}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {t.bg_base}; }}

    /* ================================================================= */
    /*  Settings sidebar                                                  */
    /* ================================================================= */

    QListWidget#settingsSidebar {{
        background-color: {t.bg_surface}; border: none;
        border-right: {_SEPARATOR_H} solid {t.border}; outline: none;
    }}
    QListWidget#settingsSidebar::item {{
        padding: {dp(10)} {dp(16)}; border-radius: 0px;
        color: {t.fg_secondary}; border-left: 3px solid transparent;
    }}
    QListWidget#settingsSidebar::item:selected {{
        background-color: {t.bg_base}; color: {t.fg_primary};
        border-left: 3px solid {t.accent_primary};
    }}
    QListWidget#settingsSidebar::item:hover:!selected {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
    }}

    /* ================================================================= */
    /*  Settings subcategory tabs                                         */
    /* ================================================================= */

    QTabWidget#subTabs::pane {{
        background-color: {t.bg_base}; border: none;
        border-top: {_SEPARATOR_H} solid {t.border};
    }}
    QTabWidget#subTabs > QTabBar::tab {{
        background-color: transparent; color: {t.fg_secondary};
        border: none; border-bottom: 2px solid transparent;
        padding: 7px 18px; margin: 0px; border-radius: 0px;
    }}
    QTabWidget#subTabs > QTabBar::tab:selected {{
        color: {t.fg_primary}; border-bottom: 2px solid {t.accent_primary};
    }}
    QTabWidget#subTabs > QTabBar::tab:hover:!selected {{
        color: {t.fg_primary}; border-bottom: 2px solid {t.bg_hover};
    }}

    /* ================================================================= */
    /*  Settings pages background                                         */
    /* ================================================================= */

    QStackedWidget#settingsPages {{ background-color: {t.bg_base}; }}

    /* ================================================================= */
    /*  Combo boxes                                                       */
    /* ================================================================= */

    QComboBox {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
        border: {_SEPARATOR_H} solid {t.border}; border-radius: 3px;
        padding: {dp(4)} {dp(8)}; min-height: {dp(20)};
    }}
    QComboBox:hover    {{ border-color: {t.accent_primary}; }}
    QComboBox:disabled {{ color: {t.fg_disabled}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
        border: {_SEPARATOR_H} solid {t.border};
        selection-background-color: {t.bg_hover}; selection-color: #FFFFFF; outline: none;
    }}

    /* ================================================================= */
    /*  Spin boxes                                                        */
    /* ================================================================= */

    QSpinBox {{
        background-color: {t.bg_elevated}; color: {t.fg_primary};
        border: {_SEPARATOR_H} solid {t.border}; border-radius: 3px;
        padding: {dp(4)} {dp(8)}; min-height: {dp(20)};
    }}
    QSpinBox:hover    {{ border-color: {t.accent_primary}; }}
    QSpinBox:disabled {{ color: {t.fg_disabled}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ background-color: {t.bg_surface}; border: none; width: 16px; }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: {t.bg_hover}; }}

    /* ================================================================= */
    /*  Sliders                                                           */
    /* ================================================================= */

    QSlider::groove:horizontal {{
        background-color: {t.bg_elevated}; border: {_SEPARATOR_H} solid {t.border};
        height: 4px; border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background-color: {t.accent_primary}; width: 14px; height: 14px;
        margin: -5px 0px; border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover    {{ background-color: {t.accent_secondary}; }}
    QSlider::handle:horizontal:disabled {{ background-color: {t.fg_disabled}; }}

    /* ================================================================= */
    /*  Account dialog                                                    */
    /* ================================================================= */

    QWidget#accountHeader {{
        background-color: {t.bg_surface}; border-bottom: {_SEPARATOR_H} solid {t.border};
    }}
    QLabel#accountTitle {{ font-size: 16pt; font-weight: 700; color: {t.accent_primary}; letter-spacing: 2px; }}
    QLabel#accountSubtitle {{ font-size: 8pt; color: {t.fg_secondary}; }}

    /* ================================================================= */
    /*  Credits dialog                                                    */
    /* ================================================================= */

    QWidget#creditsHeader {{
        background-color: {t.bg_surface}; border-bottom: {_SEPARATOR_H} solid {t.border};
    }}
    QLabel#creditsTitle    {{ font-size: 14pt; font-weight: 700; color: {t.fg_primary}; }}
    QLabel#creditsSubtitle {{ font-size: 8pt; color: {t.fg_secondary}; }}

    /* ================================================================= */
    /*  Empty state                                                       */
    /* ================================================================= */

    QWidget#emptyState {{ background: transparent; }}
    QLabel#emptyMessage {{ color: {t.fg_secondary}; font-size: 8pt; font-weight: 400; }}

    /* ================================================================= */
    /*  Footer                                                            */
    /* ================================================================= */

    QWidget#footer {{
        background-color: {t.bg_surface}; border-top: 1px solid {t.border};
        min-height: 26px; max-height: 26px;
    }}
    QLabel#footerVersion {{ color: {t.fg_disabled}; font-size: 8pt; }}
    QLabel#footerResource {{ background: transparent; font-size: 8pt; font-weight: 600; }}
    QPushButton#footerButton {{
        background: transparent; color: {t.fg_secondary}; border: none;
        padding: {_BAR_PADDING_V} {_BAR_PADDING_H};
    }}
    QPushButton#footerButton:hover    {{ color: {t.fg_primary}; }}
    QPushButton#footerButton:disabled {{ color: {t.fg_disabled}; }}

    /* Buttons that open external links — pointer cursor + underline on hover */
    QPushButton#linkButton {{
        background: transparent; color: {t.fg_secondary}; border: none;
        padding: {_BAR_PADDING_V} {_BAR_PADDING_H};
    }}
    QPushButton#linkButton:hover {{ color: {t.accent_primary}; text-decoration: underline; }}

    /* ================================================================= */
    /*  Player / emulator card slots                                      */
    /* ================================================================= */

    QWidget#playerSlot {{
        background-color: {t.bg_elevated}; border: 1px solid {t.border}; border-radius: 3px;
    }}

    /* ================================================================= */
    /*  Scale circle buttons  (UI Scale selector)                         */
    /* ================================================================= */

    QPushButton#scaleCircle {{
        background-color: {t.bg_elevated}; color: {t.fg_secondary};
        border: 2px solid {t.border}; border-radius: 15px;
        min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
        font-size: 9pt; font-weight: 600; padding: 0px;
    }}
    QPushButton#scaleCircle:hover {{
        border-color: {t.accent_primary}; color: {t.fg_primary};
    }}
    QPushButton#scaleCircle[checked="true"] {{
        background-color: {t.accent_primary}; color: #FFFFFF;
        border-color: {t.accent_primary};
    }}
    """ + (_hc_overrides(t) if high_contrast else "")
