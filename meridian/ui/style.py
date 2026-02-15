"""
Centralised Qt stylesheet for Meridian.

Design tokens live at the top so the palette can be tweaked in one place.
The stylesheet targets the menu bar, dropdown menus, and will be extended
as more UI is added.

Colour language
---------------
Backgrounds carry a faint blue undertone so the app feels cool and oceanic,
never generic.  Two accent hues — a muted steel-blue and a quiet jade-green
— provide just enough colour to guide the eye without being flashy.
"""

# -- Palette ---------------------------------------------------------------
# Backgrounds — near-black with a cool blue undertone

BG_BASE      = "#0D1017"   # deepest background  (central canvas)
BG_SURFACE   = "#131820"   # menu bar / side panels
BG_ELEVATED  = "#1A2028"   # dropdown menus / floating panels
BG_HOVER     = "#1C2B36"   # hover highlight  (blue tint emerges)
BG_PRESSED   = "#233540"   # active / pressed  (deeper teal)

# Foregrounds — cool off-whites and muted blue-grays

FG_PRIMARY   = "#CDD2DA"   # main body text
FG_SECONDARY = "#6E7A8A"   # shortcuts, hints, captions
FG_DISABLED  = "#384050"   # greyed-out items

# Borders / separators

BORDER       = "#1E2430"   # subtle dividers

# Accent colours — the two signature Meridian hues

ACCENT_BLUE  = "#3D7A9E"   # muted ocean blue  (selections, links)
ACCENT_GREEN = "#3A8A72"   # quiet jade green   (active states, highlights)

# -- Font ------------------------------------------------------------------

_FONT_FAMILY = "Segoe UI"
_FONT_SIZE   = "9pt"

# -- Dimensions ------------------------------------------------------------

_BAR_PADDING_V = "3px"      # vertical padding inside menu-bar items
_BAR_PADDING_H = "7px"      # horizontal padding inside menu-bar items
_ITEM_PADDING_V = "4px"     # vertical padding inside dropdown items
_ITEM_PADDING_H = "20px"    # horizontal padding inside dropdown items
_SEPARATOR_H   = "1px"      # separator line height
_MENU_RADIUS   = "4px"      # dropdown corner radius


