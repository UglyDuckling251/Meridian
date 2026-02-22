# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from meridian.core.config import Config, SYSTEM_NAMES


@dataclass(frozen=True)
class PublicRoom:
    room_name: str
    game_title: str
    system_id: str
    server_name: str
    host: str
    port: int
    players: int
    max_players: int
    ping_ms: int
    region: str
    passworded: bool = False

    @property
    def is_full(self) -> bool:
        return self.players >= self.max_players


class MultiplayerRoomBrowserDialog(QDialog):
    """Public netplay room browser with game/server filters."""

    HEADERS = [
        "Room",
        "Game",
        "System",
        "Server",
        "Players",
        "Ping",
        "Region",
        "Access",
    ]

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._cfg = config
        self._all_rooms: list[PublicRoom] = []
        self._selected_room: PublicRoom | None = None

        self.setWindowTitle("Public Room Browser")
        self.setMinimumSize(880, 480)
        self.resize(980, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        hint = QLabel(
            "Browse public lobbies by game or server. "
            "You can connect directly from the selected room."
        )
        hint.setWordWrap(True)
        hint.setObjectName("sectionLabel")
        root.addWidget(hint)

        filters = QFormLayout()
        filters.setSpacing(8)
        filters.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._filter_game = QLineEdit()
        self._filter_game.setPlaceholderText("Filter by game title...")
        self._filter_game.textChanged.connect(self._apply_filters)
        filters.addRow("Game:", self._filter_game)

        self._filter_server = QLineEdit()
        self._filter_server.setPlaceholderText("Filter by server name or host...")
        self._filter_server.textChanged.connect(self._apply_filters)
        filters.addRow("Server:", self._filter_server)

        self._filter_system = QComboBox()
        self._filter_system.currentTextChanged.connect(self._apply_filters)
        filters.addRow("System:", self._filter_system)

        self._filter_region = QComboBox()
        self._filter_region.addItems(["Any", "NA", "EU", "APAC", "SA", "AF", "ME"])
        pref_region = self._cfg.multiplayer_preferred_region or "Any"
        idx = self._filter_region.findText(pref_region)
        self._filter_region.setCurrentIndex(idx if idx >= 0 else 0)
        self._filter_region.currentTextChanged.connect(self._apply_filters)
        filters.addRow("Region:", self._filter_region)

        self._chk_include_full = QCheckBox("Include full rooms")
        self._chk_include_full.setChecked(self._cfg.multiplayer_show_full_rooms)
        self._chk_include_full.toggled.connect(self._apply_filters)
        filters.addRow("", self._chk_include_full)

        root.addLayout(filters)

        self._status = QLabel("")
        self._status.setObjectName("sectionLabel")
        root.addWidget(self._status)

        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(lambda _=None: self._join_selected())
        root.addWidget(self._table, 1)

        row = QHBoxLayout()
        row.addStretch()

        self._btn_settings = QPushButton("Multiplayer Settings...")
        self._btn_settings.clicked.connect(self._open_multiplayer_settings)
        row.addWidget(self._btn_settings)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(lambda: self._refresh_rooms(show_warning=True))
        row.addWidget(self._btn_refresh)

        self._btn_join = QPushButton("Join Selected")
        self._btn_join.setObjectName("primaryButton")
        self._btn_join.setEnabled(False)
        self._btn_join.clicked.connect(self._join_selected)
        row.addWidget(self._btn_join)

        self._btn_close = QPushButton("Close")
        self._btn_close.setObjectName("cancelButton")
        self._btn_close.clicked.connect(self.reject)
        row.addWidget(self._btn_close)

        root.addLayout(row)

        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(lambda: self._refresh_rooms(show_warning=False))
        interval_s = max(5, int(self._cfg.multiplayer_auto_refresh_seconds or 30))
        self._auto_timer.setInterval(interval_s * 1000)
        self._auto_timer.start()

        self._refresh_rooms(show_warning=True)

    def selected_room(self) -> PublicRoom | None:
        return self._selected_room

    def _open_multiplayer_settings(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "open_multiplayer_settings"):
            parent.open_multiplayer_settings()
            return
        QMessageBox.information(
            self,
            "Multiplayer Settings",
            "Open Edit > Settings > Networking > Multiplayer to adjust discovery settings.",
        )

    def _refresh_rooms(self, *, show_warning: bool) -> None:
        rooms, source, warning = _load_public_rooms(self._cfg)
        self._all_rooms = rooms
        self._status.setText(f"Source: {source}")
        if warning and show_warning:
            QMessageBox.information(self, "Room Browser", warning)
        self._rebuild_system_filter()
        self._apply_filters()

    def _rebuild_system_filter(self) -> None:
        current = self._filter_system.currentData()
        self._filter_system.blockSignals(True)
        self._filter_system.clear()
        self._filter_system.addItem("All systems", "")
        seen: set[str] = set()
        for room in self._all_rooms:
            if room.system_id in seen:
                continue
            seen.add(room.system_id)
            label = SYSTEM_NAMES.get(room.system_id, room.system_id.upper())
            self._filter_system.addItem(label, room.system_id)
        idx = self._filter_system.findData(current)
        self._filter_system.setCurrentIndex(idx if idx >= 0 else 0)
        self._filter_system.blockSignals(False)

    def _apply_filters(self) -> None:
        game_term = self._filter_game.text().strip().lower()
        server_term = self._filter_server.text().strip().lower()
        system_id = str(self._filter_system.currentData() or "")
        region = self._filter_region.currentText()
        include_full = self._chk_include_full.isChecked()

        rows: list[PublicRoom] = []
        for room in self._all_rooms:
            if game_term and game_term not in room.game_title.lower():
                continue
            if server_term:
                hay = f"{room.server_name} {room.host}".lower()
                if server_term not in hay:
                    continue
            if system_id and room.system_id != system_id:
                continue
            if region != "Any" and room.region != region:
                continue
            if not include_full and room.is_full:
                continue
            rows.append(room)

        self._table.setRowCount(len(rows))
        for r, room in enumerate(rows):
            system_name = SYSTEM_NAMES.get(room.system_id, room.system_id.upper())
            players_text = f"{room.players}/{room.max_players}"
            access = "Private" if room.passworded else "Public"
            values = [
                room.room_name,
                room.game_title,
                system_name,
                f"{room.server_name} ({room.host}:{room.port})",
                players_text,
                f"{room.ping_ms} ms",
                room.region,
                access,
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, room)
                self._table.setItem(r, c, item)

        self._table.resizeColumnsToContents()
        self._selected_room = None
        self._btn_join.setEnabled(False)
        self._status.setText(f"{self._status.text().split(' | ')[0]} | {len(rows)} room(s) shown")

    def _on_selection_changed(self) -> None:
        items = self._table.selectedItems()
        if not items:
            self._selected_room = None
            self._btn_join.setEnabled(False)
            return
        room = items[0].data(Qt.ItemDataRole.UserRole)
        if isinstance(room, PublicRoom):
            self._selected_room = room
            self._btn_join.setEnabled(True)
        else:
            self._selected_room = None
            self._btn_join.setEnabled(False)

    def _join_selected(self) -> None:
        if self._selected_room is None:
            return
        self.accept()


def _load_public_rooms(config: Config) -> tuple[list[PublicRoom], str, str]:
    url = (config.multiplayer_directory_url or "").strip()
    if not url:
        return _demo_public_rooms(), "Built-in public directory", ""

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Meridian/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as res:
            payload = json.loads(res.read().decode("utf-8", errors="replace"))
        data = payload.get("rooms", payload) if isinstance(payload, dict) else payload
        if not isinstance(data, list):
            raise ValueError("Expected a JSON list or object with 'rooms'.")
        rooms = [_room_from_dict(entry) for entry in data if isinstance(entry, dict)]
        rooms = [room for room in rooms if room is not None]
        if rooms:
            return rooms, f"Directory: {url}", ""
    except Exception as exc:
        return (
            _demo_public_rooms(),
            "Built-in public directory",
            f"Failed to load remote room directory.\nUsing built-in sample data.\n\n{exc}",
        )

    return _demo_public_rooms(), "Built-in public directory", ""


def _room_from_dict(raw: dict) -> PublicRoom | None:
    try:
        return PublicRoom(
            room_name=str(raw.get("room_name") or raw.get("name") or "Unnamed Room"),
            game_title=str(raw.get("game_title") or raw.get("game") or "Unknown Game"),
            system_id=str(raw.get("system_id") or "unknown"),
            server_name=str(raw.get("server_name") or raw.get("server") or "Unknown"),
            host=str(raw.get("host") or "0.0.0.0"),
            port=int(raw.get("port") or 0),
            players=int(raw.get("players") or 0),
            max_players=max(1, int(raw.get("max_players") or 1)),
            ping_ms=max(0, int(raw.get("ping_ms") or 0)),
            region=str(raw.get("region") or "Any"),
            passworded=bool(raw.get("passworded", False)),
        )
    except Exception:
        return None


def _demo_public_rooms() -> list[PublicRoom]:
    return [
        PublicRoom("Retro Nights", "Mario Kart 8 Deluxe", "switch", "Ariam #1", "104.21.55.12", 55000, 3, 12, 42, "NA"),
        PublicRoom("GoldenEye Weekend", "GoldenEye 007", "n64", "ClassicHub", "198.51.100.17", 55435, 4, 8, 58, "EU"),
        PublicRoom("Smash Club", "Super Smash Bros. Ultimate", "switch", "Ariam #2", "203.0.113.25", 55010, 12, 12, 25, "NA"),
        PublicRoom("Sonic Co-op", "Sonic 2", "genesis", "LegacyNet", "145.17.88.3", 50001, 2, 4, 64, "EU"),
        PublicRoom("Pokemon Link", "Pokemon Emerald", "gba", "PokeRelay", "77.91.100.9", 47000, 1, 4, 112, "APAC"),
        PublicRoom("SATURN Arena", "Saturn Bomberman", "saturn", "SaturnCore", "93.184.216.34", 62001, 6, 10, 74, "EU"),
        PublicRoom("Arcade Friday", "Metal Slug X", "mame", "Arcadia", "8.8.8.8", 38950, 2, 6, 87, "NA"),
        PublicRoom("Dream Race", "Sega Rally 2", "dreamcast", "DC-Live", "1.1.1.1", 50999, 5, 6, 49, "NA"),
        PublicRoom("Monster Hunter Hub", "Monster Hunter Freedom Unite", "psp", "PortableNet", "52.17.33.1", 44110, 2, 4, 95, "APAC"),
        PublicRoom("Battle City", "Bomberman", "nes", "Famiconnect", "203.0.113.144", 34500, 1, 2, 138, "SA"),
    ]
