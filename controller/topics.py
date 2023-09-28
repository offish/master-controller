PREFIX = "hydroplant/"

# mqtt topics
# sub
DEVICE_TOPIC = PREFIX + "device"
LOG_TOPIC = PREFIX + "log"
SYNC_TOPIC = PREFIX + "gui/sync"
AUTONOMY_TOPIC = PREFIX + "gui_command/autonomy"
DEVICES_DISCONNECT_TOPIC = PREFIX + "disconnected/devices"
IS_READY_TOPIC = PREFIX + "is_ready"
TEMP_TEST_TOPIC = PREFIX + "measurement/#"

# pub
GUI_TOPICS = PREFIX + "gui/topics"
READY_TOPIC = PREFIX + "ready"
MASTER_DISCONNECT_TOPIC = PREFIX + "disconnected/master_controller"
# commonly used
GUI_COMMAND = PREFIX + "gui_command/"
GUI_LOG = PREFIX + "gui/log"
