import asyncio
import os
from typing import Optional

from PyQt5.QtCore import pyqtSignal, QObject

from global_def import *

# ---------------- Unix Socket Server ----------------
class UnixServer(QObject):

    send_msg_to_mobile = pyqtSignal(str)
    def __init__(self, path: str = UNIX_MSG_SERVER_URI):
        super().__init__()
        self.path = path
        self._server: Optional[asyncio.base_events.Server] = None
        self._task: Optional[asyncio.Task] = None

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        # print(f"[UnixServer] + Connection {addr}")
        log.debug("[UnixServer] + Connection %s", addr)
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                msg = data.decode(errors="ignore")
                # print(f"[UnixServer]   Received: {msg}")
                log.debug("[UnixServer] + Received: %s", msg)
                writer.write(f"{msg}".encode() + STR_REPLY_OK.encode())
                await writer.drain()
                # 如果要送到mobile的話
                if 'dst:mobile' in msg:
                    # 先將msg轉成dict, 在替換掉src
                    d = dict(item.split(":", 1) for item in msg.split(";"))
                    if d.get("src") in ("le", "sys", "demo"):
                        d["src"] = "msg"
                        result = ";".join(f"{k}:{v}" for k, v in d.items())
                        log.debug("result: %s", result)
                        self.send_msg_to_mobile.emit(result)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.debug(e)
        finally:
            log.debug("[UnixServer] + Close: %s", addr)
            writer.close()
            await writer.wait_closed()

    async def start(self):
        # 確保不存在舊 socket 檔案
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

        self._server = await asyncio.start_unix_server(self._handle_client, path=self.path)
        # print(f"[UnixServer] Serving at {self.path}")
        log.debug("[UnixServer] Serving at %s", self.path)
        self._task = asyncio.create_task(self._server.serve_forever())

    async def stop(self):
        if self._server is not None:
            # print("[UnixServer] Shutting down...")
            log.debug("[UnixServer] Shutting down...")
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        # 移除 socket 檔案
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass