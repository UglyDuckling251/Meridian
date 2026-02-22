from emulators.extensions.cemu import _windevice
from emulators.extensions.cemu._windevice import DIDevice


def test_find_device_resolves_numbered_duplicate_label(monkeypatch):
    devices = [
        DIDevice(
            instance_guid="GUID-ONE",
            product_guid="PROD",
            name="DualSense Wireless Controller",
        ),
        DIDevice(
            instance_guid="GUID-TWO",
            product_guid="PROD",
            name="DualSense Wireless Controller",
        ),
    ]
    monkeypatch.setattr(_windevice, "enumerate_devices", lambda: devices)

    d1 = _windevice.find_device("DualSense Wireless Controller [#1]")
    d2 = _windevice.find_device("DualSense Wireless Controller [#2]")

    assert d1 is not None and d1.instance_guid == "GUID-ONE"
    assert d2 is not None and d2.instance_guid == "GUID-TWO"


def test_find_device_prefers_index_when_available(monkeypatch):
    devices = [
        DIDevice(instance_guid="A", product_guid="P", name="Foo Pad"),
        DIDevice(instance_guid="B", product_guid="P", name="Foo Pad"),
        DIDevice(instance_guid="C", product_guid="P", name="Bar Pad"),
    ]
    monkeypatch.setattr(_windevice, "enumerate_devices", lambda: devices)

    chosen = _windevice.find_device("Foo Pad", preferred_index=1)
    assert chosen is not None
    assert chosen.instance_guid == "B"
