import logging
import threading

from PyQt5.QtCore import QObject, pyqtSignal

from global_def import *
import asyncio
import signal
from typing import Optional, Tuple
from msg_check import MsgChecker, CheckerType

# ---------------- TCP Server ----------------
class TCPServer(QObject):
    tcp_data_received = pyqtSignal(str, tuple)
    mobile_disconnected = pyqtSignal(tuple)
    mobile_connected = pyqtSignal(str)
    def __init__(self, host: str = "127.0.0.1", port: int = TCP_PORT, parser=None):
        super().__init__()
        self.host = host
        self.port = port
        self._server: Optional[asyncio.base_events.Server] = None
        self._serve_task: Optional[asyncio.Task] = None
        self.parser = parser

    def is_data_valid(self, data:str) -> str:
        try:
            d = dict(item.split(':', 1) for item in data.split(';'))
        except ValueError:
            log.error(f"Invalid msg format : {data}")
            return STR_REPLY_NG
        return STR_REPLY_OK

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        log.debug("[TCP] + Connection from %s", addr)
        try:
            while True:
                data = await reader.read(TCP_MAX_PACKET_SIZE)
                if not data:
                    break
                msg = data.decode(errors="ignore")
                log.debug("[TCP]   Received: %s from %s", msg, addr)
                ok_or_ng = self.is_data_valid(msg)
                writer.write(f"{msg}".encode() + f"{ok_or_ng}".encode())
                await writer.drain()
                if ok_or_ng == STR_REPLY_OK:
                    # parse to armessageserver to handle
                    self.tcp_data_received.emit(msg, addr)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.debug("[TCP] ! Error with %s ", addr)
            log.debug(f"[TCP] ! Error with {e} ")
        finally:
            log.debug("[TCP] ! Close %s", addr)
            try:
                writer.close()
                await writer.wait_closed()
                self.mobile_disconnected.emit(addr)
            except Exception:
                pass

    async def start(self):
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        sock = self._server.sockets[0].getsockname() if self._server.sockets else (self.host, self.port)
        log.debug("[TCP]   Serving on %s",sock)
        self._serve_task = asyncio.create_task(self._server.serve_forever())

    async def stop(self):
        if self._server is not None:
            log.debug("[TCP]   Shutting down...")
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._serve_task:
            self._serve_task.cancel()
            try:
                await self._serve_task
            except asyncio.CancelledError:
                pass
            self._serve_task = None