def build_stylesheet() -> str:
    """Return the complete application stylesheet as a string."""
    return f"""

    /* ------------------------------------------------------------------ */
    /*  Global defaults                                                    */
    /* ------------------------------------------------------------------ */

    * {{
        font-family: "{_FONT_FAMILY}";
        font-size: {_FONT_SIZE};
    }}

    /* ------------------------------------------------------------------ */
    /*  Menu bar (top bar)                                                 */
    /* ------------------------------------------------------------------ */

    QMenuBar {{
        background-color: {BG_SURFACE};
        color: {FG_PRIMARY};
        border-bottom: {_SEPARATOR_H} solid {BORDER};
        padding: 0px;
        spacing: 0px;
    }}

    QMenuBar::item {{
        background: transparent;
        color: {FG_SECONDARY};
        padding: {_BAR_PADDING_V} {_BAR_PADDING_H};
        margin: 0px;
    }}

    QMenuBar::item:selected {{
        background-color: {BG_HOVER};
        color: {FG_PRIMARY};
    }}

    QMenuBar::item:pressed {{
        background-color: {BG_PRESSED};
        color: #FFFFFF;
    }}

    /* ------------------------------------------------------------------ */
    /*  Dropdown menus                                                     */
    /* ------------------------------------------------------------------ */

    QMenu {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
        border: {_SEPARATOR_H} solid {BORDER};
        border-radius: {_MENU_RADIUS};
        padding: 4px 0px;
    }}

    QMenu::item {{
        padding: {_ITEM_PADDING_V} {_ITEM_PADDING_H};
        margin: 0px 4px;
        border-radius: 3px;
    }}

    QMenu::item:selected {{
        background-color: {BG_HOVER};
        color: #FFFFFF;
    }}

    QMenu::item:disabled {{
        color: {FG_DISABLED};
    }}

    QMenu::separator {{
        height: {_SEPARATOR_H};
        background-color: {BORDER};
        margin: 4px 12px;
    }}

    QMenu::right-arrow {{
        width: 12px;
        height: 12px;
    }}

    /* ------------------------------------------------------------------ */
    /*  Tooltips                                                           */
    /* ------------------------------------------------------------------ */

    QToolTip {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
        border: {_SEPARATOR_H} solid {BORDER};
        padding: 4px 8px;
        font-size: {_FONT_SIZE};
    }}

    /* ------------------------------------------------------------------ */
    /*  Dialogs                                                            */
    /* ------------------------------------------------------------------ */

    QDialog {{
        background-color: {BG_BASE};
        color: {FG_PRIMARY};
    }}

    /* ------------------------------------------------------------------ */
    /*  Tab widget                                                         */
    /* ------------------------------------------------------------------ */

    QTabWidget::pane {{
        background-color: {BG_SURFACE};
        border: {_SEPARATOR_H} solid {BORDER};
        border-top: none;
        border-radius: 0px 0px {_MENU_RADIUS} {_MENU_RADIUS};
    }}

    QTabBar::tab {{
        background-color: {BG_BASE};
        color: {FG_SECONDARY};
        border: {_SEPARATOR_H} solid {BORDER};
        border-bottom: none;
        padding: 5px 16px;
        margin-right: 2px;
        border-radius: {_MENU_RADIUS} {_MENU_RADIUS} 0px 0px;
    }}

    QTabBar::tab:selected {{
        background-color: {BG_SURFACE};
        color: {FG_PRIMARY};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
    }}

    /* ------------------------------------------------------------------ */
    /*  Group boxes                                                        */
    /* ------------------------------------------------------------------ */

    QGroupBox {{
        background-color: transparent;
        color: {FG_SECONDARY};
        border: {_SEPARATOR_H} solid {BORDER};
        border-radius: {_MENU_RADIUS};
        margin-top: 14px;
        padding: 14px 10px 10px 10px;
        font-size: 8pt;
        font-weight: 600;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0px 4px;
        color: {FG_SECONDARY};
    }}

    /* ------------------------------------------------------------------ */
    /*  Buttons                                                            */
    /* ------------------------------------------------------------------ */

    QPushButton {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
        border: {_SEPARATOR_H} solid {BORDER};
        border-radius: 3px;
        padding: 4px 14px;
        min-height: 20px;
    }}

    QPushButton:hover {{
        background-color: {BG_HOVER};
        border-color: {ACCENT_BLUE};
        color: #FFFFFF;
    }}

    QPushButton:pressed {{
        background-color: {BG_PRESSED};
    }}

    QPushButton:disabled {{
        color: {FG_DISABLED};
        border-color: {BORDER};
    }}

    /* ------------------------------------------------------------------ */
    /*  Check boxes                                                        */
    /* ------------------------------------------------------------------ */

    QCheckBox {{
        color: {FG_PRIMARY};
        spacing: 6px;
    }}

    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: {_SEPARATOR_H} solid {FG_SECONDARY};
        border-radius: 3px;
        background-color: {BG_ELEVATED};
    }}

    QCheckBox::indicator:checked {{
        background-color: {ACCENT_BLUE};
        border-color: {ACCENT_BLUE};
    }}

    QCheckBox::indicator:hover {{
        border-color: {ACCENT_BLUE};
    }}

    /* ------------------------------------------------------------------ */
    /*  Line edits                                                         */
    /* ------------------------------------------------------------------ */

    QLineEdit {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
        border: {_SEPARATOR_H} solid {BORDER};
        border-radius: 3px;
        padding: 4px 8px;
        selection-background-color: {ACCENT_BLUE};
        selection-color: #FFFFFF;
    }}

    QLineEdit:focus {{
        border-color: {ACCENT_BLUE};
    }}

    QLineEdit::placeholder {{
        color: {FG_DISABLED};
    }}

    /* ------------------------------------------------------------------ */
    /*  List widgets                                                       */
    /* ------------------------------------------------------------------ */

    QListWidget {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
        border: {_SEPARATOR_H} solid {BORDER};
        border-radius: 3px;
        outline: none;
    }}

    QListWidget::item {{
        padding: 4px 8px;
        border-radius: 2px;
    }}

    QListWidget::item:selected {{
        background-color: {BG_HOVER};
        color: #FFFFFF;
    }}

    QListWidget::item:hover:!selected {{
        background-color: {BG_SURFACE};
    }}

    QListWidget::item:alternate {{
        background-color: rgba(255, 255, 255, 2%);
    }}

    /* ------------------------------------------------------------------ */
    /*  Labels                                                             */
    /* ------------------------------------------------------------------ */

    QLabel {{
        color: {FG_PRIMARY};
    }}

    QLabel#sectionLabel {{
        color: {FG_SECONDARY};
        font-size: 8pt;
        font-weight: 600;
    }}

    /* ------------------------------------------------------------------ */
    /*  Dialog button box                                                   */
    /* ------------------------------------------------------------------ */

    QDialogButtonBox > QPushButton {{
        min-width: 72px;
    }}

    /* ------------------------------------------------------------------ */
    /*  Scroll bars                                                        */
    /* ------------------------------------------------------------------ */

    QScrollBar:vertical {{
        background-color: {BG_BASE};
        width: 8px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {BG_PRESSED};
        border-radius: 4px;
        min-height: 24px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {ACCENT_BLUE};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {BG_BASE};
        height: 8px;
        margin: 0px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {BG_PRESSED};
        border-radius: 4px;
        min-width: 24px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {ACCENT_BLUE};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ------------------------------------------------------------------ */
    /*  Settings sidebar                                                   */
    /* ------------------------------------------------------------------ */

    QListWidget#settingsSidebar {{
        background-color: {BG_SURFACE};
        border: none;
        border-right: {_SEPARATOR_H} solid {BORDER};
        outline: none;
        font-size: {_FONT_SIZE};
    }}

    QListWidget#settingsSidebar::item {{
        padding: 10px 16px;
        border-radius: 0px;
        color: {FG_SECONDARY};
        border-left: 3px solid transparent;
    }}

    QListWidget#settingsSidebar::item:selected {{
        background-color: {BG_BASE};
        color: {FG_PRIMARY};
        border-left: 3px solid {ACCENT_BLUE};
    }}

    QListWidget#settingsSidebar::item:hover:!selected {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
    }}

    /* ------------------------------------------------------------------ */
    /*  Settings subcategory tabs                                          */
    /* ------------------------------------------------------------------ */

    QTabWidget#subTabs::pane {{
        background-color: {BG_BASE};
        border: none;
        border-top: {_SEPARATOR_H} solid {BORDER};
    }}

    QTabWidget#subTabs > QTabBar::tab {{
        background-color: transparent;
        color: {FG_SECONDARY};
        border: none;
        border-bottom: 2px solid transparent;
        padding: 7px 18px;
        margin: 0px;
        border-radius: 0px;
    }}

    QTabWidget#subTabs > QTabBar::tab:selected {{
        color: {FG_PRIMARY};
        border-bottom: 2px solid {ACCENT_BLUE};
    }}

    QTabWidget#subTabs > QTabBar::tab:hover:!selected {{
        color: {FG_PRIMARY};
        border-bottom: 2px solid {BG_HOVER};
    }}

    /* ------------------------------------------------------------------ */
    /*  Settings pages background                                          */
    /* ------------------------------------------------------------------ */

    QStackedWidget#settingsPages {{
        background-color: {BG_BASE};
    }}

    /* ------------------------------------------------------------------ */
    /*  Primary action button                                              */
    /* ------------------------------------------------------------------ */

    QPushButton#primaryButton {{
        background-color: {ACCENT_BLUE};
        color: #FFFFFF;
        border: none;
        padding: 5px 20px;
        border-radius: 3px;
        font-weight: 600;
    }}

    QPushButton#primaryButton:hover {{
        background-color: {ACCENT_GREEN};
    }}

    QPushButton#primaryButton:pressed {{
        background-color: {BG_PRESSED};
    }}

    /* ------------------------------------------------------------------ */
    /*  Combo boxes                                                        */
    /* ------------------------------------------------------------------ */

    QComboBox {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
        border: {_SEPARATOR_H} solid {BORDER};
        border-radius: 3px;
        padding: 4px 8px;
        min-height: 20px;
    }}

    QComboBox:hover {{
        border-color: {ACCENT_BLUE};
    }}

    QComboBox:disabled {{
        color: {FG_DISABLED};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
        border: {_SEPARATOR_H} solid {BORDER};
        selection-background-color: {BG_HOVER};
        selection-color: #FFFFFF;
        outline: none;
    }}

    /* ------------------------------------------------------------------ */
    /*  Spin boxes                                                         */
    /* ------------------------------------------------------------------ */

    QSpinBox {{
        background-color: {BG_ELEVATED};
        color: {FG_PRIMARY};
        border: {_SEPARATOR_H} solid {BORDER};
        border-radius: 3px;
        padding: 4px 8px;
        min-height: 20px;
    }}

    QSpinBox:hover {{
        border-color: {ACCENT_BLUE};
    }}

    QSpinBox:disabled {{
        color: {FG_DISABLED};
    }}

    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {BG_SURFACE};
        border: none;
        width: 16px;
    }}

    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {BG_HOVER};
    }}

    /* ------------------------------------------------------------------ */
    /*  Sliders                                                            */
    /* ------------------------------------------------------------------ */

    QSlider::groove:horizontal {{
        background-color: {BG_ELEVATED};
        border: {_SEPARATOR_H} solid {BORDER};
        height: 4px;
        border-radius: 2px;
    }}

    QSlider::handle:horizontal {{
        background-color: {ACCENT_BLUE};
        width: 14px;
        height: 14px;
        margin: -5px 0px;
        border-radius: 7px;
    }}

    QSlider::handle:horizontal:hover {{
        background-color: {ACCENT_GREEN};
    }}

    QSlider::handle:horizontal:disabled {{
        background-color: {FG_DISABLED};
    }}

    /* ------------------------------------------------------------------ */
    /*  Account dialog                                                     */
    /* ------------------------------------------------------------------ */

    QWidget#accountHeader {{
        background-color: {BG_SURFACE};
        border-bottom: {_SEPARATOR_H} solid {BORDER};
    }}

    QLabel#accountTitle {{
        font-size: 16pt;
        font-weight: 700;
        color: {ACCENT_BLUE};
        letter-spacing: 2px;
    }}

    QLabel#accountSubtitle {{
        font-size: 8pt;
        color: {FG_SECONDARY};
    }}

    /* ------------------------------------------------------------------ */
    /*  Credits dialog                                                     */
    /* ------------------------------------------------------------------ */

    QWidget#creditsHeader {{
        background-color: {BG_SURFACE};
        border-bottom: {_SEPARATOR_H} solid {BORDER};
    }}

    QLabel#creditsTitle {{
        font-size: 14pt;
        font-weight: 700;
        color: {FG_PRIMARY};
    }}

    QLabel#creditsSubtitle {{
        font-size: 8pt;
        color: {FG_SECONDARY};
    }}

    /* ------------------------------------------------------------------ */
    /*  Empty state (main window)                                          */
    /* ------------------------------------------------------------------ */

    QWidget#emptyState {{
        background-color: {BG_BASE};
    }}

    QLabel#emptyMessage {{
        color: {FG_SECONDARY};
        font-size: 8pt;
        font-weight: 400;
    }}

    /* ------------------------------------------------------------------ */
    /*  Footer bar                                                         */
    /* ------------------------------------------------------------------ */

    QWidget#footer {{
        background-color: {BG_SURFACE};
        border-top: 1px solid {BORDER};
        min-height: 26px;
        max-height: 26px;
    }}

    QLabel#footerVersion {{
        color: {FG_DISABLED};
        font-size: {_FONT_SIZE};
    }}

    QPushButton#footerButton {{
        background: transparent;
        color: {FG_SECONDARY};
        border: none;
        padding: {_BAR_PADDING_V} {_BAR_PADDING_H};
        font-size: {_FONT_SIZE};
    }}

    QPushButton#footerButton:hover {{
        color: {FG_PRIMARY};
    }}

    QPushButton#footerButton:disabled {{
        color: {FG_DISABLED};
    }}

    /* ------------------------------------------------------------------ */
    /*  Player slot (Input > Controllers)                                  */
    /* ------------------------------------------------------------------ */

    QWidget#playerSlot {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 3px;
    }}
    """
