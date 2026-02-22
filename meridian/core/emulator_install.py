# Copyright (C) 2025-2026 Meridian Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
# See LICENSE for the full text.

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import tarfile
from urllib.error import HTTPError
from urllib.parse import unquote, urlparse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from meridian.core.config import EmulatorCatalogEntry, EmulatorEntry, EMULATOR_CATALOG_BY_ID

log = logging.getLogger(__name__)

_GITHUB_API_BASE = "https://api.github.com/repos"
_HTTP_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Meridian-Installer/1.0",
}
_RETROARCH_BUILDBOT_NIGHTLY = (
    "https://buildbot.libretro.com/nightly/windows/x86_64/latest"
)


@dataclass
class InstallResult:
    ok: bool
    message: str
    entry: EmulatorEntry | None = None
    version: str = ""


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    assets: list[ReleaseAsset]


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def emulators_root() -> Path:
    """``<project>/emulators/`` — standalone emulators and downloaded cores."""
    root = project_root() / "emulators"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _retroarch_default_dir() -> Path:
    """``<project>/retroarch/`` — dedicated top-level folder for RetroArch."""
    return project_root() / "retroarch"


# ---------------------------------------------------------------------------
# RetroArch management  (required dependency for all cores)
# ---------------------------------------------------------------------------

def find_retroarch_entry(existing: list[EmulatorEntry]) -> EmulatorEntry | None:
    """Return the installed RetroArch entry, or None."""
    for item in existing:
        if item.catalog_id == "retroarch" or item.name.lower() == "retroarch":
            return item
    return None


def retroarch_exe_path(existing: list[EmulatorEntry]) -> Path | None:
    """Return the path to retroarch.exe if installed and present on disk."""
    ra = find_retroarch_entry(existing)
    if not ra or not ra.path:
        return None
    p = Path(ra.path)
    if p.exists():
        return p
    default = _retroarch_default_dir() / "retroarch.exe"
    if default.exists():
        return default
    return None


def retroarch_install_dir(existing: list[EmulatorEntry]) -> Path | None:
    """Return RetroArch's root directory."""
    ra = find_retroarch_entry(existing)
    if ra and ra.install_dir and Path(ra.install_dir).exists():
        return Path(ra.install_dir)
    if ra and ra.path:
        parent = Path(ra.path).parent
        if parent.exists():
            return parent
    default = _retroarch_default_dir()
    if default.exists():
        return default
    return None


def ensure_retroarch_installed(existing: list[EmulatorEntry]) -> InstallResult:
    """Install RetroArch if it is not already present.

    Returns an InstallResult with the RetroArch EmulatorEntry on success.
    """
    ra = find_retroarch_entry(existing)
    if ra and ra.path and Path(ra.path).exists():
        return InstallResult(True, "RetroArch is already installed.", ra)

    catalog = EMULATOR_CATALOG_BY_ID.get("retroarch")
    if not catalog:
        return InstallResult(False, "RetroArch catalog entry not found.")

    return install_emulator(catalog, existing)


def update_retroarch(existing: list[EmulatorEntry]) -> InstallResult:
    """Re-install RetroArch to get the latest pinned stable version."""
    catalog = EMULATOR_CATALOG_BY_ID.get("retroarch")
    if not catalog:
        return InstallResult(False, "RetroArch catalog entry not found.")
    return install_emulator(catalog, existing)


def retroarch_cores_dir(existing: list[EmulatorEntry]) -> Path | None:
    """``<project>/emulators/cores/`` — shared directory for all core DLLs.

    Cores are stored under ``emulators/`` separately from RetroArch itself
    so the RetroArch folder stays clean and cores live alongside other
    emulator data.
    """
    ra = find_retroarch_entry(existing)
    if not ra:
        return None
    cores = emulators_root() / "cores"
    cores.mkdir(parents=True, exist_ok=True)
    return cores


# ---------------------------------------------------------------------------
# Core management
# ---------------------------------------------------------------------------

