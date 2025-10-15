import asyncio


from PyQt5.QtCore import QObject, pyqtSignal
from global_def import *


class TCPServer(QObject):
    tcp_data_received = pyqtSignal(str, tuple)
    def __init__(self, host: str = "127.0.0.1", port: int = MOBILE_TCP_PORT_DEFAULT, parser=None):
        super().__init__()
        self.host_ip = host
        self.host_port = port
        self.reader = None
        self.writer = None

    async def connect(self):
        log.debug(f"Connecting to {self.host_ip}:{self.host_port}")
        self.reader, self.writer = await asyncio.open_connection(self.host_ip, self.host_port)
        if self.reader and self.writer is not None:
            log.debug(f"Connected to {self.host_ip}:{self.host_port} ok")

    async def send(self, send_data: str):
        try:
            if self.writer:
                self.writer.write(send_data.encode())
                await self.writer.drain()
                await asyncio.sleep(0.01)
                data = await self.reader.read(TCP_MAX_PACKET_SIZE)
                log.debug(f"Received from {self.host_ip}:{self.host_port}: {data}")
                await asyncio.sleep(0.01)
        except Exception as e:
            log.debug(e)

