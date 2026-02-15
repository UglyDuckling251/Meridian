"""
Settings dialog for Meridian  (Edit > Settings).

Layout
------
Left sidebar with main categories, right panel with subcategory tabs.
Each subcategory tab contains placeholder controls that will be wired
to real functionality as the project matures.

All changes are staged in a *copy* of the Config and only written to
disk when the user clicks Save.
"""

from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QCheckBox, QListWidget, QListWidgetItem, QStackedWidget,
    QTabWidget, QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
    QSlider, QFileDialog, QDialogButtonBox, QGroupBox, QMessageBox,
)

from meridian.core.config import (
    Config, EmulatorEntry, SystemEntry,
    KNOWN_SYSTEMS, SYSTEM_NAMES, emulators_for_system,
)
from meridian.ui.icons import icon as lucide_icon, pixmap as lucide_pixmap


# ======================================================================
# Category / subcategory definitions
# ======================================================================

_CATEGORIES: list[tuple[str, list[str]]] = [
    ("General",        ["General", "UI", "Hotkeys"]),
    ("Graphics",       ["Display", "Rendering"]),
    ("Performance",    ["System", "Cache"]),
    ("Input",          ["Controllers", "Keyboard"]),
    ("Emulators",      ["Installed", "Browse & Download", "Configuration"]),
    ("Networking",     ["Multiplayer", "Updates"]),
    ("Tools",          ["Scraper", "RetroAchievements", "File Management"]),
    ("Adv. Settings",  ["Debug", "Experimental"]),
]


# ======================================================================
# Main dialog
# ======================================================================

