import os
import time
import threading
import select
import termios
import tty

from PyQt5.QtCore import QObject, pyqtSignal

from global_def import *


class BtRfcommTransport(QObject):

    bt_data_received = pyqtSignal(str, tuple)
    bt_disconnected = pyqtSignal(tuple)

    def __init__(self, dev_path="/dev/rfcomm0"):
        super().__init__()

        self.dev_path = dev_path
        self._running = False
        self._thread = None
        self._fd = None

        self.bt_addr = ("bt_client", 1)
        self.encoding = "utf-8"

        self._io_lock = threading.Lock()

        # 8 KB read buffer
        self.read_chunk_size = 8192

    def start(self):
        if self._running:
            log.debug("[BT] transport already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._read_loop,
            daemon=True
        )
        self._thread.start()

        log.debug(f"[BT] start transport: {self.dev_path}")

    def stop(self):
        self._running = False
        self._close_fd()
        log.debug("[BT] stop transport")

    def send(self, msg: str):
        try:
            if self._fd is None:
                log.debug("[BT] send skipped: rfcomm not connected")
                return False

            if not msg.endswith("\n"):
                msg += "\n"

            data = msg.encode(self.encoding)

            with self._io_lock:
                os.write(self._fd, data)
                termios.tcflush(self._fd, termios.TCIFLUSH)
            log.debug(f"[BT] TX: {msg.strip()}")
            return True

        except Exception as e:
            log.debug(f"[BT] send error: {e}")
            self._close_fd()
            return False

    def _set_raw_no_echo(self):
        if self._fd is None:
            return

        try:
            tty.setraw(self._fd)

            attrs = termios.tcgetattr(self._fd)

            attrs[0] &= ~(
                termios.IGNBRK |
                termios.BRKINT |
                termios.PARMRK |
                termios.ISTRIP |
                termios.INLCR |
                termios.IGNCR |
                termios.ICRNL |
                termios.IXON
            )

            attrs[1] &= ~(termios.OPOST)

            attrs[2] |= termios.CS8

            attrs[3] &= ~(
                termios.ECHO |
                termios.ECHOE |
                termios.ECHOK |
                termios.ECHONL |
                termios.ICANON |
                termios.ISIG |
                termios.IEXTEN
            )

            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 1

            termios.tcsetattr(self._fd, termios.TCSANOW, attrs)

            log.debug("[BT] set raw no-echo")

        except Exception as e:
            log.debug(f"[BT] set raw no-echo error: {e}")

    def _close_fd(self):
        try:
            if self._fd is not None:
                os.close(self._fd)
        except Exception:
            pass

        self._fd = None

    def _cleanup_msg(self, msg: str) -> str:
        msg = msg.strip()
        msg = msg.replace("^J", "")
        msg = msg.replace("\r", "")
        msg = msg.replace("\n", "")
        msg = msg.strip()
        return msg

    def _is_valid_mobile_msg(self, msg: str) -> bool:
        if "idx:" not in msg or "cmd:" not in msg:
            log.debug(f"[BT] drop invalid RX: {msg}")
            return False

        # BT RX should only accept commands from Mobile
        if "src:Mobile" not in msg and "src:mobile" not in msg:
            log.debug(f"[BT] drop non-mobile RX: {msg}")
            return False

        # Drop Message Server response echo
        if "src:msg" in msg or "dst:mobile" in msg:
            log.debug(f"[BT] drop echo RX: {msg}")
            return False

        return True

    def _read_loop(self):
        buffer = b""

        while self._running:
            try:
                if not os.path.exists(self.dev_path):
                    time.sleep(1)
                    continue

                log.debug(f"[BT] open {self.dev_path}")

                self._fd = os.open(
                    self.dev_path,
                    os.O_RDWR | os.O_NOCTTY
                )

                self._set_raw_no_echo()

                log.debug("[BT] connected")

                buffer = b""

                while self._running and self._fd is not None:
                    rlist, _, _ = select.select(
                        [self._fd],
                        [],
                        [],
                        1.0
                    )

                    if not rlist:
                        continue

                    with self._io_lock:
                        chunk = os.read(
                            self._fd,
                            self.read_chunk_size
                        )

                    if not chunk:
                        log.debug("[BT] disconnected")
                        self.bt_disconnected.emit(self.bt_addr)
                        break

                    # Do not enable this for image transfer.
                    # log.debug(f"[BT] RX raw: {chunk!r}")

                    buffer += chunk

                    while b"\n" in buffer:
                        raw_msg, buffer = buffer.split(b"\n", 1)

                        if not raw_msg:
                            continue

                        msg = raw_msg.decode(
                            self.encoding,
                            errors="ignore"
                        )

                        msg = self._cleanup_msg(msg)

                        if not msg:
                            continue
                        '''
                        if "src:msg" in msg:
                             log.debug("[BT] clear buffer on echo RX")
                             buffer = b""
                             continue
                        '''

                        if not self._is_valid_mobile_msg(msg):
                            continue

                        log.debug(f"[BT] RX: {msg}")

                        self.bt_data_received.emit(
                            msg,
                            self.bt_addr
                        )

            except Exception:
                log.exception("[BT] loop error")

            self._close_fd()
            time.sleep(1)
