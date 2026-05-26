import subprocess
import threading
import time

from global_def import *
from auto_agent import AutoAgent

class BtInitializer:

    def __init__(
        self,
        bt_name=BT_NAME,
        bt_class=BT_CLASS,
        bluetoothd_path="/usr/libexec/bluetooth/bluetoothd",
    ):

        self.bt_name = bt_name
        self.bt_class = bt_class
        self.bluetoothd_path = bluetoothd_path

        self.bluetoothd_proc = None
        self.rfcomm_procs = {}
        self.rfcomm_locks = {}
        self.agent = None
        self._rfcomm_recovery_lock = threading.Lock()
        self._rfcomm_recovery_running = False


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

        # register SPP services
        self.run(
            f"sdptool add --channel={BT_RFCOMM_CMD_CHANNEL} SP || true"
        )

        self.run(
            f"sdptool add --channel={BT_RFCOMM_DATA_CHANNEL} SP || true"
        )

        # start rfcomm listeners
        self.start_rfcomm_listener(
            BT_RFCOMM_CMD_DEV,
            BT_RFCOMM_CMD_CHANNEL,
        )

        self.start_rfcomm_listener(
            BT_RFCOMM_DATA_DEV,
            BT_RFCOMM_DATA_CHANNEL,
        )

        log.debug("[BT_INIT] done")

    def start_rfcomm_listener(self, dev_path, channel):
        log.debug("[BT_INIT] start rfcomm listener dev=%s ch=%s", dev_path, channel)

        try:
            # self.stop_rfcomm_listener(dev_path)

            # time.sleep(1)

            proc = subprocess.Popen(
                [
                    "rfcomm",
                    "listen",
                    dev_path,
                    str(channel),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            self.rfcomm_procs[dev_path] = proc

            log.debug(
                "[BT_INIT] rfcomm listener started pid=%s dev=%s channel=%s",
                proc.pid,
                dev_path,
                channel,
            )

        except Exception as e:
            log.debug(f"[BT_INIT] rfcomm listener error dev={dev_path} ch={channel}: {e}")
            self.rfcomm_procs.pop(dev_path, None)

    def restart_rfcomm_listener(self, dev_path, channel):
        lock = self.rfcomm_locks.setdefault(dev_path, threading.Lock())

        with lock:
            try:
                log.debug(
                    "[BT_INIT] restart rfcomm listener dev=%s ch=%s",
                    dev_path,
                    channel,
                )

                self.stop_rfcomm_listener(dev_path)

                time.sleep(1)

                self.start_rfcomm_listener(dev_path, channel)

            except Exception:
                log.debug(
                    "[BT_INIT] restart rfcomm listener failed dev=%s ch=%s",
                    dev_path,
                    channel,
                )

    def stop_rfcomm_listener(self, dev_path=None):
        log.debug("[BT_INIT] stop rfcomm listener dev=%s", dev_path)

        targets = []

        if dev_path is None:
            targets = list(self.rfcomm_procs.keys())
        else:
            targets = [dev_path]

        for path in targets:
            proc = self.rfcomm_procs.get(path)

            try:
                if proc:
                    if proc.poll() is None:
                        log.debug("[BT_INIT] terminate rfcomm pid=%s dev=%s", proc.pid, path)
                        proc.terminate()

                        try:
                            proc.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            log.debug("[BT_INIT] kill rfcomm pid=%s dev=%s", proc.pid, path)
                            proc.kill()
                            proc.wait(timeout=2)
                    else:
                        ret = proc.wait()
                        log.debug("[BT_INIT] rfcomm already exited ret=%s dev=%s", ret, path)

            except Exception as e:
                log.debug(f"[BT_INIT] stop rfcomm error dev={path}: {e}")

            self.rfcomm_procs.pop(path, None)

        if dev_path is None:
            self.run("rfcomm release all || true")
            self.run('pkill -f "rfcomm listen" || true')
        else:
            self.run(f"rfcomm release {dev_path} || true")

    def check_rfcomm_listener(self):
        for dev, ch in [
            (BT_RFCOMM_CMD_DEV, BT_RFCOMM_CMD_CHANNEL),
            (BT_RFCOMM_DATA_DEV, BT_RFCOMM_DATA_CHANNEL),
        ]:
            proc = self.rfcomm_procs.get(dev)

            if proc is None or proc.poll() is not None:
                if proc is not None:
                    try:
                        proc.wait(timeout=0)
                    except Exception:
                        pass
                log.debug(
                    f"[BT_INIT] restart dead rfcomm listener "
                    f"dev={dev} ch={ch}"
                )

                self.rfcomm_procs.pop(dev, None)
                self.start_rfcomm_listener(dev, ch)

    def trigger_rfcomm_recovery(self):
        with self._rfcomm_recovery_lock:
            if self._rfcomm_recovery_running:
                log.debug("[BT_INIT] rfcomm recovery already running, skip")
                return

            self._rfcomm_recovery_running = True

            log.debug(
                "[BT_INIT] rfcomm recovery trigger accepted self=%s",
                id(self),
            )

        threading.Thread(
            target=self._rfcomm_recovery_worker,
            name="rfcomm-recovery",
            daemon=True,
        ).start()

    def _rfcomm_recovery_worker(self):
        log.debug(
            "[BT_INIT] rfcomm recovery worker start self=%s",
            id(self),
        )

        try:
            max_rounds = 10
            interval_sec = 2

            for round_idx in range(1, max_rounds + 1):

                try:
                    log.debug(
                        "[BT_INIT] rfcomm recovery round=%d",
                        round_idx,
                    )

                    cmd_ok = self.ensure_rfcomm_listener(
                        BT_RFCOMM_CMD_DEV,
                        BT_RFCOMM_CMD_CHANNEL,
                    )

                    data_ok = self.ensure_rfcomm_listener(
                        BT_RFCOMM_DATA_DEV,
                        BT_RFCOMM_DATA_CHANNEL,
                    )

                    if cmd_ok and data_ok:
                        log.debug("[BT_INIT] rfcomm recovery success")
                        return

                except Exception:
                    log.debug("[BT_INIT] rfcomm recovery round failed")

                time.sleep(interval_sec)

            log.error("[BT_INIT] rfcomm recovery failed after retry")

        finally:
            with self._rfcomm_recovery_lock:
                self._rfcomm_recovery_running = False

            log.debug(
                "[BT_INIT] rfcomm recovery worker exit self=%s",
                id(self),
            )

    def ensure_rfcomm_listener(self, dev_path, channel):
        try:
            if self.is_rfcomm_listener_alive(dev_path):
                return True

            log.debug(
                "[BT_INIT] rfcomm listener not alive, restart dev=%s ch=%s",
                dev_path,
                channel,
            )

            self.restart_rfcomm_listener(dev_path, channel)

            time.sleep(0.5)

            return self.is_rfcomm_listener_alive(dev_path)

        except Exception:
            log.debug(
                "[BT_INIT] ensure rfcomm listener failed dev=%s ch=%s",
                dev_path,
                channel,
            )

            return False

    def is_rfcomm_listener_alive(self, dev_path):
        proc = self.rfcomm_procs.get(dev_path)

        if proc is None:
            return False

        return proc.poll() is None
