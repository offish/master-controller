from .hydroplant import HydroplantSystem, Floor
from .autonomy import Autonomy
from .database import Database
from .config import BROKER_HOST, BROKER_PORT, AUTONOMY_SLEEP, DISALLOWED_KEYS
from .topics import *
from .utils import (
    get_last_part,
    get_second_last_part,
    get_floor,
    get_stages,
    topic_contains,
    get_unique_id,
)

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
        self.client = mqtt.Client(client_id="master_controller")
        self.client.will_set(MASTER_DISCONNECT_TOPIC, "")

        self.db = Database()

        self.system = HydroplantSystem(
            Floor("floor_1", "stage_1", "stage_2", "stage_3"),
            Floor("floor_2", "stage_1", "stage_2", "stage_3"),
            Floor("floor_3", "stage_1", "stage_2", "stage_3"),
        )

        self.autonomy = Autonomy(
            system=self.system,
            publish_callback=self.publish,
            log_callback=self.log,
            wait=AUTONOMY_SLEEP,
        )

    def on_connect(self, client, userdata, flags, rc) -> None:
        """Handles MQTT connection to broker and subscribes to needed topics."""
        logging.info(f"Connected to {BROKER_HOST} with result code {rc}")

        # subscribe to devices, so they can present themselves
        client.subscribe(DEVICE_TOPIC)

        # subscribing to
        client.subscribe(AUTONOMY_TOPIC)

        client.subscribe(IS_READY_TOPIC)

        # to catch when devices disconnects
        client.subscribe(DEVICES_DISCONNECT_TOPIC)

        # subscribe to logging
        client.subscribe(LOG_TOPIC)

    def on_message(self, client, userdata, msg) -> None:
        """Handles MQTT messages."""
        topic: str = msg.topic

        if not msg.payload:
            msg.payload = "{}"

        # logging.debug(f"{topic=}")
        # logging.debug(f"{msg.payload}")

        logging.debug(f"<- {topic} {msg.payload}")

        try:
            data: dict = json.loads(msg.payload)
        except json.decoder.JSONDecodeError:
            logging.error("Could not decode JSON!")
            return

        data["time"] = time.time()  # add time for later checks

        node_id = get_second_last_part(topic)
        last_part = get_last_part(topic)

        logging.debug(f"{topic=} {last_part=} {node_id=} {data=}")

        self.log(0, "received a message!")

        # device wants to know if we are online
        if topic_contains(topic, "is_ready"):
            # publish we are ready
            self.publish(READY_TOPIC, "")
            return

        # ok

        if topic_contains(topic, "disconnected"):
            node_id = data["device_id"]
            floor_name = data.get("floor")

            logging.warning(f"{node_id} disconnected")
            self.log(1, f"{node_id} disconnected")

            unsubscribe_topics = self.system.delete_objects(node_id, floor_name)
            self.__act_on_topics(False, *unsubscribe_topics)

            self.publish(GUI_TOPICS, {"topics": self.system.get_gui_topics()})
            self.publish(SYNC_TOPIC, self.system.get_gui_sync_data())
            return

        if topic_contains(topic, "device"):
            logging.info("Got device message")
            self.__setup_device(data)

        if topic_contains(topic, "gui_command"):
            logging.info("Got command from GUI")

            self.__handle_gui_command(topic, data)

        # check receipt
        if topic_contains(topic, "receipt"):
            logging.info("Got a receipt")

            self.__update_and_publish_state(topic, data)

        # TODO: do we need this?
        # sensor measurement
        # if topic_contains(topic, "measurement"):
        #     logging.info("Got new sensor measurement")

        #     sensor_id = get_last_part(topic)
        #     self.db.add_measurement(node_id, sensor_id, data)

    def publish(self, topic: str, data: dict | list) -> None:
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
                if key not in DISALLOWED_KEYS:
                    continue

                del copy[key]
            # or else runtimeerror
            # changing size while iterating
            data = copy

        logging.debug(f"-> {topic} {data}")
        self.client.publish(topic, payload=json.dumps(data))

    def log(self, level: int, message: str) -> None:
        self.publish(
            GUI_LOG,
            {
                "level": level,
                "message": message,
                "device_id": "master_controller",
                "floor": "floor_100",
            },
        )

    def __update_and_publish_state(self, topic: str, data: dict) -> None:
        topic = topic.replace("/receipt", "")
        # unique id is floor_1/stage_1/climate_node/LED
        unique_id = get_unique_id(topic)

        obj = self.system.get_object_from_unique_id(unique_id)
        obj.set_data(data)

        # e.g. plant information node with max_stages
        if obj.get_value() is None:
            return

        current_state = self.system.get_state()
        self.db.update_state(current_state)

        self.publish(SYNC_TOPIC, self.system.get_gui_sync_data())

    def __handle_gui_command(self, topic: str, data: dict) -> None:
        # turn on or off autonomy from gui
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

        unique_id = get_unique_id(topic)

        command = self.system.get_object(unique_id).get_command(**data)

        # logging.debug(f"{command=}")

        self.publish(*command)

    def __act_on_topics(self, subscribe: bool, *args) -> None:
        """Adds topics to global lists of all topics and devices, and
        subscribes to them.

        Args:
            device: A device topic which must be formattable
            *args: Strings which also should be subscribed to
        """
        for topic in args:
            if subscribe:
                self.client.subscribe(topic)
                logging.info(f"Subscribed to {topic}")
            else:
                self.client.unsubscribe(topic)
                logging.info(f"Unsubscribed to {topic}")

    def __handle_device_present(self, data: dict, node_id: str) -> list[str]:
        """returns a list of new unique ids"""
        new_topics = []

        # a device can only be on 1 floor
        floor_name = get_floor(data)

        # get the relevant floor
        floor = self.system.get_floor_by_name(floor_name)
        unique_ids = []
        # floor/(stage)/node/part

        for logic_controller in data[floor_name].get("logic_controllers", []):
            unique_id = f"{floor_name}/{node_id}/{logic_controller}"
            unique_ids.append(unique_id)

            obj = floor.add_logic_controller(unique_id)
            new_topics += obj.get_subscribe_topics()

        stages = get_stages(floor_name, data)

        for stage_name in stages:
            stage = floor.get_stage_by_name(stage_name)

            for actuator in data[floor_name][stage_name].get("actuators", []):
                unique_id = f"{floor_name}/{stage_name}/{node_id}/{actuator}"
                unique_ids.append(unique_id)

                obj = stage.add_actuator(unique_id)
                new_topics += obj.get_subscribe_topics()

            for sensor in data[floor_name][stage_name].get("sensors", []):
                # TODO: do we actually need this?
                pass

        self.__act_on_topics(True, *new_topics)
        return unique_ids

    def __publish_last_states(self, unique_ids: list[str]) -> None:
        states = self.db.get_state()

        for unique_id in unique_ids:
            if unique_id not in states:
                continue

            previous_value = states[unique_id]
            obj = self.system.get_object_from_unique_id(unique_id)
            # command = obj.get_command(value=previous_value)

            # TODO: test lights and job queueing
            command = obj.get_command(value=0)
            self.publish(*command)

    def __setup_device(self, data: dict) -> None:
        """Setups device given data.

        Sets up a new device and subscribes to its topics and other
        topics needed to communicate with it.

        Args:
            data: MQTT message containing device_id, a list of actuators and sensors.
        """
        node_id = data["device_id"]

        if node_id == "gui":
            logging.info("GUI connected")
        else:
            # other nodes has interesting data
            unique_ids = self.__handle_device_present(data, node_id)

            # set state to the last one we knew of
            self.__publish_last_states(unique_ids)

        # update gui with all topics (will only happen when something connects)
        self.publish(GUI_TOPICS, {"topics": self.system.get_gui_topics()})
        self.publish(SYNC_TOPIC, self.system.get_gui_sync_data())

    def run(self) -> None:
        """Start the master-controller and keep it running
        indefinitely.
        """
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER_HOST, BROKER_PORT, 60)

        logging.debug("Starting MQTT loop")
        # start mqtt communication in thread
        communication = Thread(target=self.client.loop_forever)
        communication.start()

        # nodes listen to this, so they can present themselves
        # if they are already running
        self.client.publish(READY_TOPIC, "")

        logging.debug("Starting autonomy")

        # self.autonomy.disable()  # disable while we test
        self.autonomy.run()

        communication.join()
