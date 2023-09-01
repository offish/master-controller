from .database import Database
from .config import (
    BROKER_HOST,
    BROKER_PORT,
    DEVICE_TOPIC,
    COMMAND_TOPIC,
    LOG_TOPIC,
    GUI_TOPIC,
)
from .utils import get_last_part, get_second_last_part, get_device_topic

import json

import paho.mqtt.client as mqtt

# actuator
# "hydroplant/actuator/action/waternode/ph"
# "hydroplant/command/waternode/ph"
# "hydroplant/log/waternode/ph"

# sensor
# "hydroplant/sensor/measurement/waternode/ph"
# "hydroplant/log/waternode/ph"

# "hydroplant/command/waternode/light"


class Controller:
    """Controller class for keeping track
    and handling connections to MQTT,
    database and other logic.
    """

    def __init__(self) -> None:
        self.client = mqtt.Client(client_id="master")
        self.db = Database()
        self.all_topics = []
        self.all_devices = []

    def on_connect(self, client, userdata, flags, rc) -> None:
        """Handles MQTT connection to broker
        and subscribes to needed topics.
        """
        print("Connected to", BROKER_HOST, "with result code " + str(rc))
        # print(userdata, flags)

        client.subscribe(DEVICE_TOPIC)

        # subscribe to all gui_commands
        client.subscribe(GUI_TOPIC)

    def on_message(self, client, userdata, msg) -> None:
        """Handles MQTT messages."""
        topic = msg.topic
        data = json.loads(msg.payload)
        print(data)

        node_id = get_second_last_part(topic)
        last_part = get_last_part(topic)

        print("Got a new", last_part, "message from", node_id)

        if "device" in topic:
            # print("Got command from GUI")
            self.setup_device(data)

        if "gui_command" in topic:
            print("Got command from GUI")

            actuator_id = get_last_part(topic)

            command_topic = get_device_topic(
                node_id, actuator_id, self.all_devices
            ).format("command")

            if not command_topic:
                # device does not exist
                client.publish(
                    LOG_TOPIC,
                    {"message": f"{node_id}/{actuator_id} does not exist!"},
                )
                return

            client.publish(command_topic, json.dumps(data))

        if "measurement" in topic:
            print("Got new sensor measurement")

            sensor_id = get_last_part(topic)
            self.db.add_measurement(node_id, sensor_id, data)

            command_topic = get_device_topic(
                node_id, sensor_id, self.all_devices
            ).format("command")

            if not command_topic:
                return

            print(f"{command_topic=}")

            res = client.publish(command_topic, json.dumps({"value": 1}))

            print(res)

        if "log" in topic:
            sensor_id = get_last_part(topic)
            self.db.add_log(node_id, sensor_id, data)

    def add_topics_and_subscribe(self, device: str, *args) -> None:
        """Adds topics to global lists of all topics and devices, and
        subscribes to them.

        Args:
            device: A device topic which must be formattable
            *args: Strings which also should be subscribed to
        """

        if not device in self.all_devices:
            self.all_devices.append(device)

        for topic in args:
            if topic in self.all_topics:
                continue

            self.client.subscribe(topic)
            self.all_topics.append(topic)

            print("Now subscribing to new topic:", topic)

    def setup_device(self, data: dict) -> None:
        """Setups device given data.

        Sets up a new device and subscribes to its topics and other
        topics needed to communicate with it.

        Args:
            data: MQTT message containing device_id, a list of actuators and sensors.
        """
        node_id = data["device_id"]

        device = "hydroplant/{}/" + node_id + "/"

        for actuator_id in data["actuators"]:
            actuator = device + actuator_id

            action = actuator.format("actuator/action")
            gui_command = actuator.format("command")
            command = actuator.format("command")
            log = actuator.format("log")

            self.add_topics_and_subscribe(actuator, action, gui_command, command, log)

        for sensor_id in data["sensors"]:
            sensor = device + sensor_id

            measurement = sensor.format("sensor/measurement")
            log = sensor.format("log")

            self.add_topics_and_subscribe(sensor, measurement, log)

        # print(self.all_devices)
        # print(self.all_topics)

    def run(self) -> None:
        """Start the master-controller and keep it running
        indefinitely.
        """
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER_HOST, BROKER_PORT, 60)
        self.client.loop_forever()
