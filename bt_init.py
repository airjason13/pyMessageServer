import subprocess
import time

from global_def import *
from auto_agent import AutoAgent

class BtInitializer:

    def __init__(
        self,
        bt_name=BT_NAME,
        bt_class=BT_CLASS,
        channel=BT_RFCOMM_CHANNEL,
        bluetoothd_path="/usr/libexec/bluetooth/bluetoothd",
    ):

        self.bt_name = bt_name
        self.bt_class = bt_class
        self.channel = channel
        self.bluetoothd_path = bluetoothd_path

        self.bluetoothd_proc = None
        self.rfcomm_proc = None
        self.agent = None


    def run(self, cmd: str):

        log.debug(f"[BT_INIT] CMD: {cmd}")

        return subprocess.run(
            cmd,
            shell=True,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def init(self):

        log.debug("[BT_INIT] start")

        # cleanup old state
        self.run("systemctl stop bluetooth || true")

        # kill old rfcomm listener only
        self.run('pkill -f "rfcomm listen" || true')

        # kill old bluetoothd
        self.run("killall bluetoothd || true")
        time.sleep(1)

        # start bluetoothd compatibility mode
        self.bluetoothd_proc = subprocess.Popen(
            [
                self.bluetoothd_path,
                "-C",
                "-n"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # wait bluetoothd ready
        time.sleep(2)

        # controller init
        self.run("modprobe btnxpuart || true")

        self.run("hciconfig hci0 up || true")

        self.run(
            f"hciconfig hci0 name {self.bt_name} || true"
        )

        self.run(
            f"hciconfig hci0 class {self.bt_class} || true"
        )

        self.run("hciconfig hci0 piscan || true")

        # wait hci0 ready
        for _ in range(10):

            result = subprocess.run(
                "hciconfig hci0",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            if result.returncode == 0:
                break

            time.sleep(1)

        # power / discoverable / pairable
        self.run(
            """bluetoothctl <<EOF
        power on
        discoverable on
        pairable on
        EOF"""
        )

        # start auto pairing agent
        self.agent = AutoAgent()
        self.agent.start()

        # register SPP service
        self.run(
            f"sdptool add --channel={self.channel} SP || true"
        )

        # start rfcomm listener
        self.start_rfcomm_listener()

        log.debug("[BT_INIT] done")

    def start_rfcomm_listener(self):
        log.debug("[BT_INIT] start rfcomm listener")

        try:
            self.stop_rfcomm_listener()

            time.sleep(1)

            self.rfcomm_proc = subprocess.Popen(
                [
                    "rfcomm",
                    "listen",
                    "/dev/rfcomm0",
                    str(self.channel),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            log.debug(
                "[BT_INIT] rfcomm listener started pid=%s channel=%s",
                self.rfcomm_proc.pid,
                self.channel,
            )

        except Exception as e:
            log.debug(f"[BT_INIT] rfcomm listener error: {e}")
            self.rfcomm_proc = None

    def restart_rfcomm_listener(self):
        log.debug("[BT_INIT] restart rfcomm listener")

        self.stop_rfcomm_listener()
        time.sleep(1)
        self.start_rfcomm_listener()

    def stop_rfcomm_listener(self):
        log.debug("[BT_INIT] stop rfcomm listener")

        try:
            if self.rfcomm_proc:
                if self.rfcomm_proc.poll() is None:
                    log.debug("[BT_INIT] terminate rfcomm pid=%s", self.rfcomm_proc.pid)
                    self.rfcomm_proc.terminate()

                    try:
                        self.rfcomm_proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        log.debug("[BT_INIT] kill rfcomm pid=%s", self.rfcomm_proc.pid)
                        self.rfcomm_proc.kill()
                        self.rfcomm_proc.wait(timeout=2)
                else:
                    # child already exited, reap it
                    ret = self.rfcomm_proc.wait()
                    log.debug("[BT_INIT] rfcomm already exited ret=%s", ret)

                self.rfcomm_proc = None

        except Exception as e:
            log.debug(f"[BT_INIT] stop rfcomm error: {e}")

        # release kernel rfcomm binding
        self.run("rfcomm release all || true")

        # cleanup possible orphan rfcomm listen
        self.run('pkill -f "rfcomm listen" || true')

    def check_rfcomm_listener(self):
        """
        Check whether rfcomm listen process is still alive.
        If exited, reap it and restart listener.
        """

        if not self.rfcomm_proc:
            log.debug("[BT_INIT] rfcomm_proc is None, restart listener")
            self.start_rfcomm_listener()
            return

        ret = self.rfcomm_proc.poll()

        if ret is not None:
            log.debug("[BT_INIT] rfcomm listener exited ret=%s, restart", ret)

            try:
                self.rfcomm_proc.wait(timeout=1)
            except Exception:
                pass

            self.rfcomm_proc = None
            self.start_rfcomm_listener()