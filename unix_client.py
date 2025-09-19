import asyncio
import os
from typing import Optional
from global_def import *


class UnixClient:
    def __init__(self, path: str = "/tmp/ipc_socket.sock"):
        self.path = path
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None


    async def connect(self):
        log.debug("[UnixClient] Connecting...")
        self.reader = None
        self.writer = None
        try:
            self.reader, self.writer = await asyncio.open_unix_connection(self.path)
            log.debug(f"[UnixClient] Connected to {self.path}")
        except Exception as e:
            log.debug(f"[UnixClient] Failed to connect to {self.path}: {e}")

    async def reconnect(self):
        log.debug("[UnixClient] Reconnecting...")
        await self.close()
        log.debug("[UnixClient] Connect")
        await self.connect()

    async def send(self, msg: str):
        if self.reader is None or self.writer is None:
            await self.connect()
        if self.writer is None:
            raise RuntimeError("Client not connected")
        log.debug(f"[UnixClient] Send: {msg}")
        try:
            self.writer.write(msg.encode())
            await self.writer.drain()
        except Exception as e:
            log.debug(f"[UnixClient] Send: {e}")
            await self.reconnect()
            return -1


        data = await self.reader.read(1024)
        log.debug(f"[UnixClient] Received: {data.decode()}")

    async def close(self):
        if self.writer is not None:
            log.debug("[UnixClient] Closing")
            try:
                self.writer.close()
                # ✅ 加超時，且容忍 loop 已停止/錯誤情況
                await asyncio.wait_for(self.writer.wait_closed(), timeout=1.0)
            except (asyncio.TimeoutError, RuntimeError) as e:
                # RuntimeError: loop 已經停止或不是同一個 loop
                log.debug(f"[UnixClient] wait_closed skipped: {e}")
            except Exception as e:
                log.debug(f"[UnixClient] close error: {e}")
        self.writer = None
        self.reader = None
