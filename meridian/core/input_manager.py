"""
Controller detection and input capture for Meridian.

Uses pygame's joystick subsystem for buttons / axes / hats, and calls
into SDL2 directly (via ctypes) for gyroscope and accelerometer sensor
data — pygame does not expose those APIs.
"""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass, field
from pathlib import Path

# SDL2 sensor-type constants  (from SDL_sensor.h)
_SDL_SENSOR_ACCEL = 1
_SDL_SENSOR_GYRO = 2

# Gyro values are in rad/s — a deliberate rotation is typically > 2
_GYRO_THRESHOLD = 2.0


@dataclass
class ControllerInfo:
    """Describes a connected game controller."""
    index: int
    name: str
    num_buttons: int
    num_axes: int
    num_hats: int
    has_gyro: bool = False
    has_accel: bool = False


class InputManager:
    """Singleton managing controller detection and input capture.

    *  Buttons / axes / hats — processed through **pygame**.
    *  Gyroscope / accelerometer — read through the **SDL2 C library**
       (loaded via :mod:`ctypes` from the copy bundled inside pygame).

    The subsystems are initialised lazily on the first call to
    :meth:`ensure_ready`.
    """

    _instance: InputManager | None = None

    def __init__(self) -> None:
        self._ready = False
        self._controllers: list[ControllerInfo] = []
        self._joysticks: dict[int, object] = {}
        # SDL2 ctypes handle + opened GameController pointers
        self._sdl2: ctypes.CDLL | None = None
        self._gc_handles: dict[int, int] = {}  # joy index → GC void*

    # -- Singleton access --------------------------------------------------

    @classmethod
    def instance(cls) -> InputManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -- Lifecycle ---------------------------------------------------------

    def ensure_ready(self) -> bool:
        """Initialise pygame joystick + SDL2 sensor layer.

        Returns ``True`` on success.
        """
        if self._ready:
            return True
        try:
            import os
            import pygame

            prev = os.environ.get("SDL_VIDEODRIVER")
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            try:
                pygame.display.init()
            finally:
                if prev is not None:
                    os.environ["SDL_VIDEODRIVER"] = prev
                else:
                    os.environ.pop("SDL_VIDEODRIVER", None)

            pygame.joystick.init()
            self._ready = True

            # Try to load SDL2 for motion-sensor access
            self._sdl2 = _load_sdl2_lib()
            if self._sdl2:
                _setup_sdl2_signatures(self._sdl2)

            self.refresh()
            return True
        except Exception:
            return False

    def shutdown(self) -> None:
        """Release all resources."""
        self._close_game_controllers()
        if not self._ready:
            return
        try:
            import pygame
            self._joysticks.clear()
            self._controllers.clear()
            pygame.joystick.quit()
            pygame.display.quit()
        except Exception:
            pass
        self._ready = False

    # -- Controller enumeration --------------------------------------------

    def refresh(self) -> list[ControllerInfo]:
        """Re-scan for connected controllers (handles hot-plug)."""
        if not self.ensure_ready():
            return []

        import pygame

        self._close_game_controllers()
        pygame.joystick.quit()
        pygame.joystick.init()

        self._joysticks.clear()
        self._controllers.clear()

        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            self._joysticks[i] = joy
            self._controllers.append(ControllerInfo(
                index=i,
                name=joy.get_name(),
                num_buttons=joy.get_numbuttons(),
                num_axes=joy.get_numaxes(),
                num_hats=joy.get_numhats(),
            ))

        # Open as GameControllers for sensor access
        self._open_game_controllers()
        return list(self._controllers)

    def controllers(self) -> list[ControllerInfo]:
        return list(self._controllers)

    def controller_names(self) -> list[str]:
        return [c.name for c in self._controllers]

    def index_for_name(self, name: str) -> int | None:
        for c in self._controllers:
            if c.name == name:
                return c.index
        return None

    # -- SDL2 GameController / sensor layer --------------------------------

    def _open_game_controllers(self) -> None:
        """Open each joystick as an SDL GameController and enable sensors."""
        if not self._sdl2:
            return
        lib = self._sdl2
        for c in self._controllers:
            try:
                if not lib.SDL_IsGameController(c.index):
                    continue
                handle = lib.SDL_GameControllerOpen(c.index)
                if not handle:
                    continue
                self._gc_handles[c.index] = handle

                if lib.SDL_GameControllerHasSensor(handle, _SDL_SENSOR_GYRO):
                    lib.SDL_GameControllerSetSensorEnabled(
                        handle, _SDL_SENSOR_GYRO, 1,
                    )
                    c.has_gyro = True

                if lib.SDL_GameControllerHasSensor(handle, _SDL_SENSOR_ACCEL):
                    lib.SDL_GameControllerSetSensorEnabled(
                        handle, _SDL_SENSOR_ACCEL, 1,
                    )
                    c.has_accel = True
            except Exception:
                continue

    def _close_game_controllers(self) -> None:
        if not self._sdl2:
            return
        for handle in self._gc_handles.values():
            try:
                self._sdl2.SDL_GameControllerClose(handle)
            except Exception:
                pass
        self._gc_handles.clear()

    def get_gyro(self, device_index: int) -> tuple[float, float, float] | None:
        """Read the gyroscope (rad/s) for *device_index*."""
        return self._read_sensor(device_index, _SDL_SENSOR_GYRO)

    def get_accel(self, device_index: int) -> tuple[float, float, float] | None:
        """Read the accelerometer (m/s²) for *device_index*."""
        return self._read_sensor(device_index, _SDL_SENSOR_ACCEL)

    def _read_sensor(
        self, device_index: int, sensor_type: int,
    ) -> tuple[float, float, float] | None:
        handle = self._gc_handles.get(device_index)
        if not handle or not self._sdl2:
            return None
        buf = (ctypes.c_float * 3)()
        rc = self._sdl2.SDL_GameControllerGetSensorData(
            handle, sensor_type, buf, 3,
        )
        if rc != 0:
            return None
        return (buf[0], buf[1], buf[2])

    # -- Input capture -----------------------------------------------------

    def drain_events(self) -> None:
        if not self._ready:
            return
        import pygame
        pygame.event.get()

    def poll_binding(self, device_index: int | None = None) -> str | None:
        """Return the next binding string, or ``None``.

        Checks buttons / axes / hats (via pygame) **and** gyroscope
        motion (via SDL2 sensors).
        """
        if not self._ready:
            return None

        import pygame

        for event in pygame.event.get():
            if device_index is not None:
                ev_joy = getattr(event, "joy", None)
                if ev_joy is not None and ev_joy != device_index:
                    continue

            if event.type == pygame.JOYBUTTONDOWN:
                return f"Button {event.button}"

            if event.type == pygame.JOYAXISMOTION:
                if abs(event.value) > 0.5:
                    sign = "+" if event.value > 0 else "-"
                    return f"Axis {event.axis}{sign}"

            if event.type == pygame.JOYHATMOTION:
                x, y = event.value
                if x != 0 or y != 0:
                    parts: list[str] = []
                    if y > 0:
                        parts.append("Up")
                    if y < 0:
                        parts.append("Down")
                    if x < 0:
                        parts.append("Left")
                    if x > 0:
                        parts.append("Right")
                    return f"Hat {event.hat} {'+'.join(parts)}"

        # -- Gyroscope check (SDL2 sensors) --------------------------------
        if self._sdl2:
            indices = (
                [device_index] if device_index is not None
                else list(self._gc_handles.keys())
            )
            for idx in indices:
                gyro = self.get_gyro(idx)
                if gyro is None:
                    continue
                gx, gy, gz = gyro
                if max(abs(gx), abs(gy), abs(gz)) > _GYRO_THRESHOLD:
                    return "Gyro"

        return None


