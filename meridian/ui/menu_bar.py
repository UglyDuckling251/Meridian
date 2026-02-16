import webbrowser

from PySide6.QtWidgets import (
    QMenuBar, QMenu, QMessageBox, QApplication, QDialog,
)
from PySide6.QtGui import QAction, QActionGroup, QKeySequence

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

        self._act_scan = _action(
            menu, "&Scan ROM Directories",
            shortcut="Ctrl+D",
            callback=self._on_scan_rom_directories,
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
            callback=self._on_select_all,
        )
        self._act_deselect = _action(
            menu, "&Deselect All",
            shortcut="Ctrl+Shift+A",
            callback=self._on_deselect_all,
        )

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def _build_view_menu(self):
        menu = self.addMenu("&View")

        self._act_grid_view = _action(
            menu, "&Grid View",
            shortcut="Ctrl+1",
            callback=self._on_view_grid,
        )
        self._act_grid_view.setCheckable(True)
        self._act_list_view = _action(
            menu, "&List View",
            shortcut="Ctrl+2",
            callback=self._on_view_list,
        )
        self._act_list_view.setCheckable(True)
        self._act_list_view.setChecked(True)
        self._view_mode_group = QActionGroup(self)
        self._view_mode_group.setExclusive(True)
        self._view_mode_group.addAction(self._act_grid_view)
        self._view_mode_group.addAction(self._act_list_view)

        menu.addSeparator()

        # Sort By submenu
        sort_menu = QMenu("&Sort By", self)
        menu.addMenu(sort_menu)
        self._act_sort_title = _action(sort_menu, "Title", callback=lambda: self._on_sort("title"))
        self._act_sort_platform = _action(sort_menu, "Platform", callback=lambda: self._on_sort("platform"))
        self._act_sort_added = _action(sort_menu, "Date Added", callback=lambda: self._on_sort("added"))
        self._act_sort_played = _action(sort_menu, "Last Played", callback=lambda: self._on_sort("played"))
        self._act_sort_count = _action(sort_menu, "Play Count", callback=lambda: self._on_sort("count"))
        self._sort_group = QActionGroup(self)
        self._sort_group.setExclusive(True)
        for act in (
            self._act_sort_title,
            self._act_sort_platform,
            self._act_sort_added,
            self._act_sort_played,
            self._act_sort_count,
        ):
            act.setCheckable(True)
            self._sort_group.addAction(act)
        self._act_sort_title.setChecked(True)

        menu.addSeparator()

        self._act_favorites = _action(
            menu, "Show &Favorites Only",
            shortcut="Ctrl+F",
            callback=self._on_toggle_favorites_only,
        )
        self._act_favorites.setCheckable(True)
        self._act_hidden = _action(
            menu, "Show &Hidden Games",
            callback=self._on_toggle_hidden,
        )
        self._act_hidden.setCheckable(True)

        menu.addSeparator()

        self._act_fullscreen = _action(
            menu, "F&ullscreen",
            shortcut="F11",
            callback=self._on_toggle_fullscreen,
        )
        self._act_fullscreen.setCheckable(True)

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _build_tools_menu(self):
        menu = self.addMenu("&Tools")

        metadata_menu = QMenu("&Metadata && Scraping", self)
        menu.addMenu(metadata_menu)
        self._act_scrape_library = _action(
            metadata_menu,
            "Scrape &Library Metadata",
            callback=self._on_scrape_library_metadata,
        )
        self._act_scrape_selected = _action(
            metadata_menu,
            "Scrape &Selected Game Metadata",
            callback=self._on_scrape_selected_metadata,
        )
        self._act_scrape = _action(
            metadata_menu,
            "Scraper &Settings...",
            shortcut="Ctrl+M",
            callback=lambda: self._on_open_settings_page("Tools", "Scraper"),
        )
        metadata_menu.addSeparator()
        self._act_clear_cache = _action(
            metadata_menu,
            "&Clear Metadata Cache",
            callback=self._on_clear_metadata_cache,
        )

        menu.addSeparator()

        self._act_manage_emu = _action(
            menu, "&Emulator Settings...",
            shortcut="Ctrl+E",
            callback=lambda: self._on_open_settings_page("Emulators", "Installed"),
        )
        self._act_file_mgmt = _action(
            menu, "&File Management...",
            callback=lambda: self._on_open_settings_page("Tools", "File Management"),
        )
        self._act_clock_settings = _action(
            menu, "Cl&ock Settings...",
            callback=lambda: self._on_open_settings_page("Tools", "Clock"),
        )

        menu.addSeparator()

        self._act_amiibo = _action(
            menu, "&Amiibo...",
            callback=self._on_amiibo,
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
        self._open_settings_dialog()

    def _on_scan_rom_directories(self):
        if self._window is None:
            return
        scan_fn = getattr(self._window, "scan_rom_directories", None)
        if callable(scan_fn):
            scan_fn(interactive=True)
            return
        QMessageBox.information(
            self._window,
            "Scan ROM Directories",
            "ROM scanning is not available in this window.",
        )

    def _on_select_all(self):
        if self._window is None:
            return
        fn = getattr(self._window, "select_all_games", None)
        if callable(fn):
            fn()

    def _on_deselect_all(self):
        if self._window is None:
            return
        fn = getattr(self._window, "deselect_all_games", None)
        if callable(fn):
            fn()

    def _on_open_settings_page(self, category: str, sub_tab: str):
        self._open_settings_dialog(category=category, sub_tab=sub_tab)

    def _on_scrape_library_metadata(self):
        if self._window is None:
            return
        fn = getattr(self._window, "scrape_metadata_library", None)
        if callable(fn):
            fn()
            return
        QMessageBox.information(
            self._window,
            "Scrape Metadata",
            "Library metadata scraping is not available in this window.",
        )

    def _on_scrape_selected_metadata(self):
        if self._window is None:
            return
        fn = getattr(self._window, "scrape_selected_metadata", None)
        if callable(fn):
            fn()
            return
        QMessageBox.information(
            self._window,
            "Scrape Selected Metadata",
            "Selected-game metadata scraping is not available in this window.",
        )

    def _on_clear_metadata_cache(self):
        if self._window is None:
            return
        fn = getattr(self._window, "clear_metadata_cache", None)
        if callable(fn):
            fn()
            return
        QMessageBox.information(
            self._window,
            "Clear Metadata Cache",
            "Metadata cache handling is not available in this window.",
        )

    def _on_amiibo(self):
        QMessageBox.information(
            self._window,
            "Amiibo",
            "Amiibo tools are coming soon.\n\n"
            "UI entry is in place; backend logic is not implemented yet.",
        )

    def _open_settings_dialog(self, category: str | None = None, sub_tab: str | None = None):
        dlg = SettingsDialog(self._config, parent=self._window)
        if category:
            dlg.navigate_to(category, sub_tab)
        dlg.exec()
        # Always sync — the user may have clicked Save (which applies
        # changes live) and then closed the dialog via Cancel / X.
        self._config = dlg.saved_config()

    def _on_exit(self):
        QApplication.instance().quit()

    def _on_toggle_fullscreen(self):
        if self._window is None:
            return
        if self._window.isFullScreen():
            self._window.showNormal()
            self._act_fullscreen.setChecked(False)
        else:
            self._window.showFullScreen()
            self._act_fullscreen.setChecked(True)

    def _on_view_grid(self):
        if self._window is None:
            return
        fn = getattr(self._window, "set_view_mode", None)
        if callable(fn):
            fn("grid")

    def _on_view_list(self):
        if self._window is None:
            return
        fn = getattr(self._window, "set_view_mode", None)
        if callable(fn):
            fn("list")

    def _on_sort(self, mode: str):
        if self._window is None:
            return
        fn = getattr(self._window, "set_sort_mode", None)
        if callable(fn):
            fn(mode)

    def _on_toggle_favorites_only(self, checked: bool):
        if self._window is None:
            return
        fn = getattr(self._window, "set_show_favorites_only", None)
        if callable(fn):
            fn(bool(checked))

    def _on_toggle_hidden(self, checked: bool):
        if self._window is None:
            return
        fn = getattr(self._window, "set_show_hidden_games", None)
        if callable(fn):
            fn(bool(checked))

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
