# auto_agent.py

import threading

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

from global_def import *


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

AGENT_PATH = "/test/agent"
CAPABILITY = "KeyboardDisplay"


class BluezAutoAgent(dbus.service.Object):

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Release(self):
        log.debug("[BT_AGENT] Release")

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        log.debug(f"[BT_AGENT] AuthorizeService device={device}, uuid={uuid}")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        log.debug(f"[BT_AGENT] RequestAuthorization device={device}")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        log.debug(f"[BT_AGENT] Auto confirm passkey={passkey:06d}, device={device}")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        log.debug(f"[BT_AGENT] RequestPinCode device={device}")
        return "0000"

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        log.debug(f"[BT_AGENT] RequestPasskey device={device}")
        return dbus.UInt32(0)

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        log.debug(f"[BT_AGENT] DisplayPinCode device={device}, pincode={pincode}")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        log.debug(
            f"[BT_AGENT] DisplayPasskey device={device}, "
            f"passkey={passkey:06d}, entered={entered}"
        )
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Cancel(self):
        log.debug("[BT_AGENT] Cancel")


class AutoAgent:

    def __init__(self):
        self.bus = None
        self.agent = None
        self.mainloop = None
        self.thread = None

    def start(self):
        log.debug("[BT_AGENT] start")

        self.bus = dbus.SystemBus()

        self.agent = BluezAutoAgent(
            self.bus,
            AGENT_PATH
        )

        manager = dbus.Interface(
            self.bus.get_object("org.bluez", "/org/bluez"),
            "org.bluez.AgentManager1"
        )

        try:
            manager.UnregisterAgent(AGENT_PATH)
        except Exception:
            pass

        manager.RegisterAgent(
            AGENT_PATH,
            CAPABILITY
        )

        manager.RequestDefaultAgent(
            AGENT_PATH
        )

        self.mainloop = GLib.MainLoop()

        self.thread = threading.Thread(
            target=self.mainloop.run,
            daemon=True
        )

        self.thread.start()

        log.debug(f"[BT_AGENT] ready capability={CAPABILITY}")

    def stop(self):
        try:
            if self.mainloop:
                self.mainloop.quit()
        except Exception:
            pass