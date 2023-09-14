# mqtt topics
# sub
DEVICE_TOPIC = "hydroplant/device"
LOG_TOPIC = "hydroplant/log"
SYNC_TOPIC = "hydroplant/gui/sync"
AUTONOMY_TOPIC = "hydroplant/gui_command/autonomy"

# pub
GUI_TOPICS = "hydroplant/gui/topics"
READY_TOPIC = "hydroplant/ready"

# payload specific
DISALLOWED_KEYS = ["time", "status", "topic"]