class SettingsDialog(QDialog):
    """Modal settings dialog with sidebar + subcategory tabs."""

    MIN_W, MIN_H = 740, 500

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(self.MIN_W, self.MIN_H)
        self.resize(800, 540)

        self._cfg = copy.deepcopy(config)
        self._build_ui()
        self._sidebar.setCurrentRow(0)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # -- Sidebar ---------------------------------------------------
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("settingsSidebar")
        self._sidebar.setFixedWidth(160)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for cat_name, _ in _CATEGORIES:
            item = QListWidgetItem(cat_name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._sidebar.addItem(item)

        self._sidebar.currentRowChanged.connect(self._on_category_changed)
        body.addWidget(self._sidebar)

        # -- Right panel (stacked pages) -------------------------------
        self._pages = QStackedWidget()
        self._pages.setObjectName("settingsPages")

        self._page_builders = {
            "General":       self._page_general,
            "Graphics":      self._page_graphics,
            "Performance":   self._page_performance,
            "Input":         self._page_input,
            "Emulators":     self._page_emulators,
            "Networking":    self._page_networking,
            "Tools":         self._page_tools,
            "Adv. Settings": self._page_advanced,
        }

        for cat_name, sub_tabs in _CATEGORIES:
            page = self._make_page(cat_name, sub_tabs)
            self._pages.addWidget(page)

        body.addWidget(self._pages, 1)
        root.addLayout(body, 1)

        # -- Bottom button bar -----------------------------------------
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(12, 8, 12, 10)
        btn_bar.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(btn_cancel)

        btn_save = QPushButton("Save")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._on_save)
        btn_bar.addWidget(btn_save)

        root.addLayout(btn_bar)

    def _make_page(self, cat_name: str, sub_tabs: list[str]) -> QWidget:
        """Build one right-side page with subcategory tabs."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setObjectName("subTabs")
        builder_fn = self._page_builders.get(cat_name)
        for sub_name in sub_tabs:
            content = builder_fn(sub_name) if builder_fn else _placeholder(sub_name)
            tabs.addTab(content, sub_name)

        layout.addWidget(tabs)
        return page

    # ------------------------------------------------------------------
    # Sidebar slot
    # ------------------------------------------------------------------

    def _on_category_changed(self, index: int):
        self._pages.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Page builders — each returns content widget for a subcategory tab
    # ------------------------------------------------------------------

    # -- General -------------------------------------------------------

    def _page_general(self, sub: str) -> QWidget:
        if sub == "General":
            return self._general_general()
        if sub == "UI":
            return self._general_ui()
        if sub == "Hotkeys":
            return self._general_hotkeys()
        return _placeholder(sub)

    def _general_general(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Startup")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        self._chk_maximized = QCheckBox("Start maximized")
        self._chk_maximized.setChecked(self._cfg.start_maximized)
        g.addWidget(self._chk_maximized)
        self._chk_confirm_exit = QCheckBox("Confirm before exit")
        self._chk_confirm_exit.setChecked(self._cfg.confirm_on_exit)
        g.addWidget(self._chk_confirm_exit)
        layout.addWidget(grp)

        grp2 = QGroupBox("Language")
        g2 = QHBoxLayout(grp2)
        lbl = QLabel("Interface language:")
        combo = QComboBox()
        combo.addItem("English")
        combo.setEnabled(False)
        g2.addWidget(lbl)
        g2.addWidget(combo, 1)
        layout.addWidget(grp2)

        layout.addStretch()
        return w

    def _general_ui(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Appearance")
        g = QVBoxLayout(grp)
        g.setSpacing(8)

        row = QHBoxLayout()
        row.addWidget(QLabel("Theme:"))
        combo = QComboBox()
        combo.addItems(["Meridian Dark"])
        combo.setEnabled(False)
        row.addWidget(combo, 1)
        g.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("UI Scale:"))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(80, 150)
        slider.setValue(100)
        slider.setEnabled(False)
        row2.addWidget(slider, 1)
        lbl_pct = QLabel("100%")
        lbl_pct.setFixedWidth(40)
        row2.addWidget(lbl_pct)
        g.addLayout(row2)

        layout.addWidget(grp)

        grp2 = QGroupBox("Game Display")
        g2 = QVBoxLayout(grp2)
        g2.setSpacing(8)
        g2.addWidget(QCheckBox("Show game titles under cover art"))
        g2.addWidget(QCheckBox("Show platform badges"))
        for cb in grp2.findChildren(QCheckBox):
            cb.setChecked(True)
            cb.setEnabled(False)
        layout.addWidget(grp2)

        layout.addStretch()
        return w

    def _general_hotkeys(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Global Hotkeys")
        g = QFormLayout(grp)
        g.setSpacing(8)
        for label, default in [
            ("Toggle Fullscreen:", "F11"),
            ("Open Settings:", "Ctrl+,"),
            ("Search:", "Ctrl+K"),
            ("Quick Launch:", "Enter"),
        ]:
            le = QLineEdit(default)
            le.setReadOnly(True)
            le.setEnabled(False)
            g.addRow(label, le)
        layout.addWidget(grp)

        layout.addStretch()
        return w

    # -- Graphics ------------------------------------------------------

    def _page_graphics(self, sub: str) -> QWidget:
        if sub == "Display":
            return self._graphics_display()
        if sub == "Rendering":
            return self._graphics_rendering()
        return _placeholder(sub)

    def _graphics_display(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Window")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Remember window size and position"))
        g.addWidget(_disabled_check("Use borderless window in fullscreen"))
        layout.addWidget(grp)

        grp2 = QGroupBox("Resolution")
        g2 = QFormLayout(grp2)
        g2.setSpacing(8)
        combo = QComboBox()
        combo.addItems(["Native", "720p", "1080p", "1440p", "4K"])
        combo.setEnabled(False)
        g2.addRow("Internal resolution:", combo)
        layout.addWidget(grp2)

        layout.addStretch()
        return w

    def _graphics_rendering(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Rendering")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Enable VSync"))
        g.addWidget(_disabled_check("Use GPU-accelerated UI rendering"))
        layout.addWidget(grp)

        layout.addStretch()
        return w

    # -- Performance ---------------------------------------------------

    def _page_performance(self, sub: str) -> QWidget:
        if sub == "System":
            return self._perf_system()
        if sub == "Cache":
            return self._perf_cache()
        return _placeholder(sub)

    def _perf_system(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Resource Usage")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Limit background CPU usage"))
        g.addWidget(_disabled_check("Reduce animations"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Concurrent scan threads:"))
        spin = QSpinBox()
        spin.setRange(1, 16)
        spin.setValue(4)
        spin.setEnabled(False)
        row.addWidget(spin)
        row.addStretch()
        g.addLayout(row)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    def _perf_cache(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Metadata Cache")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Cache box art thumbnails"))
        g.addWidget(_disabled_check("Cache scraped metadata locally"))

        btn = QPushButton("Clear Cache")
        btn.setEnabled(False)
        btn.setFixedWidth(120)
        g.addWidget(btn)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    # -- Input ---------------------------------------------------------

    def _page_input(self, sub: str) -> QWidget:
        if sub == "Controllers":
            return self._input_controllers()
        if sub == "Keyboard":
            return self._input_keyboard()
        return _placeholder(sub)

    def _input_controllers(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # -- Options ---------------------------------------------------
        grp_opts = QGroupBox("Options")
        g_opts = QVBoxLayout(grp_opts)
        g_opts.setSpacing(8)
        g_opts.addWidget(_disabled_check("Enable gamepad navigation"))
        g_opts.addWidget(_disabled_check("Vibration feedback"))
        layout.addWidget(grp_opts)

        # -- Player slots (1-10) ---------------------------------------
        lbl = QLabel("Player Assignments")
        lbl.setObjectName("sectionLabel")
        layout.addWidget(lbl)

        detected = _detect_controllers()

        from PySide6.QtWidgets import QScrollArea
        scroll_content = QWidget()
        slots_layout = QVBoxLayout(scroll_content)
        slots_layout.setContentsMargins(0, 0, 0, 0)
        slots_layout.setSpacing(4)

        for i in range(1, 11):
            slot = self._make_player_slot(i, detected)
            slots_layout.addWidget(slot)

        slots_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        return w

    def _make_player_slot(self, number: int, detected: list[str]) -> QWidget:
        """Build one player row: checkbox, controller type, input device."""
        slot = QWidget()
        slot.setObjectName("playerSlot")
        row = QHBoxLayout(slot)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(8)

        chk = QCheckBox()
        chk.setToolTip(f"Enable Player {number}")
        row.addWidget(chk)

        lbl = QLabel(f"P{number}")
        lbl.setFixedWidth(24)
        lbl.setObjectName("sectionLabel")
        row.addWidget(lbl)

        type_combo = QComboBox()
        type_combo.addItems([
            "Gamepad",
            "Pro Controller",
            "Wii Remote",
            "Wii Remote + Nunchuk",
            "Classic Controller",
            "DualShock",
            "DualSense",
            "Xbox Controller",
            "Joy-Con (L+R)",
            "Joy-Con (Single)",
            "Fight Stick",
            "Steering Wheel",
            "Custom",
        ])
        type_combo.setEnabled(False)
        type_combo.setMinimumWidth(150)
        row.addWidget(type_combo)

        device_combo = QComboBox()
        device_combo.addItem("None")
        device_combo.addItem("Keyboard + Mouse")
        device_combo.addItem("Any Available")
        for name in detected:
            device_combo.addItem(name)
        device_combo.setEnabled(False)
        row.addWidget(device_combo, 1)

        return slot

    def _input_keyboard(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Keyboard Navigation")
        g = QFormLayout(grp)
        g.setSpacing(8)
        for label, default in [
            ("Navigate Up:", "Up / W"),
            ("Navigate Down:", "Down / S"),
            ("Select:", "Enter"),
            ("Back:", "Escape"),
        ]:
            le = QLineEdit(default)
            le.setReadOnly(True)
            le.setEnabled(False)
            g.addRow(label, le)
        layout.addWidget(grp)

        layout.addStretch()
        return w

    # -- Emulators -----------------------------------------------------

    def _page_emulators(self, sub: str) -> QWidget:
        if sub == "Installed":
            return self._emu_installed()
        if sub == "Browse & Download":
            return self._emu_browse()
        if sub == "Configuration":
            return self._emu_config()
        return _placeholder(sub)

    def _emu_installed(self) -> QWidget:
        """Shows installed emulators with settings/delete/update buttons."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        lbl = QLabel("Installed emulators:")
        lbl.setObjectName("sectionLabel")
        layout.addWidget(lbl)

        from PySide6.QtWidgets import QScrollArea

        self._installed_content = QWidget()
        self._installed_layout = QVBoxLayout(self._installed_content)
        self._installed_layout.setContentsMargins(0, 0, 0, 0)
        self._installed_layout.setSpacing(4)
        self._installed_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._installed_content)
        layout.addWidget(scroll, 1)

        # Add manually button
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_add = QPushButton("Add Manually...")
        btn_add.clicked.connect(self._on_add_emulator)
        btn_row.addWidget(btn_add)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Populate existing installed emulators
        self._installed_cards: list[QWidget] = []
        for entry in self._cfg.emulators:
            self._insert_installed_card(entry)

        if not self._cfg.emulators:
            empty = QLabel("No emulators installed. Use Browse & Download or Add Manually.")
            empty.setObjectName("sectionLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            idx = self._installed_layout.count() - 1
            self._installed_layout.insertWidget(idx, empty)

        return w

    def _insert_installed_card(self, entry: EmulatorEntry):
        """One installed emulator card: name, path, cog/delete/update icons."""
        card = QWidget()
        card.setObjectName("playerSlot")
        row = QHBoxLayout(card)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)

        # Installed indicator
        check_icon = QLabel()
        check_icon.setPixmap(lucide_pixmap("circle-check", 16, "#3A8A72"))
        check_icon.setFixedSize(20, 20)
        row.addWidget(check_icon)

        # Name + path
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(f"<b>{entry.display_name()}</b>")
        info.addWidget(name_lbl)
        if entry.path:
            path_lbl = QLabel(entry.path)
            path_lbl.setObjectName("sectionLabel")
            info.addWidget(path_lbl)
        row.addLayout(info, 1)

        # Action buttons (icon-only)
        btn_settings = QPushButton()
        btn_settings.setIcon(lucide_icon("settings", 14, "#CDD2DA"))
        btn_settings.setFixedSize(28, 28)
        btn_settings.setToolTip("Emulator settings")
        btn_settings.clicked.connect(lambda _, e=entry: self._on_emu_settings(e))
        row.addWidget(btn_settings)

        btn_update = QPushButton()
        btn_update.setIcon(lucide_icon("refresh-cw", 14, "#CDD2DA"))
        btn_update.setFixedSize(28, 28)
        btn_update.setToolTip("Check for updates")
        btn_update.setEnabled(False)
        row.addWidget(btn_update)

        btn_delete = QPushButton()
        btn_delete.setIcon(lucide_icon("trash-2", 14, "#CDD2DA"))
        btn_delete.setFixedSize(28, 28)
        btn_delete.setToolTip("Remove emulator")
        btn_delete.clicked.connect(
            lambda _, c=card, e=entry: self._on_delete_installed(c, e)
        )
        row.addWidget(btn_delete)

        idx = self._installed_layout.count() - 1
        self._installed_layout.insertWidget(idx, card)
        self._installed_cards.append(card)

    def _on_emu_settings(self, entry: EmulatorEntry):
        """Open per-emulator settings dialog."""
        dlg = _EmulatorSettingsDialog(entry, self._cfg, parent=self)
        dlg.exec()

    def _on_delete_installed(self, card: QWidget, entry: EmulatorEntry):
        if entry in self._cfg.emulators:
            self._cfg.emulators.remove(entry)
        if card in self._installed_cards:
            self._installed_cards.remove(card)
        card.setParent(None)
        card.deleteLater()

    def _emu_browse(self) -> QWidget:
        """Browse emulators by console with download buttons."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Filter
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_row.addWidget(QLabel("Filter by system:"))
        self._browse_filter = QComboBox()
        self._browse_filter.addItem("All Systems", "")
        for sid, name, _ in KNOWN_SYSTEMS:
            self._browse_filter.addItem(name, sid)
        self._browse_filter.currentIndexChanged.connect(self._on_browse_filter)
        filter_row.addWidget(self._browse_filter, 1)
        layout.addLayout(filter_row)

        # Catalog scroll area
        from PySide6.QtWidgets import QScrollArea

        self._browse_content = QWidget()
        self._browse_layout = QVBoxLayout(self._browse_content)
        self._browse_layout.setContentsMargins(0, 0, 0, 0)
        self._browse_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._browse_content)
        layout.addWidget(scroll, 1)

        self._populate_browse_catalog("")
        return w

    def _populate_browse_catalog(self, filter_system: str):
        """Rebuild the catalog list, optionally filtered to one system."""
        # Clear existing
        while self._browse_layout.count():
            item = self._browse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        installed_names = {e.name for e in self._cfg.emulators}

        from meridian.core.config import EMULATOR_CATALOG
        for emu_name, url, systems in EMULATOR_CATALOG:
            if filter_system and filter_system not in systems:
                continue

            card = QWidget()
            card.setObjectName("playerSlot")
            row = QHBoxLayout(card)
            row.setContentsMargins(10, 6, 10, 6)
            row.setSpacing(10)

            # Info
            info = QVBoxLayout()
            info.setSpacing(1)
            name_lbl = QLabel(f"<b>{emu_name}</b>")
            info.addWidget(name_lbl)

            system_names = [SYSTEM_NAMES.get(s, s) for s in systems[:5]]
            suffix = f" +{len(systems) - 5} more" if len(systems) > 5 else ""
            platforms = QLabel(", ".join(system_names) + suffix)
            platforms.setObjectName("sectionLabel")
            platforms.setWordWrap(True)
            info.addWidget(platforms)

            row.addLayout(info, 1)

            if emu_name in installed_names:
                installed_lbl = QLabel()
                installed_lbl.setPixmap(lucide_pixmap("circle-check", 16, "#3A8A72"))
                installed_lbl.setToolTip("Installed")
                row.addWidget(installed_lbl)
            else:
                btn_dl = QPushButton()
                btn_dl.setIcon(lucide_icon("download", 14, "#CDD2DA"))
                btn_dl.setFixedSize(28, 28)
                btn_dl.setToolTip(f"Download {emu_name}")
                btn_dl.setEnabled(False)
                row.addWidget(btn_dl)

            self._browse_layout.addWidget(card)

        self._browse_layout.addStretch()

    def _on_browse_filter(self, index: int):
        sid = self._browse_filter.currentData() or ""
        self._populate_browse_catalog(sid)

    def _emu_config(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Defaults")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Auto-detect installed emulators"))
        g.addWidget(_disabled_check("Pass fullscreen flag to emulators"))
        g.addWidget(_disabled_check("Close Meridian while emulator is running"))
        layout.addWidget(grp)

        grp2 = QGroupBox("Launch")
        g2 = QVBoxLayout(grp2)
        g2.setSpacing(8)
        g2.addWidget(_disabled_check("Confirm before launching game"))
        g2.addWidget(_disabled_check("Track play time"))
        layout.addWidget(grp2)

        layout.addStretch()
        return w

    # -- Networking ----------------------------------------------------

    def _page_networking(self, sub: str) -> QWidget:
        if sub == "Multiplayer":
            return self._net_multiplayer()
        if sub == "Updates":
            return self._net_updates()
        return _placeholder(sub)

    def _net_multiplayer(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Netplay")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Enable multiplayer features"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Username:"))
        le = QLineEdit()
        le.setPlaceholderText("Player")
        le.setEnabled(False)
        row.addWidget(le, 1)
        g.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Default port:"))
        spin = QSpinBox()
        spin.setRange(1024, 65535)
        spin.setValue(55435)
        spin.setEnabled(False)
        row2.addWidget(spin)
        row2.addStretch()
        g.addLayout(row2)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    def _net_updates(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Updates")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Check for updates on startup"))
        g.addWidget(_disabled_check("Include pre-release versions"))

        btn = QPushButton("Check Now")
        btn.setEnabled(False)
        btn.setFixedWidth(120)
        g.addWidget(btn)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    # -- Tools ---------------------------------------------------------

    def _page_tools(self, sub: str) -> QWidget:
        if sub == "Scraper":
            return self._tools_scraper()
        if sub == "RetroAchievements":
            return self._tools_retroachievements()
        if sub == "File Management":
            return self._tools_files()
        return _placeholder(sub)

    def _tools_scraper(self) -> QWidget:
        """Unified scraper config — one source at a time, no overlap."""
        w = QWidget()
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # -- Active source selector ------------------------------------
        grp_src = QGroupBox("Scraper Source")
        g_src = QVBoxLayout(grp_src)
        g_src.setSpacing(8)

        hint = QLabel(
            "Select one source for all metadata and artwork. "
            "Only the active source is queried — no overlap or duplication."
        )
        hint.setObjectName("sectionLabel")
        hint.setWordWrap(True)
        g_src.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("Active source:"))
        combo = QComboBox()
        combo.addItems([
            "ScreenScraper",
            "TheGamesDB",
            "IGDB",
            "LaunchBox DB",
            "MobyGames",
            "OpenRetro",
        ])
        combo.setEnabled(False)
        row.addWidget(combo, 1)
        g_src.addLayout(row)

        layout.addWidget(grp_src)

        # -- API credentials -------------------------------------------
        grp_api = QGroupBox("API Credentials (for active source)")
        g_api = QFormLayout(grp_api)
        g_api.setSpacing(8)

        le_user = QLineEdit()
        le_user.setPlaceholderText("Username (if required)")
        le_user.setEnabled(False)
        g_api.addRow("Username:", le_user)

        le_key = QLineEdit()
        le_key.setPlaceholderText("API key")
        le_key.setEchoMode(QLineEdit.EchoMode.Password)
        le_key.setEnabled(False)
        g_api.addRow("API Key:", le_key)

        btn_row = QHBoxLayout()
        btn_test = QPushButton("Test Connection")
        btn_test.setEnabled(False)
        btn_row.addWidget(btn_test)
        btn_row.addStretch()
        g_api.addRow("", btn_row)

        layout.addWidget(grp_api)

        # -- What to fetch ---------------------------------------------
        grp_content = QGroupBox("Content to Fetch")
        g_c = QVBoxLayout(grp_content)
        g_c.setSpacing(8)
        g_c.addWidget(_disabled_check("Game title"))
        g_c.addWidget(_disabled_check("Description / summary"))
        g_c.addWidget(_disabled_check("Genre, release date, players"))
        g_c.addWidget(_disabled_check("Developer / publisher"))
        g_c.addWidget(_disabled_check("Rating"))
        layout.addWidget(grp_content)

        # -- Artwork to fetch ------------------------------------------
        grp_art = QGroupBox("Artwork to Fetch")
        g_a = QVBoxLayout(grp_art)
        g_a.setSpacing(8)
        g_a.addWidget(_disabled_check("Front box art"))
        g_a.addWidget(_disabled_check("Back box art"))
        g_a.addWidget(_disabled_check("In-game screenshots"))
        g_a.addWidget(_disabled_check("Title screen"))
        g_a.addWidget(_disabled_check("Fan art / banners"))
        g_a.addWidget(_disabled_check("Video snaps"))

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Max image resolution:"))
        combo_res = QComboBox()
        combo_res.addItems(["Original", "1080p", "720p", "480p"])
        combo_res.setEnabled(False)
        row2.addWidget(combo_res, 1)
        g_a.addLayout(row2)

        layout.addWidget(grp_art)

        # -- Behaviour -------------------------------------------------
        grp_beh = QGroupBox("Behaviour")
        g_b = QVBoxLayout(grp_beh)
        g_b.setSpacing(8)
        g_b.addWidget(_disabled_check("Auto-scrape when new ROMs are found"))
        g_b.addWidget(_disabled_check("Overwrite existing metadata"))
        g_b.addWidget(_disabled_check("Prefer local files over remote"))
        g_b.addWidget(_disabled_check("Hash ROMs for accurate matching (CRC32)"))
        layout.addWidget(grp_beh)

        layout.addStretch()

        # Wrap in scroll area
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_content)

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return outer

    def _tools_retroachievements(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("RetroAchievements Account")
        g = QFormLayout(grp)
        g.setSpacing(8)

        le_user = QLineEdit()
        le_user.setPlaceholderText("RetroAchievements username")
        le_user.setEnabled(False)
        g.addRow("Username:", le_user)

        le_key = QLineEdit()
        le_key.setPlaceholderText("API key")
        le_key.setEchoMode(QLineEdit.EchoMode.Password)
        le_key.setEnabled(False)
        g.addRow("API Key:", le_key)

        layout.addWidget(grp)

        grp2 = QGroupBox("Integration")
        g2 = QVBoxLayout(grp2)
        g2.setSpacing(8)
        g2.addWidget(_disabled_check("Enable RetroAchievements"))
        g2.addWidget(_disabled_check("Show achievement notifications"))
        g2.addWidget(_disabled_check("Hardcore mode"))
        g2.addWidget(_disabled_check("Display achievement badges in game grid"))
        layout.addWidget(grp2)

        grp3 = QGroupBox("Data")
        g3 = QVBoxLayout(grp3)
        g3.setSpacing(8)
        g3.addWidget(_disabled_check("Sync progress on launch"))
        g3.addWidget(_disabled_check("Cache achievement icons locally"))

        row = QHBoxLayout()
        btn = QPushButton("Test Connection")
        btn.setEnabled(False)
        row.addWidget(btn)
        row.addStretch()
        g3.addLayout(row)

        layout.addWidget(grp3)
        layout.addStretch()
        return w

    def _tools_files(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("File Management")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Verify ROM integrity on scan"))
        g.addWidget(_disabled_check("Remove missing ROMs from library"))
        g.addWidget(_disabled_check("Hash ROMs for scraper matching (CRC32)"))

        row = QHBoxLayout()
        btn_open = QPushButton("Open App Data Directory")
        btn_open.setEnabled(False)
        row.addWidget(btn_open)
        row.addStretch()
        g.addLayout(row)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    # -- Advanced ------------------------------------------------------

    def _page_advanced(self, sub: str) -> QWidget:
        if sub == "Debug":
            return self._adv_debug()
        if sub == "Experimental":
            return self._adv_experimental()
        return _placeholder(sub)

    def _adv_debug(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Diagnostics")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("Enable debug logging"))
        g.addWidget(_disabled_check("Show FPS counter"))
        g.addWidget(_disabled_check("Log emulator stdout"))

        row = QHBoxLayout()
        btn = QPushButton("Open Log File")
        btn.setEnabled(False)
        row.addWidget(btn)
        row.addStretch()
        g.addLayout(row)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    def _adv_experimental(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        grp = QGroupBox("Experimental Features")
        g = QVBoxLayout(grp)
        g.setSpacing(8)
        g.addWidget(_disabled_check("GPU-accelerated game grid"))
        g.addWidget(_disabled_check("Predictive ROM scanning"))
        g.addWidget(_disabled_check("Cloud save sync"))

        lbl = QLabel("These features are unstable and may cause issues.")
        lbl.setObjectName("sectionLabel")
        g.addWidget(lbl)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    # ------------------------------------------------------------------
    # Emulator callbacks
    # ------------------------------------------------------------------

    def _on_add_emulator(self):
        dlg = _EmulatorEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            entry = dlg.result_entry()
            self._cfg.add_emulator(entry)
            self._emu_list.addItem(f"{entry.display_name()}  —  {entry.path}")

    def _on_edit_emulator(self):
        row = self._emu_list.currentRow()
        if row < 0:
            return
        entry = self._cfg.emulators[row]
        dlg = _EmulatorEditDialog(entry=entry, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new = dlg.result_entry()
            self._cfg.emulators[row] = new
            self._emu_list.item(row).setText(
                f"{new.display_name()}  —  {new.path}" if new.path else new.display_name()
            )

    def _on_remove_emulator(self):
        row = self._emu_list.currentRow()
        if row >= 0:
            self._cfg.remove_emulator(row)
            self._emu_list.takeItem(row)

    # ------------------------------------------------------------------
    # Save / cancel
    # ------------------------------------------------------------------

    def _on_save(self):
        self._cfg.start_maximized = self._chk_maximized.isChecked()
        self._cfg.confirm_on_exit = self._chk_confirm_exit.isChecked()
        self._cfg.save()
        self.accept()

    def saved_config(self) -> Config:
        return self._cfg


# ======================================================================
# Emulator add / edit sub-dialog
# ======================================================================

class _EmulatorEditDialog(QDialog):
    """Small modal for adding or editing a single emulator entry."""

    def __init__(self, entry: EmulatorEntry | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Emulator" if entry else "Add Emulator")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self._txt_name = QLineEdit()
        self._txt_name.setPlaceholderText("e.g. RetroArch, Dolphin, PCSX2")
        form.addRow("Name:", self._txt_name)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._txt_path = QLineEdit()
        self._txt_path.setPlaceholderText("Path to emulator executable")
        path_row.addWidget(self._txt_path, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self._on_browse)
        path_row.addWidget(btn_browse)
        form.addRow("Executable:", path_row)

        self._txt_args = QLineEdit()
        self._txt_args.setPlaceholderText('e.g. -L "cores/bsnes.dll" "{rom}"')
        form.addRow("Arguments:", self._txt_args)

        hint = QLabel(
            '<span style="color:#6E7A8A; font-size:8pt;">'
            "Use <b>{rom}</b> as a placeholder for the ROM file path.</span>"
        )
        form.addRow("", hint)
        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        if entry:
            self._txt_name.setText(entry.name)
            self._txt_path.setText(entry.path)
            self._txt_args.setText(entry.args)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Emulator Executable",
            "", "Executables (*.exe);;All Files (*)",
        )
        if path:
            self._txt_path.setText(path)

    def _on_ok(self):
        if not self._txt_name.text().strip():
            QMessageBox.warning(self, "Validation", "Emulator name is required.")
            self._txt_name.setFocus()
            return
        if not self._txt_path.text().strip():
            QMessageBox.warning(self, "Validation", "Executable path is required.")
            self._txt_path.setFocus()
            return
        self.accept()

    def result_entry(self) -> EmulatorEntry:
        return EmulatorEntry(
            name=self._txt_name.text().strip(),
            path=self._txt_path.text().strip(),
            args=self._txt_args.text().strip() or '"{rom}"',
        )


# ======================================================================
# Per-emulator settings dialog  (cog icon)
# ======================================================================

class _EmulatorSettingsDialog(QDialog):
    """Settings for one specific installed emulator."""

    def __init__(self, entry: EmulatorEntry, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{entry.display_name()} — Settings")
        self.setMinimumSize(480, 380)

        self._entry = entry
        self._cfg = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # -- Paths -----------------------------------------------------
        grp_paths = QGroupBox("Paths")
        g_p = QFormLayout(grp_paths)
        g_p.setSpacing(8)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._txt_exe = QLineEdit(entry.path)
        self._txt_exe.setPlaceholderText("Path to executable")
        path_row.addWidget(self._txt_exe, 1)
        btn_b = QPushButton("Browse...")
        btn_b.setFixedWidth(80)
        btn_b.clicked.connect(self._on_browse_exe)
        path_row.addWidget(btn_b)
        g_p.addRow("Executable:", path_row)

        self._txt_args = QLineEdit(entry.args)
        self._txt_args.setPlaceholderText('"{rom}"')
        g_p.addRow("Launch args:", self._txt_args)

        rom_row = QHBoxLayout()
        rom_row.setSpacing(6)
        self._txt_rom_dir = QLineEdit()
        self._txt_rom_dir.setPlaceholderText("Default ROM directory for this emulator (optional)")
        self._txt_rom_dir.setEnabled(False)
        rom_row.addWidget(self._txt_rom_dir, 1)
        btn_b2 = QPushButton("Browse...")
        btn_b2.setFixedWidth(80)
        btn_b2.setEnabled(False)
        rom_row.addWidget(btn_b2)
        g_p.addRow("ROM directory:", rom_row)

        layout.addWidget(grp_paths)

        # -- Graphics --------------------------------------------------
        grp_gfx = QGroupBox("Graphics")
        g_g = QVBoxLayout(grp_gfx)
        g_g.setSpacing(8)
        g_g.addWidget(_disabled_check("Pass fullscreen flag on launch"))
        g_g.addWidget(_disabled_check("Use exclusive fullscreen"))

        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Resolution override:"))
        combo = QComboBox()
        combo.addItems(["Default", "720p", "1080p", "1440p", "4K"])
        combo.setEnabled(False)
        res_row.addWidget(combo, 1)
        g_g.addLayout(res_row)

        layout.addWidget(grp_gfx)

        # -- Behaviour -------------------------------------------------
        grp_beh = QGroupBox("Behaviour")
        g_b = QVBoxLayout(grp_beh)
        g_b.setSpacing(8)
        g_b.addWidget(_disabled_check("Close Meridian while running"))
        g_b.addWidget(_disabled_check("Auto-save state on exit"))
        layout.addWidget(grp_beh)

        layout.addStretch()

        # -- Buttons ---------------------------------------------------
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
        )
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Emulator Executable",
            "", "Executables (*.exe);;All Files (*)",
        )
        if path:
            self._txt_exe.setText(path)

    def _on_save(self):
        self._entry.path = self._txt_exe.text().strip()
        self._entry.args = self._txt_args.text().strip() or '"{rom}"'
        self.accept()


# ======================================================================
# Helpers
# ======================================================================

def _placeholder(name: str) -> QWidget:
    """Fallback empty tab."""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(20, 20, 20, 20)
    lbl = QLabel(f"{name} settings will appear here.")
    lbl.setObjectName("sectionLabel")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl)
    return w


def _disabled_check(text: str, checked: bool = False) -> QCheckBox:
    """Create a disabled checkbox placeholder."""
    cb = QCheckBox(text)
    cb.setChecked(checked)
    cb.setEnabled(False)
    return cb


def _detect_controllers() -> list[str]:
    """Return names of currently connected game controllers via pygame."""
    try:
        import pygame
        pygame.joystick.init()
        names = []
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            names.append(joy.get_name())
        pygame.joystick.quit()
        return names
    except Exception:
        return []
