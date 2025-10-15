import platform

import utils.log_utils
from arglassescmd.cmd_def import *
from version import *
LOG_FILE_PREFIX = "msg_server.log"

log = utils.log_utils.logging_init(__file__, LOG_FILE_PREFIX)

TCP_PORT = 9527
UDP_PORT = 9528

TCP_MAX_PACKET_SIZE = 4096


MOBILE_TCP_PORT_DEFAULT = 55688

if platform.machine() == "aarch64":
    LOCAL_IP = "0.0.0.0"
else:
    LOCAL_IP = "127.0.0.1"

UNIX_MSG_SERVER_URI = '/tmp/ipc_msg_server.sock'
UNIX_DEMO_APP_SERVER_URI = '/tmp/ipc_demo_app_server.sock'
UNIX_SYS_SERVER_URI = '/tmp/ipc_sys_server.sock'
UNIX_LE_SERVER_URI = '/tmp/ipc_le_server.sock'

STR_REPLY_OK = ";OK"
STR_REPLY_NG = ";NG"