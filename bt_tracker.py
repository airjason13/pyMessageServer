# bt_state_tracker.py

import os
import json
import time
import threading
from global_def import log

STATE_FILE = "/run/ar_bt_state.json"

class BtStateTracker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BtStateTracker, cls).__new__(cls)
                cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.state = {
            "bt_auth_count": 0,
            "rfcomm_connect_count": 0,
            "last_auth_time": "",
            "last_rfcomm_time": "",
            # 新增當下狀態追蹤
            "is_bt_authorized": False,
            "is_rfcomm_connected": False
        }
        self.file_lock = threading.Lock()
        # 如果程式重啟但系統沒重啟，嘗試載入舊紀錄
        self._load()

    def _load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    self.state.update(json.load(f))
            except Exception as e:
                log.error(f"[BT_STATE] Load state failed: {e}")

    def _save(self):
        with self.file_lock:
            try:
                # 實作 Atomic Write (先寫入暫存檔再 Rename，防止其他程式讀到殘缺資料)
                tmp_file = STATE_FILE + ".tmp"
                with open(tmp_file, 'w') as f:
                    json.dump(self.state, f, indent=4)
                os.rename(tmp_file, STATE_FILE)
            except Exception as e:
                log.error(f"[BT_STATE] Save state error: {e}")

    def add_bt_auth(self):
        self.state["bt_auth_count"] += 1
        self.state["last_auth_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save()
        log.debug(f"[BT_STATE] Auth Count: {self.state['bt_auth_count']}")

    def add_rfcomm_connect(self):
        self.state["rfcomm_connect_count"] += 1
        self.state["last_rfcomm_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save()
        log.debug(f"[BT_STATE] RFCOMM Count: {self.state['rfcomm_connect_count']}")

    def set_bt_authorized(self, status: bool):
        self.state["is_bt_authorized"] = status
        if status:
            self.state["bt_auth_count"] += 1
            self.state["last_auth_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save()

    def set_rfcomm_connected(self, status: bool):
        self.state["is_rfcomm_connected"] = status
        if status:
            self.state["rfcomm_connect_count"] += 1
            self.state["last_rfcomm_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save()