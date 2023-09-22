from .database import Database
from .config import BROKER_HOST, BROKER_PORT, AUTONOMY_SLEEP, DISALLOWED_KEYS
from .topics import *
from .utils import (
    get_last_part,
    get_second_last_part,
    get_floor,
    get_stages,
    get_floor_from_topic,
    get_stage_from_topic,
    topic_contains,
    get_unique_id,
)
from .autonomy import Autonomy

from threading import Thread
import logging
import time
import json

import paho.mqtt.client as mqtt


class Controller:
    """Controller class for keeping track
    and handling connections to MQTT,
    database and other logic.
    """

    def __init__(self) -> None:
        self.client = mqtt.Client(client_id="master")
        self.db = Database()
        self.autonomy = Autonomy(
            publisher_callback=self.publisher,
            topics_callback=self.get_topics,
            state_callback=self.get_state,
            log_callback=self.log,
            wait=AUTONOMY_SLEEP,
        )
        self.all_gui_topics: list[str] = []
        self.all_topics: list[str] = []
        self.all_devices: list[str] = []
        self.state = {}  # overview of all states, unique_id: value

    def get_gui_formatted_states(self) -> list[dict]:
        # TODO: only send parts at a time, not the whole thing
        # everytime, due to mqtt message size
        gui_formatted = {}

        if not self.state:
            return []

        for key, value in self.state.items():
            # gui does not want this
            key = key.replace("/receipt", "")
            gui_formatted[GUI_COMMAND + key] = value

        # {"hydroplant/gui_command/floor_1/stage_1/climate_node/LED": 1}
        return gui_formatted

    def update_and_publish_state(self, topic: str, data: dict) -> None:
        # unique id is floor_1/stage_1/climate_node/LED
        # TODO: handle this better
        topic = topic.replace("/receipt", "")
        unique_id = get_unique_id(topic)

        self.state[unique_id] = data["value"]
        # self.autonomy.update_state(self.state)
        self.db.update_state(self.state)
        # TODO: test publishing to gui
        self._publish(SYNC_TOPIC, self.get_gui_formatted_states())

    def get_topics(self) -> list[str]:
        """Function for autonomy to get all existing topics."""
        return self.all_topics

    def get_state(self) -> dict:
        return self.state

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
        self._publish(GUI_LOG, log)

    def _publish(self, topic: str, data: dict | list) -> None:
        """Publish a message to a topic over MQTT.

        Takes a JSON input and turns it into a string to be able to send.

        Args:
            topic: MQTT topic where message should go
            data: JSON data to be published
        """
        # strip message for unnecessary data
        # this is done to save bandwidth over mqtt
        if isinstance(data, dict):
            copy = data.copy()
            for key in data:
                if key in DISALLOWED_KEYS:
                    del copy[key]
            # or else runtimeerror
            # changing size while iterating
            data = copy

        print(f"{data=}")

        serialized_data = json.dumps(data)
        logging.debug(f"Sending to {topic} with payload {serialized_data}")
        self.client.publish(topic, payload=serialized_data)

    def on_connect(self, client, userdata, flags, rc) -> None:
        """Handles MQTT connection to broker and subscribes to needed topics."""
        logging.info(f"Connected to {BROKER_HOST} with result code {rc}")

        # subscribe to devices, so they can present themselves
        client.subscribe(DEVICE_TOPIC)

        # subscribing to
        client.subscribe(AUTONOMY_TOPIC)

        # subscribe to logging
        client.subscribe(LOG_TOPIC)

    def on_message(self, client, userdata, msg) -> None:
        """Handles MQTT messages."""
        topic: str = msg.topic
        data: dict = json.loads(msg.payload)

        inform_autonomy = False

        data["time"] = time.time()  # add time for later checks

        logging.debug(f"{topic} {data}")

        node_id = get_second_last_part(topic)
        last_part = get_last_part(topic)

        logging.debug(f"Got new {last_part} message from {node_id} with payload {data}")

        self.log(0, "received a message!")

        if topic_contains(topic, "device"):
            logging.info("Got device message")
            self.setup_device(data)

        if topic_contains(topic, "gui_command"):
            logging.info("Got command from GUI")

            if topic == AUTONOMY_TOPIC:
                if data["value"]:
                    self.autonomy.enable()
                    logging.info("GUI turned autonomy on")
                    self.log(1, "Autonomy turned on")
                else:
                    self.autonomy.disable()
                    logging.warning("GUI turned autonomy off")
                    self.log(1, "Autonomy turned off")

                return

            actuator_id = get_last_part(topic)
            floor = get_floor_from_topic(topic)
            stage = get_stage_from_topic(topic)

            command_topic = topic.replace("gui_command", "command")

            data["id"] = actuator_id
            data["floor"] = floor
            data["stage"] = stage

            inform_autonomy = True
            self._publish(topic=command_topic, data=data)

        # check receipt
        if topic_contains(topic, "receipt"):
            logging.info("Got a receipt")

            self.update_and_publish_state(topic, data)
            inform_autonomy = True

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

        floor = get_floor(data)
        stages = get_stages(floor, data)

        for stage in stages:
            actuators = data[floor][stage].get("actuators")
            sensors = data[floor][stage].get("sensors")

            device = PREFIX + "{}/" + f"{floor}/{stage}/{node_id}/"

            if actuators:
                for actuator_id in actuators:
                    actuator = device + actuator_id

                    gui_command = actuator.format("gui_command")
                    receipt = actuator.format("command") + "/receipt"

                    master_topics = [gui_command, receipt]
                    gui_topics = [gui_command]

                    self.add_topics_and_subscribe(actuator, *master_topics)

                    for i in gui_topics:
                        if i in self.all_gui_topics:
                            continue

                        self.all_gui_topics.append(i)

            if sensors:
                for sensor_id in sensors:
                    sensor = device + sensor_id

                    measurement = sensor.format("sensor/measurement")

                    master_topics = [measurement]

                    self.add_topics_and_subscribe(sensor, *master_topics)

        if len(self.all_gui_topics) > 0:
            self._publish(GUI_TOPICS, {"topics": self.all_gui_topics})

        states = self.get_gui_formatted_states()

        if states:
            self._publish(SYNC_TOPIC, states)

    def run(self) -> None:
        """Start the master-controller and keep it running
        indefinitely.
        """
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER_HOST, BROKER_PORT, 60)

        self.state = self.db.get_state()

        logging.debug("Starting MQTT loop")
        communication = Thread(target=self.client.loop_forever)
        communication.start()

        # nodes listen to this, so they can present themselves
        # if they were already running
        self.client.publish(READY_TOPIC, "")

        logging.debug("Starting autonomy")
        self.autonomy.disable()
        self.autonomy.run()
