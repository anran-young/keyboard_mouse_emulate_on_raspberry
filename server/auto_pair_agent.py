#!/usr/bin/python3
#
# BlueZ Agent that auto-accepts pairing/authorization requests.
#

import os
import sys
import time
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib


AGENT_PATH = "/org/bluez/AutoPairAgent"


def _log(message: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class AutoPairAgent(dbus.service.Object):
    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Release(self):
        _log("Release()")

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        _log(f"RequestPinCode(device={device}) -> 0000")
        # For legacy pairing flows. Returning a fixed PIN keeps things deterministic.
        return "0000"

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        _log(f"RequestPasskey(device={device}) -> 0")
        # For legacy passkey flows.
        return dbus.UInt32(0)

    @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        _log(f"DisplayPasskey(device={device}, passkey={int(passkey)}, entered={int(entered)})")

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        _log(f"DisplayPinCode(device={device}, pincode={pincode})")

    @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        # iOS/iPadOS often triggers this for "Just Works" confirmation.
        # Accept without user interaction.
        _log(f"RequestConfirmation(device={device}, passkey={int(passkey)}) -> ACCEPT")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        # Accept pairing/authorization.
        _log(f"RequestAuthorization(device={device}) -> ACCEPT")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        # Accept service authorization.
        _log(f"AuthorizeService(device={device}, uuid={uuid}) -> ACCEPT")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Cancel(self):
        _log("Cancel()")


def main():
    if os.geteuid() != 0:
        sys.exit("Only root can run this script")

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    agent = AutoPairAgent(bus, AGENT_PATH)

    manager = dbus.Interface(
        bus.get_object("org.bluez", "/org/bluez"), "org.bluez.AgentManager1"
    )

    # Capability values: DisplayOnly, DisplayYesNo, KeyboardOnly, NoInputNoOutput, KeyboardDisplay.
    # iPadOS tends to behave better with DisplayYesNo for numeric comparison.
    capability = os.environ.get("BT_AGENT_CAPABILITY", "DisplayYesNo")
    _log(f"Starting AutoPairAgent path={AGENT_PATH} capability={capability}")

    try:
        manager.RegisterAgent(AGENT_PATH, capability)
        _log("RegisterAgent() ok")
    except dbus.DBusException as exc:
        # If already registered (e.g., restarted without unregister), continue.
        if "AlreadyExists" not in str(exc):
            raise
        _log(f"RegisterAgent() already exists: {exc}")

    try:
        manager.RequestDefaultAgent(AGENT_PATH)
        _log("RequestDefaultAgent() ok")
    except dbus.DBusException as exc:
        # If another agent already is default, try to override; if denied, surface it.
        if "AlreadyExists" in str(exc):
            _log(f"RequestDefaultAgent() already exists: {exc}")
        else:
            raise

    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()
