import webbrowser

from PySide6.QtWidgets import (
    QMenuBar, QMenu, QMessageBox, QFileDialog, QApplication, QDialog,
)
from PySide6.QtGui import QAction, QKeySequence

from meridian.core.config import Config
from meridian.ui.settings_dialog import SettingsDialog
from meridian.ui.account_dialog import AccountDialog


_VERSION = "0.1.0-dev"
_REPO_URL = "https://github.com/UglyDuckling251/Meridian"


class MenuBar(QMenuBar):
    """
    Application menu bar for Meridian.

    Menus: File, Edit, View, Tools, Multiplayer, Account, Help.
    Actions that aren't wired to real functionality yet are created
    but left disabled so the UI is honest about what works.
    """

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._window = parent
        self._config = config

        self._build_file_menu()
        self._build_edit_menu()
        self._build_view_menu()
        self._build_tools_menu()
        self._build_multiplayer_menu()
        self._build_account_menu()
        self._build_help_menu()

    # ------------------------------------------------------------------
    # File
    # ------------------------------------------------------------------

    def _build_file_menu(self):
        menu = self.addMenu("&File")

        self._act_add_rom_dir = _action(
            menu, "Add ROM &Directory...",
            shortcut="Ctrl+D",
            callback=self._on_add_rom_directory,
        )
        self._act_scan = _action(
            menu, "&Scan ROM Directories",
            shortcut="Ctrl+Shift+S",
            enabled=False,
        )

        menu.addSeparator()

        self._act_import = _action(
            menu, "&Import Game...",
            shortcut="Ctrl+I",
            enabled=False,
        )

        menu.addSeparator()

        self._act_exit = _action(
            menu, "E&xit",
            shortcut="Alt+F4",
            callback=self._on_exit,
        )

    # ------------------------------------------------------------------
    # Edit
    # ------------------------------------------------------------------

    def _build_edit_menu(self):
        menu = self.addMenu("&Edit")

        self._act_settings = _action(
            menu, "&Settings...",
            shortcut="Ctrl+,",
            callback=self._on_settings,
        )

        menu.addSeparator()

        self._act_select_all = _action(
            menu, "Select &All",
            shortcut="Ctrl+A",
            enabled=False,
        )
        self._act_deselect = _action(
            menu, "&Deselect All",
            shortcut="Ctrl+Shift+A",
            enabled=False,
        )

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def _build_view_menu(self):
        menu = self.addMenu("&View")

        self._act_grid_view = _action(
            menu, "&Grid View",
            shortcut="Ctrl+1",
            enabled=False,
        )
        self._act_list_view = _action(
            menu, "&List View",
            shortcut="Ctrl+2",
            enabled=False,
        )

        menu.addSeparator()

        # Sort By submenu
        sort_menu = QMenu("&Sort By", self)
        menu.addMenu(sort_menu)
        self._act_sort_title    = _action(sort_menu, "Title",       enabled=False)
        self._act_sort_platform = _action(sort_menu, "Platform",    enabled=False)
        self._act_sort_added    = _action(sort_menu, "Date Added",  enabled=False)
        self._act_sort_played   = _action(sort_menu, "Last Played", enabled=False)
        self._act_sort_count    = _action(sort_menu, "Play Count",  enabled=False)

        menu.addSeparator()

        self._act_favorites = _action(
            menu, "Show &Favorites Only",
            shortcut="Ctrl+F",
            enabled=False,
        )
        self._act_hidden = _action(
            menu, "Show &Hidden Games",
            enabled=False,
        )

        menu.addSeparator()

        self._act_fullscreen = _action(
            menu, "F&ullscreen",
            shortcut="F11",
            callback=self._on_toggle_fullscreen,
        )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _build_tools_menu(self):
        menu = self.addMenu("&Tools")

        self._act_manage_emu = _action(
            menu, "Manage &Emulators...",
            shortcut="Ctrl+E",
            enabled=False,
        )
        self._act_scrape = _action(
            menu, "Scrape &Metadata...",
            shortcut="Ctrl+M",
            enabled=False,
        )

        menu.addSeparator()

        self._act_verify = _action(
            menu, "&Verify ROMs",
            enabled=False,
        )
        self._act_clear_cache = _action(
            menu, "&Clear Metadata Cache",
            enabled=False,
        )

        menu.addSeparator()

        self._act_open_rom_dir = _action(
            menu, "Open ROM &Directory",
            enabled=False,
        )
        self._act_open_app_data = _action(
            menu, "Open &App Data Directory",
            enabled=False,
        )

    # ------------------------------------------------------------------
    # Multiplayer
    # ------------------------------------------------------------------

    def _build_multiplayer_menu(self):
        menu = self.addMenu("M&ultiplayer")

        self._act_host = _action(
            menu, "&Host Room...",
            enabled=False,
        )
        self._act_join = _action(
            menu, "&Join Room...",
            enabled=False,
        )
        self._act_direct = _action(
            menu, "&Direct Connect...",
            enabled=False,
        )

        menu.addSeparator()

        self._act_room_list = _action(
            menu, "Show Room &List",
            enabled=False,
        )

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def _build_account_menu(self):
        menu = self.addMenu("&Account")

        self._act_login = _action(
            menu, "&Sign In to Ariam...",
            callback=self._on_account,
        )
        self._act_create = _action(
            menu, "&Create Ariam Account...",
            callback=self._on_account,
        )

        menu.addSeparator()

        self._act_profile = _action(
            menu, "View &Profile",
            enabled=False,
        )
        self._act_signout = _action(
            menu, "Sign &Out",
            enabled=False,
        )

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def _build_help_menu(self):
        menu = self.addMenu("&Help")

        self._act_docs = _action(
            menu, "View &Documentation",
            callback=self._on_open_docs,
        )
        self._act_report_bug = _action(
            menu, "&Report a Bug",
            callback=self._on_report_bug,
        )

        menu.addSeparator()

        self._act_check_update = _action(
            menu, "Check for &Updates",
            enabled=False,
        )

        menu.addSeparator()

        self._act_about = _action(
            menu, "&About Meridian",
            callback=self._on_about,
        )
        self._act_about_qt = _action(
            menu, "About &Qt",
            callback=QApplication.instance().aboutQt,
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_account(self):
        dlg = AccountDialog(parent=self._window)
        dlg.exec()

    def _on_settings(self):
        dlg = SettingsDialog(self._config, parent=self._window)
        dlg.exec()
        # Always sync — the user may have clicked Save (which applies
        # changes live) and then closed the dialog via Cancel / X.
        self._config = dlg.saved_config()

    def _on_add_rom_directory(self):
        path = QFileDialog.getExistingDirectory(
            self._window, "Select ROM Directory",
        )
        if path:
            QMessageBox.information(
                self._window,
                "ROM Directory",
                f"Selected directory:\n{path}\n\n"
                "ROM scanning is not yet implemented.",
            )

    def _on_exit(self):
        QApplication.instance().quit()

    def _on_toggle_fullscreen(self):
        if self._window is None:
            return
        if self._window.isFullScreen():
            self._window.showNormal()
        else:
            self._window.showFullScreen()

    def _on_open_docs(self):
        webbrowser.open(f"{_REPO_URL}#readme")

    def _on_report_bug(self):
        webbrowser.open(f"{_REPO_URL}/issues/new")

    def _on_about(self):
        QMessageBox.about(
            self._window,
            "About Meridian",
            f"<h3>Meridian</h3>"
            f"<p>Version {_VERSION}</p>"
            f"<p>A fully customizable, all-in-one frontend for "
            f"organizing and playing your ROM collection.</p>"
            f"<p>Licensed under the "
            f"<a href='{_REPO_URL}/blob/main/LICENSE'>AGPL-3.0</a>.</p>"
            f"<p><a href='{_REPO_URL}'>GitHub</a></p>",
        )


# ----------------------------------------------------------------------
# Helper
# ----------------------------------------------------------------------

def _action(
    menu: QMenu,
    text: str,
    *,
    shortcut: str | None = None,
    callback=None,
    enabled: bool = True,
) -> QAction:
    """Create a QAction, add it to *menu*, and return it."""
    action = QAction(text, menu)
    if shortcut:
        action.setShortcut(QKeySequence(shortcut))
    if callback:
        action.triggered.connect(callback)
    action.setEnabled(enabled)
    menu.addAction(action)
    return action
