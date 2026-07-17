import platform

import utils.log_utils
from arglassescmd.cmd_def import *
from version import *
LOG_FILE_PREFIX = "msg_server.log"

log = utils.log_utils.logging_init(__file__, LOG_FILE_PREFIX)

TCP_PORT = 9527
UDP_PORT = 9528

TCP_MAX_PACKET_SIZE = 8*1024*1024 # 4096
UNIX_SOCKET_BUFFER_SIZE = 8*1024*1024

MOBILE_TCP_PORT_DEFAULT = 55688

# WiFi Configuration
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

# Bluetooth Configuration

'''
BT_NAME is a default bt device name.
1. find the prefix of the bt_name defined in BT_CONF_URI
2. find the tail of the bt mac with bluetoothctl
3. The final BT_NAME show in device is {prefix_bt_name}_{tail_bt_mac}
Upon method is wrote in bt_init.py.
If there is no BT_CONF_URI or no bt_name defined in BT_CONF_URI, 
use the default BT_NAME defined in global_def.py. 
'''
BT_NAME = "GIS_AR"
BT_CLASS = "0x000704"  # Device Identifie
'''
    Class: 0x000704
	Service Classes: Unspecified
	Device Class: Uncategorized, Wrist Watch
	If audio in CLASS, rfcomm will be jammed.
'''
#BT_CLASS = "0x2c0000"  # Device Identifie

BT_RFCOMM_CMD_DEV = "/dev/rfcomm0"
BT_RFCOMM_DATA_DEV = "/dev/rfcomm1"
BT_RFCOMM_CMD_CHANNEL = 1
BT_RFCOMM_DATA_CHANNEL = 2
BT_FORWARD_UNIX_ACK = True
