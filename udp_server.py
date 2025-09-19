from typing import Optional, Tuple

from global_def import *
import asyncio

class UDPServer:
    class _Protocol(asyncio.DatagramProtocol):
        def __init__(self, on_ready: asyncio.Future):
            self.transport: Optional[asyncio.transports.DatagramTransport] = None
            self.on_ready = on_ready

        def connection_made(self, transport: asyncio.BaseTransport) -> None:
            self.transport = transport  # type: ignore
            if not self.on_ready.done():
                self.on_ready.set_result(True)
            print("[UDP]   Ready")

        def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
            msg = data.decode(errors="ignore")
            print(f"[UDP]   Received {msg!r} from {addr}")
            if self.transport is not None:
                self.transport.sendto(f"Echo: {msg}".encode(), addr)

        def error_received(self, exc: Exception) -> None:
            print(f"[UDP] ! Error: {exc}")

    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
        self.host = host
        self.port = port
        self._transport: Optional[asyncio.transports.DatagramTransport] = None
        self._protocol: Optional[UDPServer._Protocol] = None

    async def start(self):
        loop = asyncio.get_running_loop()
        on_ready = loop.create_future()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPServer._Protocol(on_ready),
            local_addr=(self.host, self.port),
        )
        self._transport = transport
        self._protocol = protocol  # type: ignore
        await on_ready
        sock = transport.get_extra_info("sockname")
        print(f"[UDP]   Serving on {sock}")

    async def stop(self):
        if self._transport is not None:
            print("[UDP]   Shutting down...")
            self._transport.close()
            self._transport = None
            self._protocol = None

