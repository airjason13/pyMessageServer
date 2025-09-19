import asyncio
import os
import signal
import inspect
from typing import Optional, Tuple, Callable, Awaitable, Union

CheckerType = Callable[[bytes, Union[Tuple[str, int], str, None]], Union[None, bytes, str, Awaitable[Union[None, bytes, str]]]]

class MsgChecker:
    """
    提供共同的訊息處理層。
    - 可在 __init__ 傳入 parser 回呼，或在子類別 override msg_parser()
    - msg_parser 收到 bytes 與 addr，回傳 bytes/str 或 None（不回覆）
    """
    def __init__(self, parser: Optional[CheckerType] = None, encoding: str = "utf-8"):
        self._external_parser = parser
        self.encoding = encoding

    async def _call_parser(self, data: bytes, addr):
        print("_call_parser")
        """支援注入的同步/非同步 parser；否則呼叫內建的 msg_parser。"""
        if self._external_parser is not None:
            print("_call_parser a")
            res = self._external_parser(data, addr)
            print("_call_parser b")
            if inspect.isawaitable(res):
                res = await res
            return res
        print("_call_parser")
        return await self.msg_parser(data, addr)

    async def msg_parser(self, data: bytes, addr):
        """
        預設行為：Echo（可在子類別覆寫）。
        回傳值：
          - bytes / str：會回傳給對端
          - None：不回覆
        """
        # 預設加上前綴 Echo:
        print("msg_parser")
        try:
            text = data.decode(self.encoding, errors="ignore")
        except Exception as e:
            print(e)
        print("text")
        return text

    @staticmethod
    def _ensure_bytes(resp, encoding="utf-8") -> Optional[bytes]:
        if resp is None:
            return None
        if isinstance(resp, bytes):
            return resp
        if isinstance(resp, str):
            return resp.encode(encoding)
        # 其他型別忽略
        return None