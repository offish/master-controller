from .database import Database
from .config import (
    BROKER_HOST,
    BROKER_PORT,
)
from .topics import *
from .utils import (
    get_last_part,
    get_second_last_part,
    get_device_topic,
    get_all_gui_topics,
    get_floor,
    get_stages,
    get_floor_from_topic,
    get_stage_from_topic,
)
from .autonomy import Autonomy

from threading import Thread
import time
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
        self.autonomy = Autonomy(self.publisher)
        self.all_topics = []
        self.all_devices = []
        self.state = {}

    def update_state(self, last_part: str, data: dict) -> None:
        self.state[last_part] = data["value"]
        self.db.update_state(self.state)

    def publisher(self, topic: str, data: dict | list) -> None:
        """Function for the autonomy to communicate with MQTT."""
        self._publish(topic, data)

    def _publish(self, topic: str, data: dict | list) -> None:
        """Publish a message to a topic over MQTT.

        Takes a JSON input and turns it into a string to be able to send.

        Args:
            topic: MQTT topic where message should go
            data: JSON data to be published
        """
        data_string = json.dumps(data)
        self.client.publish(topic, data_string)

    def on_connect(self, client, userdata, flags, rc) -> None:
        """Handles MQTT connection to broker and subscribes to needed topics."""
        print("Connected to", BROKER_HOST, "with result code " + str(rc))
        # print(userdata, flags)

        client.subscribe(DEVICE_TOPIC)

        # subscribe to all commands coming from GUI
        client.subscribe(GUI_COMMANDS)

    def on_message(self, client, userdata, msg) -> None:
        """Handles MQTT messages."""
        topic: str = msg.topic
        data: dict = json.loads(msg.payload)
        data["time"] = time.time()  # add time for later checks

        print(f"Got data {data}")

        add_to_autonomy = False
        node_id = get_second_last_part(topic)
        last_part = get_last_part(topic)

        print("Got a new", last_part, "message from", node_id)

        if "device" in topic:
            # print("Got command from GUI")
            self.setup_device(data)

        if "gui_command" in topic:
            print("Got command from GUI")

            actuator_id = get_last_part(topic)

            # floor = get_floor_from_topic(topic)
            # stage = get_stage_from_topic(topic)

            command_topic = topic.replace("gui_command", "command")

            if not topic in self.all_topics:
                # device does not exist
                self._publish(
                    LOG_TOPIC,
                    {
                        "level": "error",
                        "message": f"{command_topic} does not exist!",
                    },
                )
                return

            data["id"] = actuator_id

            add_to_autonomy = True
            self._publish(command_topic, data)

        # actuator activity, on or off
        if "activity" in topic:
            print("Got new actuator activity")
            self.update_state(last_part, data)

        # sensor measurement
        if "measurement" in topic:
            print("Got new sensor measurement")

            sensor_id = get_last_part(topic)
            self.db.add_measurement(node_id, sensor_id, data)
            add_to_autonomy = True

            command_topic = get_device_topic(
                node_id, sensor_id, self.all_devices
            ).format("command")

            if not command_topic:
                return

            print(f"{command_topic=}")

            res = self._publish(command_topic, {"value": 1})
            print(res)

        if "log" in topic:
            sensor_id = get_last_part(topic)
            self.db.add_log(node_id, sensor_id, data)

        if add_to_autonomy:
            self.autonomy.add_data({"topic": topic, "type": last_part, **data})

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

        if node_id == "gui":
            print("hei gui")

            gui_topics = get_all_gui_topics(self.all_topics)

            print(gui_topics)

            self._publish(GUI_TOPICS, {"topics": gui_topics})
            return

        floor = get_floor(data)
        stages = get_stages(floor, data)

        # self.autonomy.disable()

        for stage in stages:
            actuators = data[floor][stage].get("actuators")
            sensors = data[floor][stage].get("sensors")

            device = "hydroplant/{}/" + f"{floor}/{stage}/{node_id}/"

            if actuators:
                for actuator_id in actuators:
                    actuator = device + actuator_id

                    gui_command_response = actuator.format("gui_command") + "/response"
                    gui_command = actuator.format("gui_command")
                    action = actuator.format("actuator/action")
                    command = actuator.format("command")
                    log = actuator.format("log")

                    self.add_topics_and_subscribe(
                        actuator,
                        action,
                        gui_command_response,
                        gui_command,
                        command,
                        log,
                    )

            if sensors:
                for sensor_id in sensors:
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

        communication = Thread(target=self.client.loop_forever)
        communication.start()
        # self.client.loop_forever()
        self.autonomy.run()
