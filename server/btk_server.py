#!/usr/bin/python3
#
# Bluetooth keyboard/Mouse emulator DBUS Service
#

from __future__ import absolute_import, print_function
from optparse import OptionParser, make_option
import os
import sys
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
import time
import socket
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
import logging
from logging import debug, info, warning, error
import bluetooth
from bluetooth import *
import threading


AGENT_PATH = "/org/thanhle/btkbservice/agent"
PROFILE_PATH = "/org/thanhle/btkbservice/profile"
BLUEZ_ADAPTER_PATH = "/org/bluez/hci0"

logging.basicConfig(level=logging.DEBUG)

# @todo fill your host mac here manually
TARGET_ADDRESS = "88:A2:9E:3A:34:42"


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class AutoAcceptAgent(dbus.service.Object):
    """BlueZ Agent that auto-accepts pairing/authorization (Just Works)."""

    def __init__(self, bus, path=AGENT_PATH):
        super().__init__(bus, path)

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Release(self):
        info("Agent Release")

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        # For NoInputNoOutput devices, iOS should use "Just Works".
        # Returning a fixed PIN often causes pairing to fail.
        warning("RequestPinCode for %s; rejecting to force JustWorks", device)
        raise Rejected("NoInputNoOutput")

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        warning("RequestPasskey for %s; rejecting to force JustWorks", device)
        raise Rejected("NoInputNoOutput")

    @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        info("DisplayPasskey device=%s passkey=%06u entered=%u", device, passkey, entered)

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        info("DisplayPinCode device=%s pincode=%s", device, pincode)

    @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        info("RequestConfirmation device=%s passkey=%06u -> auto-accept", device, passkey)
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        info("RequestAuthorization device=%s -> auto-accept", device)
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        info("AuthorizeService device=%s uuid=%s -> auto-accept", device, uuid)
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Cancel(self):
        info("Agent Cancel")


def register_no_io_agent(bus):
    agent = AutoAcceptAgent(bus)
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.AgentManager1")

    try:
        manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
    except dbus.exceptions.DBusException as ex:
        # If something else already registered this path/capability, keep going.
        warning("RegisterAgent failed: %s", ex)

    try:
        manager.RequestDefaultAgent(AGENT_PATH)
    except dbus.exceptions.DBusException as ex:
        warning("RequestDefaultAgent failed: %s", ex)

    info("BlueZ Agent registered at %s (NoInputNoOutput)", AGENT_PATH)
    return agent


def ensure_adapter_discoverable(bus):
    adapter = bus.get_object("org.bluez", BLUEZ_ADAPTER_PATH)
    props = dbus.Interface(adapter, "org.freedesktop.DBus.Properties")

    # Best-effort: some distros/permissions may restrict these.
    for (key, val) in (
        ("Powered", dbus.Boolean(True)),
        ("Pairable", dbus.Boolean(True)),
        ("PairableTimeout", dbus.UInt32(0)),
        ("Discoverable", dbus.Boolean(True)),
        ("DiscoverableTimeout", dbus.UInt32(0)),
    ):
        try:
            props.Set("org.bluez.Adapter1", key, val)
        except dbus.exceptions.DBusException as ex:
            warning("Failed to set Adapter1.%s: %s", key, ex)

    try:
        name = props.Get("org.bluez.Adapter1", "Alias")
        info("Adapter ready (Alias=%s)", name)
    except dbus.exceptions.DBusException:
        info("Adapter ready")


class BTKbProfile(dbus.service.Object):
    def __init__(self, bus, device, path=PROFILE_PATH):
        super().__init__(bus, path)
        self._device = device

    @dbus.service.method("org.bluez.Profile1", in_signature="", out_signature="")
    def Release(self):
        info("Profile Release")

    @dbus.service.method("org.bluez.Profile1", in_signature="oha{sv}", out_signature="")
    def NewConnection(self, device, fd, properties):
        info("NewConnection device=%s properties=%s", device, dict(properties))
        self._device.on_new_connection(fd, properties)

    @dbus.service.method("org.bluez.Profile1", in_signature="o", out_signature="")
    def RequestDisconnection(self, device):
        info("RequestDisconnection device=%s", device)
        self._device.on_disconnection()

