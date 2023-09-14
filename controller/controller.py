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
    topic_contains,
)
from .autonomy import Autonomy

from threading import Thread
import logging
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
        self.all_gui_topics = []
        self.all_topics = []
        self.all_devices = []
        self.state = {}

    def update_state(self, last_part: str, data: dict) -> None:
        self.state[last_part] = data["value"]
        self.autonomy.update_state(self.state)
        self.db.update_state(self.state)

    def publisher(self, topic: str, data: dict | list) -> None:
        """Function for the autonomy to communicate with MQTT."""
        self._publish(topic, data)

    def log(self, level: int, message: str) -> None:
        log = {
            "level": level,
            "message": message,
            "device_id": "master-controller",
            "floor": "floor_100",
        }
        self._publish("hydroplant/gui/log", log)

    def _publish(self, topic: str, data: dict | list) -> None:
        """Publish a message to a topic over MQTT.

        Takes a JSON input and turns it into a string to be able to send.

        Args:
            topic: MQTT topic where message should go
            data: JSON data to be published
        """
        data_string = json.dumps(data)
        logging.debug(f"Sending to {topic} with payload {data_string}")
        self.client.publish(topic, payload=data_string)

    def on_connect(self, client, userdata, flags, rc) -> None:
        """Handles MQTT connection to broker and subscribes to needed topics."""
        logging.info(f"Connected to {BROKER_HOST} with result code {rc}")

        # subscribe to devices, so they can present themselves
        client.subscribe(DEVICE_TOPIC)

        # subscribing to

        # subscribe to logging
        client.subscribe(LOG_TOPIC)

    def on_message(self, client, userdata, msg) -> None:
        """Handles MQTT messages."""
        topic: str = msg.topic
        data: dict = json.loads(msg.payload)

        inform_autonomy = False

        # TODO: dont listen to ourselves
        # if data.get("device_id") == "master-controller":
        #     return

        data["time"] = time.time()  # add time for later checks

        logging.debug(f"{topic} {data}")

        node_id = get_second_last_part(topic)
        last_part = get_last_part(topic)

        logging.debug(f"Got new {last_part} message from {node_id} with payload {data}")

        self.log(1, "received a message!")

        if topic_contains(topic, "device"):
            logging.info("Got device message")
            self.setup_device(data)

        if topic_contains(topic, "gui_command"):
            logging.info("Got command from GUI")

            actuator_id = get_last_part(topic)

            floor = get_floor_from_topic(topic)
            stage = get_stage_from_topic(topic)

            command_topic = topic.replace("gui_command", "command")

            data["id"] = actuator_id
            data["floor"] = floor
            data["stage"] = stage

            inform_autonomy = True

            self._publish(topic=command_topic, data=data)

        if topic_contains(topic, "receipt"):
            logging.info("Got a receipt")

            inform_autonomy = True

        # actuator activity, on or off
        if topic_contains(topic, "activity"):
            logging.info("Got new actuator action")
            self.update_state(last_part, data)

        # sensor measurement
        if topic_contains(topic, "measurement"):
            logging.info("Got new sensor measurement")

            sensor_id = get_last_part(topic)
            self.db.add_measurement(node_id, sensor_id, data)
            inform_autonomy = True

        # if "log" in topic:
        #     sensor_id = get_last_part(topic)
        #     self.db.add_log(node_id, sensor_id, data)

        if inform_autonomy:
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

            self.client.subscribe(topic=topic)
            self.all_topics.append(topic)

            logging.info(f"Subscribed to {topic}")

    def setup_device(self, data: dict) -> None:
        """Setups device given data.

        Sets up a new device and subscribes to its topics and other
        topics needed to communicate with it.

        Args:
            data: MQTT message containing device_id, a list of actuators and sensors.
        """
        node_id = data["device_id"]

        if node_id == "gui":
            logging.info("GUI connected")

            # gui_topics = get_all_gui_topics(self.all_topics)

            logging.debug(f"{self.all_gui_topics}")

            self._publish(GUI_TOPICS, {"topics": self.all_gui_topics})
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
                    receipt = actuator.format("command") + "/receipt"
                    # action = actuator.format("actuator/action")
                    # log = actuator.format("log")

                    master_topics = [gui_command, receipt]
                    gui_topics = [gui_command, gui_command_response]

                    self.add_topics_and_subscribe(actuator, *master_topics)

                    for i in gui_topics:
                        self.all_gui_topics.append(i)

            if sensors:
                for sensor_id in sensors:
                    sensor = device + sensor_id

                    measurement = sensor.format("sensor/measurement")
                    # log = sensor.format("log")

                    master_topics = [measurement]

                    self.add_topics_and_subscribe(sensor, *master_topics)

    def run(self) -> None:
        """Start the master-controller and keep it running
        indefinitely.
        """
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER_HOST, BROKER_PORT, 60)

        logging.debug("Starting MQTT loop")
        communication = Thread(target=self.client.loop_forever)
        communication.start()

        logging.debug("Starting autonomy")
        self.autonomy.disable()
        self.autonomy.run()
