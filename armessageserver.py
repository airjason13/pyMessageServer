import asyncio
import signal
from sys import argv

from PyQt5.QtCore import QCoreApplication, QObject
from qasync import QEventLoop

from global_def import *
from mobile_client import MobileClient
from tcp_server import TCPServer
from udp_server import UDPServer
from unix_client import UnixClient
from unix_server import UnixServer


class AsyncWorker(QObject):
    """一個在獨立 Thread 中運行 asyncio 事件迴圈的類別"""
    def __init__(self,async_loop,
               tcp_host="127.0.0.1", tcp_port=TCP_PORT,
               udp_host="127.0.0.1", udp_port=UDP_PORT,
               unix_server_path=UNIX_MSG_SERVER_URI):
        super().__init__()
        self.loop = async_loop
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.unix_server_path = unix_server_path
        self.tcp_server = None
        self.udp_server = None
        self.unix_server = None
        self.mobile_clients: list[MobileClient] = [] # 可以有多各mobile同時連線ar glasses
        self.demo_app_unix_client = None
        self.le_app_unix_client = None
        self.sys_app_unix_client = None
        self.int_mobile_cmd_idx = 0



    async def custom_parser(data: bytes, addr):
        return 0

    def handle_msg_cmd(self, data, addr):
        msg = data
        d = dict(item.split(":", 1) for item in msg.split(";"))
        log.debug("handle_msg_cmd result: %s", d)
        log.debug("d['cmd'] result: %s", d['cmd'])
        log.debug("d['cmd'].strip() result: %s", d['cmd'].strip())
        if MSG_SPEC_HELLO in d['cmd']:    # mobile 第一個command,說明了mobile 的tcp server port是多少
            log.debug("len(self.mobile_clients): %d", len(self.mobile_clients))
            # 檢查是否已經有了mobile_client指向此 mobile server
            got_client = 0
            if len(self.mobile_clients) > 0:
                for c in self.mobile_clients:
                    if c.mobile_host_ip == addr[0]:
                        got_client = 1
                        break
            else:
                pass
            if got_client == 0:
                mobile_client = MobileClient(addr[0], d['data'].split("=")[1])
                self.mobile_clients.append(mobile_client)

                asyncio.run_coroutine_threadsafe(
                    mobile_client.connect(),
                    self.loop
                )

    ''' 處理 tcp recv data '''
    def tcp_data_recv_handler(self, data:str, addr:tuple):
        log.debug(f"Recv: {data} from {addr}")
        d = dict(item.split(':', 1) for item in data.split(';'))
        self.int_mobile_cmd_idx = int(d['idx'])
        log.debug(f"self.int_mobile_cmd_idx: {self.int_mobile_cmd_idx}")
        try:
            # 如果cmd start with "msg", 不用傳unix msg
            if 'cmd:msg' in data:
                self.handle_msg_cmd(data, addr)
            else:
                # self._periodic_unix_msg(data)
                self._periodic_unix_msg(d)
        except asyncio.CancelledError:
            log.debug("Cancelled")
        except Exception as e:
            log.debug(e)

    def send_msg_to_mobile(self, send_data:str):
        log.debug(f"Send: {send_data}")
        for c in self.mobile_clients:
            asyncio.run_coroutine_threadsafe(
                c.send(send_data),
                self.loop
            )

    # mobile 斷線後要把tcp client 清除
    def mobile_client_disconnect(self, tuple):
        log.debug(f"mobile_client_disconnect: {tuple}")
        for c in self.mobile_clients:
            if c.mobile_host_ip == tuple[0]:
                log.debug(f"disconnect mobile_client mobile_host_ip : {c.mobile_host_ip}")
                log.debug(f"disconnect mobile_client mobile_tcp_port : {c.mobile_tcp_port}")
                self.mobile_clients.remove(c)
        log.debug("len(self.mobile_clients): %d", len(self.mobile_clients))


    async def start_all_server(self):
        log.debug("")
        self.tcp_server = TCPServer(self.tcp_host, self.tcp_port)
        self.tcp_server.tcp_data_received.connect(self.tcp_data_recv_handler)
        self.tcp_server.mobile_disconnected.connect(self.mobile_client_disconnect)
        self.udp_server = UDPServer(self.udp_host, self.udp_port)
        self.unix_server = UnixServer(self.unix_server_path)
        self.unix_server.send_msg_to_mobile.connect(self.send_msg_to_mobile)
        self.demo_app_unix_client = UnixClient(UNIX_DEMO_APP_SERVER_URI)
        self.le_app_unix_client = UnixClient(UNIX_LE_SERVER_URI)
        self.sys_app_unix_client = UnixClient(UNIX_SYS_SERVER_URI)
        await self.tcp_server.start()
        await self.udp_server.start()
        await self.unix_server.start()
        await self.demo_app_unix_client.connect()
        await self.le_app_unix_client.connect()
        await self.sys_app_unix_client.connect()
        ''''# === 測試用 新增：每 5 秒觸發一次 test_send_unix_msg ===
        self.timer = QTimer(self)
        self.timer.setInterval(5000)  # 5 秒
        self.timer.timeout.connect(self._periodic_unix_msg)
        self.timer.start()'''

    def _periodic_unix_msg(self, data: dict) -> None:
        """
        QTimer 觸發時呼叫，安排 coroutine 到 asyncio 事件迴圈
        """
        log.debug("")
        # 例如傳送字串 "Hello from QTimer"
        asyncio.run_coroutine_threadsafe(
            self.test_send_unix_msg(data),
            self.loop
        )

    async def test_send_unix_msg(self, unix_msg_dict:dict):
        log.debug("test_unix_loop")
        if unix_msg_dict is None:
            return


        if unix_msg_dict.get('cmd').startswith('le'):
            prefix_s = f"idx:{unix_msg_dict['idx']};src:mobile;dst:le;"
            log.debug(f"prefix_s: {prefix_s}")
            if unix_msg_dict.get('data') is None:
                await self.le_app_unix_client.send(prefix_s + "cmd:" + unix_msg_dict['cmd'])
            else:
                await self.le_app_unix_client.send(prefix_s + "cmd:" + unix_msg_dict['cmd'] + ";data:" + unix_msg_dict['data'])
        elif unix_msg_dict.get('cmd').startswith('demo'):
            prefix_s = f"idx:{unix_msg_dict['idx']};src:mobile;dst:demo;"
            log.debug(f"prefix_s: {prefix_s}")
            log.debug(f"d['cmd']: {unix_msg_dict['cmd']}")
            if unix_msg_dict.get('data') is None:
                await self.demo_app_unix_client.send(prefix_s + "cmd:" + unix_msg_dict['cmd'])
            else:
                await self.demo_app_unix_client.send(prefix_s + "cmd:" + unix_msg_dict['cmd'] + ";data:" + unix_msg_dict['data'])
        elif unix_msg_dict.get('cmd').startswith('sys'):
            prefix_s = f"idx:{unix_msg_dict['idx']};src:mobile;dst:sys;"
            log.debug(f"prefix_s: {prefix_s}")
            log.debug(f"d['cmd']: {unix_msg_dict['cmd']}")
            if unix_msg_dict.get('data') is None:
                await self.sys_app_unix_client.send(prefix_s + "cmd:" + unix_msg_dict['cmd'])
            else:
                await self.sys_app_unix_client.send(prefix_s + "cmd:" + unix_msg_dict['cmd'] + ";data:" + unix_msg_dict['data'])




    async def async_job(self, cmd:str, data=None):

        log.debug("[%s] start", cmd)
        if "initial" in cmd:
            await self.start_all_server()
        elif "test_unix_loop" in cmd:
            await self.test_send_unix_msg(data)
        log.debug("[%s] end", cmd)


    def run(self):
        """Thread 進入點：設定並啟動事件迴圈"""
        asyncio.set_event_loop(self.loop)
        # 在啟動時排程一個 coroutine
        self.loop.create_task(self.async_job("initial",))
        log.debug("[AsyncWorker] event loop running ...")
        self.loop.run_forever()

    def add_task(self, name, data):
        """從主線程安排新的 coroutine"""
        asyncio.run_coroutine_threadsafe(self.async_job(name, data), self.loop)

    def stop(self):
        """安全關閉事件迴圈"""
        self.loop.call_soon_threadsafe(self.loop.stop)


def main():
    log.debug(f"Welcome {Version}")
    # 使用 QCoreApplication 取代 QApplication，不需要 GUI 子系統
    app = QCoreApplication(argv)
    # 用 qasync 把 Qt 事件迴圈包裝成 asyncio 事件迴圈
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    worker = AsyncWorker(loop, tcp_host=LOCAL_IP, udp_host=LOCAL_IP)


    # 友善的 Ctrl+C 結束
    def handle_sigint(*_):
        print("\n[Main] SIGINT received, quitting ...")
        app.quit()

    # Unix 下可用 add_signal_handler，跨平台保險也掛一個 signal.signal
    try:
        loop.add_signal_handler(signal.SIGINT, handle_sigint)
    except NotImplementedError:
        pass
    signal.signal(signal.SIGINT, handle_sigint)

    log.debug("Run AsyncWorker")
    worker.run()


if __name__ == "__main__":
    main()
