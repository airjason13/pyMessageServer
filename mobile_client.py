import asyncio

from PyQt5.QtCore import QObject
from global_def import *

class MobileClient(QObject):
    def __init__(self, host: str = "127.0.0.1", port: int = MOBILE_TCP_PORT_DEFAULT, parser=None):
        super().__init__()
        self.mobile_host_ip = host
        self.mobile_tcp_port = port
        self.reader, self.writer = None, None

    async def connect(self):
        log.debug(f"Connecting to {self.mobile_host_ip}:{self.mobile_tcp_port}")
        self.reader, self.writer = await asyncio.open_connection(self.mobile_host_ip, self.mobile_tcp_port)
        if self.reader and self.writer is not None:
            log.debug(f"Connected to {self.mobile_host_ip}:{self.mobile_tcp_port} ok")

    async def send(self, send_data: str):
        try:
            if self.writer:
                self.writer.write(send_data.encode())
                await self.writer.drain()
                await asyncio.sleep(0.01)
                data = await self.reader.read(1024)
                log.debug(f"Received from {self.mobile_host_ip}:{self.mobile_tcp_port}: {data}")
                await asyncio.sleep(0.01)
        except Exception as e:
            log.debug(e)