class BTKbDevice():
    # change these constants
    MY_ADDRESS = "88:A2:9E:3A:34:42"
    MY_DEV_NAME = "ThanhLe_Keyboard_Mouse"

    # define some constants
    P_CTRL = 17  # Service port - must match port configured in SDP record
    P_INTR = 19  # Interrupt port - must match port configured in SDP record
    # dbus path of the bluez profile we will create
    # file path of the sdp record to load
    SDP_RECORD_PATH = sys.path[0] + "/sdp_record.xml"
    UUID = "00001124-0000-1000-8000-00805f9b34fb"

    def __init__(self):
        print("2. Setting up BT device")
        self._listen_lock = threading.Lock()
        self._listening = False
        self._profile = None
        self._use_bluez_profile = False
        self.init_bt_device()
        self.init_bluez_profile()

    def uses_bluez_profile(self):
        return self._use_bluez_profile

    def start_listen_thread(self):
        with self._listen_lock:
            if self._listening:
                return
            self._listening = True

        t = threading.Thread(target=self._listen_forever, daemon=True)
        t.start()

    def _listen_forever(self):
        while True:
            try:
                self.listen()
                return
            except Exception as err:
                error(err)
                time.sleep(2)

    # configure the bluetooth hardware device
    def init_bt_device(self):
        print("3. Configuring Device name " + BTKbDevice.MY_DEV_NAME)
        # set the device class to a keybord and set the name
        os.system("hciconfig hci0 up")
        os.system("hciconfig hci0 name " + BTKbDevice.MY_DEV_NAME)
        # make the device discoverable
        os.system("hciconfig hci0 piscan")

        # Also set via BlueZ (more reliable than hciconfig on some setups)
        try:
            ensure_adapter_discoverable(dbus.SystemBus())
        except Exception as ex:
            warning("ensure_adapter_discoverable failed: %s", ex)

    # set up a bluez profile to advertise device capabilities from a loaded service record
    def init_bluez_profile(self):
        print("4. Configuring Bluez Profile")
        # setup profile options
        service_record = self.read_sdp_service_record()
        opts = {
            "AutoConnect": True,
            "ServiceRecord": service_record
        }
        # retrieve a proxy for the bluez profile interface
        bus = dbus.SystemBus()

        # Export a Profile1 object at a dedicated path; if registration succeeds,
        # BlueZ will call NewConnection.
        self._profile = BTKbProfile(bus, self, PROFILE_PATH)

        manager = dbus.Interface(bus.get_object(
            "org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")

        # Best-effort cleanup if we previously registered this exact path.
        try:
            manager.UnregisterProfile(PROFILE_PATH)
        except dbus.exceptions.DBusException:
            pass

        try:
            manager.RegisterProfile(PROFILE_PATH, BTKbDevice.UUID, opts)
            self._use_bluez_profile = True
            print("6. Profile registered (via BlueZ ProfileManager1)")
        except dbus.exceptions.DBusException as ex:
            # Common when another daemon/plugin already owns this UUID.
            warning("RegisterProfile skipped (%s). Falling back to raw L2CAP sockets.", ex)
            self._use_bluez_profile = False

        os.system("hciconfig hci0 class 0x002540")

    def on_new_connection(self, fd, properties):
        try:
            raw_fd = fd.take() if hasattr(fd, "take") else int(fd)
        except Exception:
            raw_fd = int(fd)

        try:
            sock = socket.fromfd(raw_fd, socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
        except OSError as ex:
            error("fromfd failed: %s", ex)
            return

        # Duplicate to avoid closing the underlying fd unexpectedly.
        sock = sock.dup()

        psm = None
        try:
            psm = int(properties.get("PSM")) if "PSM" in properties else None
        except Exception:
            psm = None

        # HID uses 17 (control) and 19 (interrupt). If unknown, best-effort assign.
        if psm == self.P_CTRL or (psm is None and not hasattr(self, "ccontrol")):
            self.ccontrol = sock
            info("Control channel connected (PSM=%s)", psm)
        elif psm == self.P_INTR or (psm is None and not hasattr(self, "cinterrupt")):
            self.cinterrupt = sock
            info("Interrupt channel connected (PSM=%s)", psm)
        else:
            # Extra/unexpected connection; keep it as interrupt fallback if unset.
            if not hasattr(self, "cinterrupt"):
                self.cinterrupt = sock
                info("Unknown channel assigned to interrupt (PSM=%s)", psm)
            else:
                warning("Unknown extra connection ignored (PSM=%s)", psm)
                try:
                    sock.close()
                except Exception:
                    pass

    def on_disconnection(self):
        for attr in ("ccontrol", "cinterrupt"):
            s = getattr(self, attr, None)
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass
                try:
                    delattr(self, attr)
                except Exception:
                    pass

    # read and return an sdp record from a file
    def read_sdp_service_record(self):
        print("5. Reading service record")
        try:
            fh = open(BTKbDevice.SDP_RECORD_PATH, "r")
        except:
            sys.exit("Could not open the sdp record. Exiting...")
        return fh.read()

    def setup_socket(self):
        self.scontrol = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        self.sinterrupt = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind these sockets to a port - port zero to select next available
        self.scontrol.bind((socket.BDADDR_ANY, self.P_CTRL))
        self.sinterrupt.bind((socket.BDADDR_ANY, self.P_INTR))

    # listen for incoming client connections
    def listen(self):
        print("\033[0;33m7. Waiting for connections\033[0m")

        # key point: use connect to get the host request for the accept() below
        # it work, I just dont care for having been into it for 2days
        self.setup_socket()
        try:
            # must be ahead of listen or 'File descriptor in bad state'
            self.scontrol.connect((TARGET_ADDRESS, self.P_CTRL))
        except socket.error as err:
            # it was expect to failed
            print("Connect failed: "+str(err))

        # this may not work
        # os.system("bluetoothctl connect " + TARGET_ADDRESS)

        self.setup_socket()

        # Start listening on the server sockets
        self.scontrol.listen(5)
        self.sinterrupt.listen(5)

        self.ccontrol, cinfo = self.scontrol.accept()
        print (
            "\033[0;32mGot a connection on the control channel from %s \033[0m" % cinfo[0])

        self.cinterrupt, cinfo = self.sinterrupt.accept()
        print (
            "\033[0;32mGot a connection on the interrupt channel from %s \033[0m" % cinfo[0])

    # send a string to the bluetooth host machine
    def send_string(self, message):
        try:
            if not hasattr(self, 'cinterrupt'):
                self.start_listen_thread()
                return
            self.cinterrupt.send(bytes(message))
        except (AttributeError, OSError) as err:
            error(err)
            self.start_listen_thread()


class BTKbService(dbus.service.Object):

    def __init__(self):
        print("1. Setting up service")
        # set up as a dbus service
        bus_name = dbus.service.BusName(
            "org.thanhle.btkbservice", bus=dbus.SystemBus())
        dbus.service.Object.__init__(
            self, bus_name, "/org/thanhle/btkbservice")
        # create and setup our device
        self.device = BTKbDevice()
        # If BlueZ Profile registration did not succeed, fall back to raw L2CAP sockets.
        if not self.device.uses_bluez_profile():
            self.device.start_listen_thread()

    @dbus.service.method('org.thanhle.btkbservice', in_signature='yay')
    def send_keys(self, modifier_byte, keys):
        print("Get send_keys request through dbus")
        print("key msg: ", keys)
        state = [ 0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0 ]
        state[2] = int(modifier_byte)
        count = 4
        for key_code in keys:
            if(count < 10):
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)

    @dbus.service.method('org.thanhle.btkbservice', in_signature='yay')
    def send_mouse(self, modifier_byte, keys):
        state = [0xA1, 2, 0, 0, 0, 0]
        count = 2
        for key_code in keys:
            if(count < 6):
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)


# main routine
if __name__ == "__main__":
    # we an only run as root
    try:
        if not os.geteuid() == 0:
            sys.exit("Only root can run this script")

        if TARGET_ADDRESS == "":
            sys.exit("Please fill your host mac address in line 26")

        DBusGMainLoop(set_as_default=True)

        bus = dbus.SystemBus()
        register_no_io_agent(bus)
        ensure_adapter_discoverable(bus)

        myservice = BTKbService()
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        sys.exit()
