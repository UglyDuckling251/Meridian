"""Cemu 2.6 controller-profile XML serialization and deserialization.

The canonical format written by Cemu's ``InputManager::save()`` is the only
output format.  For *reading*, the parser also tolerates the ``<axis>`` tag
variant produced by older Meridian builds.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from .models import (
    AxisSettings,
    CemuProfile,
    ControllerEntry,
    MappingEntry,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _text(node: ET.Element | None, default: str = "") -> str:
    if node is None:
        return default
    return (node.text or "").strip()


def _float(node: ET.Element | None, default: float = 0.0) -> float:
    txt = _text(node)
    if not txt:
        return default
    try:
        return float(txt)
    except (ValueError, TypeError):
        return default


def _bool(node: ET.Element | None, default: bool = False) -> bool:
    txt = _text(node).lower()
    if txt in ("1", "true"):
        return True
    if txt in ("0", "false", ""):
        return default
    return default


def _int(node: ET.Element | None, default: int = 0) -> int:
    txt = _text(node)
    if not txt:
        return default
    try:
        return int(txt)
    except (ValueError, TypeError):
        return default


def _parse_axis_settings(node: ET.Element | None) -> AxisSettings:
    """Parse an ``<axis>``, ``<rotation>``, or ``<trigger>`` element.

    Tolerates a bare text value (e.g. ``<rotation>0</rotation>``) emitted by
    some older Meridian profiles by treating it as the deadzone with range 1.
    """
    if node is None:
        return AxisSettings()
    dz_node = node.find("deadzone")
    rg_node = node.find("range")
    if dz_node is not None or rg_node is not None:
        return AxisSettings(
            deadzone=_float(dz_node, 0.15),
            range=_float(rg_node, 1.0),
        )
    bare = _text(node)
    if bare:
        try:
            return AxisSettings(deadzone=float(bare), range=1.0)
        except ValueError:
            pass
    return AxisSettings()


# ── Deserialization ──────────────────────────────────────────────────────

def parse_xml(source: str | Path | bytes) -> CemuProfile:
    """Parse a Cemu controller-profile XML into a :class:`CemuProfile`.

    *source* may be a file path, raw XML bytes, or an XML string.

    Raises :class:`ValueError` on structurally invalid XML.
    """
    if isinstance(source, (str, Path)) and not str(source).lstrip().startswith("<"):
        tree = ET.parse(str(source))
        root = tree.getroot()
    else:
        raw = source if isinstance(source, (str, bytes)) else str(source)
        root = ET.fromstring(raw if isinstance(raw, str) else raw.decode("utf-8"))

    if root.tag != "emulated_controller":
        raise ValueError(
            f"Expected <emulated_controller> root, got <{root.tag}>"
        )

    emulated_type = _text(root.find("type"), "Wii U GamePad")
    profile_name = _text(root.find("profile"))

    controllers: list[ControllerEntry] = []
    for cnode in root.iter("controller"):
        if cnode is root:
            continue
        ctrl = _parse_controller_node(cnode)
        if ctrl is not None:
            controllers.append(ctrl)

    if not controllers:
        ctrl = _parse_flat_controller(root)
        if ctrl is not None:
            controllers.append(ctrl)

    return CemuProfile(
        emulated_type=emulated_type,
        profile_name=profile_name,
        controllers=controllers,
    )


def _parse_controller_node(cnode: ET.Element) -> ControllerEntry | None:
    """Parse a ``<controller>`` element that has child tags (canonical format)."""
    api_node = cnode.find("api")
    if api_node is None:
        if cnode.text and cnode.text.strip():
            return None
        return None

    uuid = _text(cnode.find("uuid"), "0")
    display_name = _text(cnode.find("display_name"))
    product_guid = _text(cnode.find("product_guid"))
    rumble = _float(cnode.find("rumble"))
    motion = _bool(cnode.find("motion"))
    axis = _parse_axis_settings(cnode.find("axis"))
    rotation = _parse_axis_settings(cnode.find("rotation"))
    trigger = _parse_axis_settings(cnode.find("trigger"))

    mappings = _parse_mappings(cnode.find("mappings"))

    return ControllerEntry(
        api=_text(api_node),
        uuid=uuid,
        display_name=display_name,
        product_guid=product_guid,
        rumble=rumble,
        motion=motion,
        axis=axis,
        rotation=rotation,
        trigger=trigger,
        mappings=mappings,
    )


def _parse_flat_controller(root: ET.Element) -> ControllerEntry | None:
    """Handle older Meridian-generated profiles where ``<controller>`` holds
    only a text value (API name) and ``<mappings>`` is a direct child of the
    root element.
    """
    cnode = root.find("controller")
    mappings_node = root.find("mappings")
    if cnode is None and mappings_node is None:
        return None

    api = _text(cnode) if cnode is not None else "SDLController"
    mappings = _parse_mappings(mappings_node)
    if not mappings and cnode is not None and cnode.find("api") is not None:
        return None

    return ControllerEntry(api=api, mappings=mappings)


def _parse_mappings(node: ET.Element | None) -> list[MappingEntry]:
    if node is None:
        return []
    entries: list[MappingEntry] = []
    for entry in node.findall("entry"):
        mapping_node = entry.find("mapping")
        button_node = entry.find("button")
        axis_node = entry.find("axis")

        if mapping_node is None:
            continue

        mapping_el = mapping_node
        if mapping_el.find("device") is not None:
            button_val = _int(mapping_el.find("button"))
            mapping_id_node = entry.find("entry")
            if mapping_id_node is not None:
                mapping_id = _int(mapping_id_node)
                entries.append(MappingEntry(mapping_id=mapping_id, button=button_val))
            continue

        mapping_id = _int(mapping_el)
        if button_node is not None:
            button_val = _int(button_node)
        elif axis_node is not None:
            button_val = _int(axis_node)
        else:
            continue

        entries.append(MappingEntry(mapping_id=mapping_id, button=button_val))

    return entries


# ── Serialization ────────────────────────────────────────────────────────

def to_xml(profile: CemuProfile) -> str:
    """Serialize a :class:`CemuProfile` to Cemu 2.6 canonical XML."""
    root = ET.Element("emulated_controller")

    ET.SubElement(root, "type").text = profile.emulated_type

    if profile.profile_name:
        ET.SubElement(root, "profile").text = profile.profile_name

    for ctrl in profile.controllers:
        _write_controller(root, ctrl)

    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(root, encoding="unicode")
        + "\n"
    )


def write_xml(profile: CemuProfile, path: str | Path) -> Path:
    """Write *profile* to *path* and return the resolved :class:`Path`."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(to_xml(profile), encoding="utf-8")
    return p


