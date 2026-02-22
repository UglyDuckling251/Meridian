"""Windows DirectInput device enumeration via ctypes.

Provides :func:`enumerate_devices` which returns every game controller
visible to DirectInput8, including each device's instance GUID, product
GUID, and display name.  On non-Windows platforms the function returns
an empty list.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import NamedTuple

log = logging.getLogger(__name__)


class DIDevice(NamedTuple):
    instance_guid: str   # e.g. "B7020510-997D-11F0-8001-444553540000"
    product_guid: str    # e.g. "0CE6054C-0000-0000-0000-504944564944"
    name: str            # e.g. "DualSense Wireless Controller"


def enumerate_devices() -> list[DIDevice]:
    """Return all DirectInput game controllers currently connected."""
    if sys.platform != "win32":
        return []
    try:
        return _enumerate_di8()
    except Exception:
        log.debug("DirectInput enumeration failed", exc_info=True)
        return []


_NUMBERED_SUFFIX_RE = re.compile(r"\s+\[#(\d+)\]\s*$")


def _parse_label(device_name: str) -> tuple[str, int | None]:
    """Return ``(base_name, ordinal)`` for labels like ``Name [#2]``."""
    raw = device_name.strip()
    m = _NUMBERED_SUFFIX_RE.search(raw)
    if not m:
        return raw, None
    try:
        ordinal = int(m.group(1))
    except ValueError:
        ordinal = None
    return raw[:m.start()].strip(), ordinal


def find_device(device_name: str, preferred_index: int | None = None) -> DIDevice | None:
    """Find a DirectInput device by UI label and optional index.

    Supports numbered labels (e.g. ``DualSense Wireless Controller [#2]``)
    emitted by Meridian's device picker when duplicate names are present.
    """
    base_name, ordinal = _parse_label(device_name)
    name_lower = base_name.lower().strip()
    devices = enumerate_devices()

    # Numbered duplicate label from UI: choose the Nth same-name device.
    if ordinal is not None and ordinal > 0:
        same_name = [
            d for d in devices
            if d.name.lower().strip() == name_lower
        ]
        if ordinal <= len(same_name):
            return same_name[ordinal - 1]

    # Device index from InputManager (stable in current session).
    if isinstance(preferred_index, int) and 0 <= preferred_index < len(devices):
        candidate = devices[preferred_index]
        cand_name = candidate.name.lower().strip()
        if cand_name == name_lower or name_lower in cand_name:
            return candidate

    for dev in devices:
        if dev.name.lower().strip() == name_lower:
            return dev
    for dev in devices:
        if name_lower in dev.name.lower():
            return dev
    return None


# ---------------------------------------------------------------------------
# DirectInput8 COM enumeration via ctypes
# ---------------------------------------------------------------------------

def _enumerate_di8() -> list[DIDevice]:
    import ctypes
    from ctypes import wintypes, POINTER, Structure, c_void_p

    class GUID(Structure):
        _fields_ = [
            ("Data1", ctypes.c_ulong),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_ubyte * 8),
        ]

        def __str__(self) -> str:
            d4 = bytes(self.Data4)
            return (
                f"{self.Data1:08X}-{self.Data2:04X}-{self.Data3:04X}-"
                f"{d4[0]:02X}{d4[1]:02X}-"
                f"{d4[2]:02X}{d4[3]:02X}{d4[4]:02X}{d4[5]:02X}"
                f"{d4[6]:02X}{d4[7]:02X}"
            )

    class DIDEVICEINSTANCEW(Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("guidInstance", GUID),
            ("guidProduct", GUID),
            ("dwDevType", wintypes.DWORD),
            ("tszInstanceName", wintypes.WCHAR * 260),
            ("tszProductName", wintypes.WCHAR * 260),
            ("guidFFDriver", GUID),
            ("wUsagePage", wintypes.WORD),
            ("wUsage", wintypes.WORD),
        ]

    DI8DEVCLASS_GAMECTRL = 4
    DIEDFL_ATTACHEDONLY = 0x00000001

    LPDIENUMDEVICESCALLBACKW = ctypes.WINFUNCTYPE(
        wintypes.BOOL, POINTER(DIDEVICEINSTANCEW), c_void_p,
    )

    devices: list[DIDevice] = []

    @LPDIENUMDEVICESCALLBACKW
    def _callback(lpddi, _pv):
        dev = lpddi.contents
        devices.append(DIDevice(
            instance_guid=str(dev.guidInstance),
            product_guid=str(dev.guidProduct),
            name=dev.tszProductName,
        ))
        return 1  # DIENUM_CONTINUE

    iid = GUID(
        0xBF798031, 0x483A, 0x4DA2,
        (ctypes.c_ubyte * 8)(0xAA, 0x99, 0x5D, 0x64, 0xED, 0x36, 0x97, 0x00),
    )

    kernel32 = ctypes.windll.kernel32
    kernel32.GetModuleHandleW.restype = c_void_p
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    hinst = kernel32.GetModuleHandleW(None)

    dinput8 = ctypes.WinDLL("dinput8.dll")
    dinput8.DirectInput8Create.restype = wintypes.LONG
    dinput8.DirectInput8Create.argtypes = [
        c_void_p, wintypes.DWORD, c_void_p, c_void_p, c_void_p,
    ]

    di = c_void_p()
    hr = dinput8.DirectInput8Create(
        hinst, 0x0800, ctypes.addressof(iid), ctypes.addressof(di), None,
    )
    if hr != 0:
        log.debug("DirectInput8Create failed: 0x%08X", hr & 0xFFFFFFFF)
        return []

    try:
        vtable_ptr = ctypes.cast(di, POINTER(c_void_p))[0]

        enum_fn = ctypes.WINFUNCTYPE(
            wintypes.LONG, c_void_p, wintypes.DWORD,
            LPDIENUMDEVICESCALLBACKW, c_void_p, wintypes.DWORD,
        )(ctypes.cast(vtable_ptr, POINTER(c_void_p))[4])

        enum_fn(di, DI8DEVCLASS_GAMECTRL, _callback, None, DIEDFL_ATTACHEDONLY)
    finally:
        release_fn = ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)(
            ctypes.cast(
                ctypes.cast(di, POINTER(c_void_p))[0],
                POINTER(c_void_p),
            )[2]
        )
        release_fn(di)

    return devices
