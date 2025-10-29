import asyncio
import socket

from PyQt5.QtCore import QObject
from global_def import *

class MobileClient(QObject):
    def __init__(self, host: str = "127.0.0.1", port: int = MOBILE_TCP_PORT_DEFAULT, parser=None):
        super().__init__()
        self.mobile_host_ip = host
        self.mobile_tcp_port = port
        self.reader, self.writer = None, None
        self.snd_size = TCP_MAX_PACKET_SIZE  # 4 * 1024 * 1024  # 4 MiB
        self.rcv_size = TCP_MAX_PACKET_SIZE  # 4 * 1024 * 1024

    async def connect(self):
        log.debug(f"Connecting to {self.mobile_host_ip}:{self.mobile_tcp_port}")
        try:
            self.reader, self.writer = await asyncio.open_connection(self.mobile_host_ip, self.mobile_tcp_port)
            if self.reader and self.writer is not None:
                log.debug(f"Connected to {self.mobile_host_ip}:{self.mobile_tcp_port} ok")
            sock = self.writer.get_extra_info("socket")
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.snd_size)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.rcv_size)
            log.debug(f"[UnixClient] Connected to {self.path}")
        except Exception as e:
            log.debug(e)

    async def send(self, send_data: str):
        try:
            if self.writer:
                self.writer.write(send_data.encode())
                await self.writer.drain()
                await asyncio.sleep(0.01)
                data = await self.reader.read(self.rcv_size)
                log.debug(f"Received from {self.mobile_host_ip}:{self.mobile_tcp_port}: {data}")
                await asyncio.sleep(0.01)
        except Exception as e:
            log.debug(e)