def _write_controller(parent: ET.Element, ctrl: ControllerEntry) -> None:
    cnode = ET.SubElement(parent, "controller")

    ET.SubElement(cnode, "api").text = ctrl.api
    ET.SubElement(cnode, "uuid").text = str(ctrl.uuid)
    ET.SubElement(cnode, "display_name").text = ctrl.display_name

    ET.SubElement(cnode, "rumble").text = str(ctrl.rumble)
    ET.SubElement(cnode, "motion").text = str(ctrl.motion).lower()

    if ctrl.product_guid:
        ET.SubElement(cnode, "product_guid").text = ctrl.product_guid

    _write_axis_group(cnode, "axis", ctrl.axis)
    _write_axis_group(cnode, "rotation", ctrl.rotation)
    _write_axis_group(cnode, "trigger", ctrl.trigger)

    mappings_node = ET.SubElement(cnode, "mappings")
    for m in sorted(ctrl.mappings, key=lambda e: e.mapping_id):
        entry_node = ET.SubElement(mappings_node, "entry")
        ET.SubElement(entry_node, "mapping").text = str(m.mapping_id)
        ET.SubElement(entry_node, "button").text = str(m.button)


def _write_axis_group(parent: ET.Element, tag: str, settings: AxisSettings) -> None:
    group = ET.SubElement(parent, tag)
    ET.SubElement(group, "deadzone").text = str(settings.deadzone)
    ET.SubElement(group, "range").text = str(settings.range)