# ======================================================================
# SDL2 shared-library helpers
# ======================================================================

def _load_sdl2_lib() -> ctypes.CDLL | None:
    """Locate and load the SDL2 shared library bundled with pygame."""
    try:
        import pygame
        pg_dir = Path(pygame.__file__).parent

        if sys.platform == "win32":
            candidates = [pg_dir / "SDL2.dll"]
        elif sys.platform == "darwin":
            candidates = [
                pg_dir / ".dylibs" / "libSDL2-2.0.0.dylib",
                pg_dir / "libSDL2.dylib",
            ]
        else:
            candidates = [
                pg_dir / "libSDL2-2.0.so.0",
                pg_dir / "libSDL2.so",
            ]

        for path in candidates:
            if path.exists():
                return ctypes.CDLL(str(path))
    except Exception:
        pass

    # Fallback: system-wide
    try:
        import ctypes.util
        name = ctypes.util.find_library("SDL2")
        if name:
            return ctypes.CDLL(name)
    except Exception:
        pass

    return None


def _setup_sdl2_signatures(lib: ctypes.CDLL) -> None:
    """Declare the C signatures for the handful of SDL2 functions we call."""
    try:
        c_int = ctypes.c_int
        c_void_p = ctypes.c_void_p

        lib.SDL_IsGameController.restype = c_int
        lib.SDL_IsGameController.argtypes = [c_int]

        lib.SDL_GameControllerOpen.restype = c_void_p
        lib.SDL_GameControllerOpen.argtypes = [c_int]

        lib.SDL_GameControllerClose.restype = None
        lib.SDL_GameControllerClose.argtypes = [c_void_p]

        lib.SDL_GameControllerHasSensor.restype = c_int
        lib.SDL_GameControllerHasSensor.argtypes = [c_void_p, c_int]

        lib.SDL_GameControllerSetSensorEnabled.restype = c_int
        lib.SDL_GameControllerSetSensorEnabled.argtypes = [c_void_p, c_int, c_int]

        lib.SDL_GameControllerGetSensorData.restype = c_int
        lib.SDL_GameControllerGetSensorData.argtypes = [
            c_void_p, c_int, ctypes.POINTER(ctypes.c_float), c_int,
        ]
    except AttributeError:
        # SDL2 build too old — no sensor functions.  Clear the handle so
        # the rest of the code gracefully skips sensor work.
        pass