def download_single_retroarch_core(dll_name: str, cores_dir: Path) -> Path | None:
    """Download a single RetroArch core DLL into *cores_dir*."""
    import time as _time

    cores_dir.mkdir(parents=True, exist_ok=True)
    core_zip_url = f"{_RETROARCH_BUILDBOT_NIGHTLY}/{dll_name}.zip"
    try:
        zip_path = _download_asset(core_zip_url, f"{dll_name}.zip")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(cores_dir)
        _safe_delete_file(zip_path)
        core_path = cores_dir / dll_name
        if core_path.exists():
            # Set the mtime to now so core_has_update() doesn't falsely
            # report an update — zipfile.extractall() preserves the archive's
            # internal timestamps which are older than the server's Last-Modified.
            now = _time.time()
            import os as _os
            _os.utime(core_path, (now, now))
            return core_path
        return None
    except Exception:
        return None


def core_has_update(
    catalog_entry: EmulatorCatalogEntry,
    existing: list[EmulatorEntry],
) -> bool:
    """Check if a newer nightly build of a RetroArch core exists.

    Compares the local DLL's modification time against the remote server's
    ``Last-Modified`` header via a lightweight HTTP HEAD request.
    Returns False if the core isn't installed or the check fails.
    """
    import email.utils
    dll_name = catalog_entry.core_filename
    if not dll_name:
        return False
    cores = retroarch_cores_dir(existing)
    if not cores:
        return False
    local_path = cores / dll_name
    if not local_path.exists():
        return False

    url = f"{_RETROARCH_BUILDBOT_NIGHTLY}/{dll_name}.zip"
    try:
        req = urllib.request.Request(url, method="HEAD", headers=_HTTP_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            lm = resp.headers.get("Last-Modified", "")
            if not lm:
                return False
            remote_ts = email.utils.parsedate_to_datetime(lm).timestamp()
            local_ts = local_path.stat().st_mtime
            return remote_ts > local_ts
    except Exception:
        return False


def update_retroarch_core(
    catalog_entry: EmulatorCatalogEntry,
    existing: list[EmulatorEntry],
) -> InstallResult:
    """Re-download a RetroArch core to get the latest nightly build."""
    dll_name = catalog_entry.core_filename
    if not dll_name:
        return InstallResult(False, f"No core filename for {catalog_entry.name}.")

    cores = retroarch_cores_dir(existing)
    if not cores:
        return InstallResult(False, "RetroArch is not installed.")

    core_path = download_single_retroarch_core(dll_name, cores)
    if core_path:
        return InstallResult(True, f"Updated {catalog_entry.name} core.")
    return InstallResult(False, f"Failed to download {dll_name}.")


def delete_retroarch_core(
    catalog_entry: EmulatorCatalogEntry,
    existing: list[EmulatorEntry],
) -> tuple[bool, str]:
    """Delete a RetroArch core DLL from disk.

    Returns (success, error_message).
    """
    dll_name = catalog_entry.core_filename
    if not dll_name:
        return True, ""

    cores = retroarch_cores_dir(existing)
    if not cores:
        return True, "RetroArch cores directory not found (nothing to delete)."

    target = cores / dll_name
    if not target.exists():
        return True, ""
    try:
        target.unlink()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def check_core_installed(
    catalog_entry: EmulatorCatalogEntry,
    existing: list[EmulatorEntry],
) -> bool:
    """Return True if the core DLL exists on disk."""
    dll_name = catalog_entry.core_filename
    if not dll_name:
        return False
    cores = retroarch_cores_dir(existing)
    if not cores:
        return False
    return (cores / dll_name).exists()


# ---------------------------------------------------------------------------
# Main install dispatcher
# ---------------------------------------------------------------------------

def install_emulator(
    entry: EmulatorCatalogEntry,
    existing: list[EmulatorEntry],
) -> InstallResult:
    """Install one emulator entry (standalone or RetroArch core)."""
    if entry.install_strategy == "manual":
        reason = entry.notes or "No automated Windows installer is available."
        return InstallResult(
            False, f"Manual install required for {entry.name}: {reason}"
        )

    if entry.install_strategy == "retroarch_core":
        return _install_retroarch_core(entry, existing)

    if not entry.windows_supported:
        return InstallResult(
            False, f"{entry.name} does not have an automated Windows installer."
        )

    try:
        release = _resolve_latest_stable_release(entry)
        ranked_assets = _rank_assets(entry, release.assets)
        if not ranked_assets:
            return InstallResult(
                False, f"No matching Windows asset found for {entry.name}."
            )

        # RetroArch gets its own top-level folder; everything else
        # goes under emulators/.
        if entry.id == "retroarch":
            install_dir = _retroarch_default_dir()
        else:
            install_dir = emulators_root() / (entry.install_subdir or entry.id)
        exe_path: Path | None = None
        resolved_install_dir = install_dir
        last_error = ""

        if entry.install_strategy == "installer":
            asset = ranked_assets[0]
            download_file = _download_asset(asset.download_url, asset.name)
            _run_windows_installer(download_file, install_dir)
            exe_path = _detect_executable(install_dir, entry.exe_candidates)
            if not exe_path:
                exe_path = _detect_installer_executable_windows(entry)
                if exe_path:
                    resolved_install_dir = exe_path.parent
        else:
            for asset in ranked_assets[:10]:
                try:
                    download_file = _download_asset(asset.download_url, asset.name)
                    _install_archive(download_file, install_dir)
                    exe_path = _detect_executable(install_dir, entry.exe_candidates)
                    if exe_path:
                        break
                    last_error = (
                        f"Asset '{asset.name}' did not contain a runnable executable."
                    )
                except Exception as exc:
                    last_error = f"Asset '{asset.name}' failed: {exc}"
                finally:
                    _safe_delete_file(
                        download_file if "download_file" in locals() else None
                    )

        if not exe_path:
            return InstallResult(
                False,
                f"{entry.name} installed, but executable was not found in {install_dir}."
                + (f" {last_error}" if last_error else ""),
            )

        emu_entry = EmulatorEntry(
            name=entry.name,
            path=str(exe_path),
            args=entry.default_args or '"{rom}"',
            catalog_id=entry.id,
            version=release.tag,
            install_dir=str(resolved_install_dir),
            provider=entry.release_provider,
        )
        return InstallResult(
            True, f"Installed {entry.name} ({release.tag}).", emu_entry, release.tag
        )
    except Exception as exc:
        return InstallResult(False, f"Failed to install {entry.name}: {exc}")


# ---------------------------------------------------------------------------
# RetroArch core installation
# ---------------------------------------------------------------------------

def _install_retroarch_core(
    entry: EmulatorCatalogEntry,
    existing: list[EmulatorEntry],
) -> InstallResult:
    """Install a RetroArch core and create an individual EmulatorEntry for it."""
    dll_name = entry.core_filename
    if not dll_name:
        return InstallResult(False, f"No core filename for {entry.name}.")

    # Ensure RetroArch is installed first
    ra = find_retroarch_entry(existing)
    if not ra or not ra.path or not Path(ra.path).exists():
        ra_result = ensure_retroarch_installed(existing)
        if not ra_result.ok:
            return InstallResult(
                False,
                f"RetroArch must be installed first. {ra_result.message}",
            )
        ra = ra_result.entry

    if not ra or not ra.path:
        return InstallResult(False, "RetroArch installation not found.")

    ra_root = Path(ra.install_dir) if ra.install_dir else Path(ra.path).parent
    cores_dir = emulators_root() / "cores"

    try:
        core_dll = download_single_retroarch_core(dll_name, cores_dir)
        if not core_dll:
            return InstallResult(
                False, f"Failed to download RetroArch core {dll_name}."
            )

        # Build an individual EmulatorEntry for this core.
        # install_dir points to RetroArch so launch logic can find it,
        # but the core DLL lives under emulators/cores/.
        core_entry = EmulatorEntry(
            name=entry.name,
            path=str(Path(ra.path)),
            args='-L "{core}" "{rom}"',
            catalog_id=entry.id,
            version="latest",
            install_dir=str(ra_root),
            provider="retroarch_core",
        )
        for system_id in entry.systems:
            core_entry.system_overrides[system_id] = dll_name

        return InstallResult(
            True,
            f"Installed {entry.name} core ({dll_name}).",
            core_entry,
            "nightly",
        )
    except Exception as exc:
        return InstallResult(
            False, f"Failed to install RetroArch core {entry.name}: {exc}"
        )


# ---------------------------------------------------------------------------
# Release resolution
# ---------------------------------------------------------------------------

def _resolve_latest_stable_release(entry: EmulatorCatalogEntry) -> ReleaseInfo:
    if entry.release_provider == "direct":
        url = (entry.preferred_download_url or entry.release_source or "").strip()
        if not url:
            raise RuntimeError(
                f"No direct download URL configured for {entry.name}."
            )
        file_name = _asset_name_from_url(url)
        tag = entry.preferred_version or "pinned"
        return ReleaseInfo(
            tag=tag, assets=[ReleaseAsset(name=file_name, download_url=url)]
        )

    if entry.release_provider != "github" or not entry.release_source:
        raise RuntimeError(f"Unsupported release provider for {entry.name}")

    url = f"{_GITHUB_API_BASE}/{entry.release_source}/releases"
    req = urllib.request.Request(url, headers=_HTTP_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(
            f"Release lookup failed ({exc.code}) for {entry.release_source}."
        ) from exc

    if not isinstance(payload, list) or not payload:
        raise RuntimeError("No releases available.")

    release = None
    for candidate in payload:
        if candidate.get("draft"):
            continue
        if candidate.get("prerelease"):
            continue
        release = candidate
        break
    if release is None:
        release = payload[0]

    tag = str(release.get("tag_name") or release.get("name") or "latest")
    assets = []
    for asset in release.get("assets", []):
        name = str(asset.get("name", ""))
        dl = str(asset.get("browser_download_url", ""))
        if name and dl:
            assets.append(ReleaseAsset(name=name, download_url=dl))
    return ReleaseInfo(tag=tag, assets=assets)


# ---------------------------------------------------------------------------
# Asset ranking
# ---------------------------------------------------------------------------

def _rank_assets(
    entry: EmulatorCatalogEntry, assets: list[ReleaseAsset]
) -> list[ReleaseAsset]:
    if not assets:
        return []
    include = [s.lower() for s in entry.asset_include]
    exclude = [s.lower() for s in entry.asset_exclude]
    global_exclude = [
        "source", "src", "symbols", "pdb", "debug",
        "android", "ios", "macos", "linux",
        "arm64", "aarch64", "arm-",
    ]

    def _score(asset_name: str) -> int:
        name = asset_name.lower()
        if any(token in name for token in exclude + global_exclude):
            return -10_000
        if not _is_supported_installer_or_archive(name):
            return -10_000

        score = 0
        for token in include:
            if token in name:
                score += 100

        if name.endswith(".zip"):
            score += 30
        elif name.endswith(".tar.gz") or name.endswith(".tgz"):
            score += 20
        elif name.endswith(".7z"):
            score += 25
        elif name.endswith(".exe"):
            score += 15

        if "x64" in name or "x86_64" in name or "x86-64" in name or "win64" in name:
            score += 10
        if "windows" in name or "win" in name:
            score += 10
        return score

    ranked = sorted(assets, key=lambda a: _score(a.name), reverse=True)
    return [asset for asset in ranked if _score(asset.name) >= 0]


def _is_supported_installer_or_archive(asset_name: str) -> bool:
    return (
        asset_name.endswith(".zip")
        or asset_name.endswith(".7z")
        or asset_name.endswith(".exe")
        or asset_name.endswith(".tar.gz")
        or asset_name.endswith(".tgz")
    )


# ---------------------------------------------------------------------------
# Download / extraction helpers
# ---------------------------------------------------------------------------

def _download_asset(url: str, filename: str) -> Path:
    download_dir = emulators_root() / "_downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    dest = download_dir / filename

    req = urllib.request.Request(url, headers=_HTTP_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=120) as res:
        data = res.read()
    dest.write_bytes(data)
    return dest


def _safe_delete_file(path: Path | None) -> None:
    if not path:
        return
    try:
        if path.exists():
            path.unlink(missing_ok=True)
    except Exception:
        pass


def _asset_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if not name:
        return "download.bin"
    return name


def _install_archive(archive_path: Path, install_dir: Path) -> None:
    if install_dir.exists():
        shutil.rmtree(install_dir)
    install_dir.mkdir(parents=True, exist_ok=True)

    lower = archive_path.name.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(install_dir)
        return
    if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(install_dir)
        return
    if lower.endswith(".exe"):
        target = install_dir / archive_path.name
        shutil.copy2(archive_path, target)
        return
    if lower.endswith(".7z"):
        py7zr_error: Exception | None = None
        try:
            import py7zr  # type: ignore
            with py7zr.SevenZipFile(archive_path, mode="r") as zf:
                zf.extractall(path=install_dir)
            return
        except Exception as exc:
            py7zr_error = exc

        seven_zip = _find_or_download_7za()
        if seven_zip:
            result = subprocess.run(
                [str(seven_zip), "x", str(archive_path), f"-o{install_dir}", "-y"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return
            output = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"7z extraction failed. "
                f"py7zr error: {py7zr_error}. "
                f"7za output: {output or 'unknown error'}"
            )

        raise RuntimeError(
            "7z extraction failed and no 7-Zip tool could be obtained. "
            f"py7zr error: {py7zr_error}"
        )
    raise RuntimeError(f"Unsupported archive format: {archive_path.name}")


# URL for the official standalone 7za.exe packaged as a .zip (works with
# Python's built-in zipfile).  This is used when py7zr cannot handle
# certain codecs (e.g. BCJ2 in RetroArch archives) and no system 7-Zip
# is installed.
_7ZA_ZIP_URL = "https://www.7-zip.org/a/7za920.zip"


def _find_or_download_7za() -> Path | None:
    """Locate an existing 7z CLI, or download 7za.exe into the project."""
    # Check system PATH first
    system_7z = shutil.which("7z") or shutil.which("7za") or shutil.which("7zr")
    if system_7z:
        return Path(system_7z)

    # Check our own tools directory
    tools_dir = project_root() / "tools"
    local_7za = tools_dir / "7za.exe"
    if local_7za.exists():
        return local_7za

    # Download 7za.exe from the official 7-Zip site
    log.info("Downloading 7za.exe for .7z extraction support...")
    try:
        tools_dir.mkdir(parents=True, exist_ok=True)
        zip_dest = tools_dir / "7za920.zip"
        req = urllib.request.Request(
            _7ZA_ZIP_URL,
            headers={"User-Agent": "Meridian-Installer/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            zip_dest.write_bytes(res.read())
        with zipfile.ZipFile(zip_dest, "r") as zf:
            zf.extract("7za.exe", tools_dir)
        _safe_delete_file(zip_dest)
        if local_7za.exists():
            log.info("7za.exe downloaded to %s", local_7za)
            return local_7za
    except Exception as exc:
        log.warning("Failed to download 7za.exe: %s", exc)

    return None


# ---------------------------------------------------------------------------
# Windows installer helpers
# ---------------------------------------------------------------------------

def _run_windows_installer(installer_path: Path, install_dir: Path) -> None:
    """Run a Windows installer interactively with install_dir pre-filled."""
    install_dir.mkdir(parents=True, exist_ok=True)

    commands = [
        [str(installer_path), "/CURRENTUSER", f"/DIR={install_dir}"],
        [str(installer_path), f"/DIR={install_dir}"],
        [str(installer_path), f"/D={install_dir}"],
        [str(installer_path)],
    ]

    errors: list[str] = []
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
        except OSError as exc:
            if getattr(exc, "winerror", None) == 740:
                _run_elevated_process(cmd)
                return
            raise
        if result.returncode == 0:
            return
        if result.returncode == 740:
            _run_elevated_process(cmd)
            return
        output = (result.stderr or result.stdout or "").strip()
        errors.append(f"{cmd[1]} => code {result.returncode}: {output[:400]}")

    raise RuntimeError(
        "Installer execution failed. Tried common installer flags. "
        + " | ".join(errors)
    )


def _run_elevated_process(cmd: list[str]) -> None:
    """Run installer command elevated (UAC) and wait for completion."""
    if sys.platform != "win32":
        raise RuntimeError("Elevation fallback is only supported on Windows.")
    if not cmd:
        raise RuntimeError("Installer command is empty.")

    exe = cmd[0]
    args = " ".join(_quote_windows_arg(a) for a in cmd[1:])
    ps_cmd = (
        "$p = Start-Process -FilePath "
        f"{_ps_quote(exe)} -ArgumentList { _ps_quote(args) } "
        "-Verb RunAs -PassThru -Wait; "
        "exit $p.ExitCode"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "Elevated installer run failed or was cancelled by user. "
            f"PowerShell output: {output[:500]}"
        )


def _quote_windows_arg(value: str) -> str:
    if not value:
        return '""'
    if any(ch in value for ch in ' \t"'):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Executable detection
# ---------------------------------------------------------------------------

def _detect_executable(install_dir: Path, exe_candidates: list[str]) -> Path | None:
    for candidate in exe_candidates:
        direct = install_dir / candidate
        if direct.exists():
            return direct

    lowered = {name.lower() for name in exe_candidates}
    for file_path in install_dir.rglob("*.exe"):
        if file_path.name.lower() in lowered:
            return file_path

    for file_path in install_dir.rglob("*.exe"):
        return file_path
    return None


def _detect_installer_executable_windows(entry: EmulatorCatalogEntry) -> Path | None:
    """Best-effort executable discovery from Windows uninstall registry metadata."""
    if sys.platform != "win32":
        return None
    try:
        import winreg  # type: ignore
    except Exception:
        return None

    hives = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    name_tokens = {entry.name.lower(), entry.id.lower().replace("_", " ")}

    for hive, base_path in hives:
        try:
            with winreg.OpenKey(hive, base_path) as base:
                subkey_count, _value_count, _last_mod = winreg.QueryInfoKey(base)
                for idx in range(subkey_count):
                    try:
                        subkey_name = winreg.EnumKey(base, idx)
                        with winreg.OpenKey(base, subkey_name) as sub:
                            display_name = _read_reg_str(sub, "DisplayName").lower()
                            if not display_name or not any(
                                token in display_name for token in name_tokens
                            ):
                                continue

                            install_location = _read_reg_str(sub, "InstallLocation")
                            display_icon = _read_reg_str(sub, "DisplayIcon")

                            if install_location:
                                install_path = Path(install_location.strip('"'))
                                exe = _detect_executable(
                                    install_path, entry.exe_candidates
                                )
                                if exe:
                                    return exe
                            if display_icon:
                                icon_path = (
                                    display_icon.split(",")[0].strip().strip('"')
                                )
                                icon_exe = Path(icon_path)
                                if (
                                    icon_exe.exists()
                                    and icon_exe.suffix.lower() == ".exe"
                                ):
                                    return icon_exe
                    except Exception:
                        continue
        except Exception:
            continue
    return None


def _read_reg_str(subkey, name: str) -> str:
    try:
        value, _kind = subkey.QueryValueEx(name)
    except Exception:
        return ""
    if isinstance(value, str):
        return value
    return str(value)
