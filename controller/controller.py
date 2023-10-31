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
from .classes import *

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
        self.autonomy = Autonomy(
            publish_callback=self.publish,
            topics_callback=self.get_topics,
            state_callback=self.get_state,
            log_callback=self.log,
            wait=AUTONOMY_SLEEP,
        )
        # self.all_gui_topics: list[str] = []
        # self.all_topics: list[str] = []
        # self.all_devices: list[str] = []
        # self.state = {}  # overview of all states, unique_id: value

        self.system = HydroplantSystem(
            Floor("floor_1", "stage_1", "stage_2", "stage_3"),
            Floor("floor_2", "stage_1", "stage_2", "stage_3"),
            Floor("floor_3", "stage_1", "stage_2", "stage_3"),
        )

        # hardcoded places
        # self.places = {
        #     "1": {
        #         "1": False,  # there is no plant holder in place 2
        #         "3": True,
        #         "max_places": 3,
        #     },  # bool is if should change stage
        #     "2": {"1": False, "2": True, "3": True, "max_places": 3},
        #     "3": {"2": True, "max_places": 3},
        # }

    def get_floor(self, topic: str) -> Floor | None:
        floor_str = get_floor_from_topic(topic)

        if not floor_str:
            return None

        floor = floor_str.replace("floor_", "")
        return self.system[int(floor) - 1]

    @staticmethod
    def __json_to_str(data: dict | list) -> str:
        return json.dumps(data)

    # def get_gui_formatted_states(self) -> dict:
    #     # TODO: only send parts at a time, not the whole thing
    #     # everytime, due to mqtt message size
    #     gui_formatted = {}

    #     if not self.state:
    #         return []

    #     for key, value in self.state.items():
    #         # gui does not want this
    #         key = key.replace("/receipt", "")
    #         gui_formatted[GUI_COMMAND + key] = value

    #     # {"hydroplant/gui_command/floor_1/stage_1/climate_node/LED": 1}
    #     return gui_formatted

    def update_and_publish_state(self, topic: str, data: dict) -> None:
        # unique id is floor_1/stage_1/climate_node/LED
        # TODO: handle this better
        topic = topic.replace("/receipt", "")
        unique_id = get_unique_id(topic)

        value = data.get("value")

        # e.g. plant information node with max_stages
        if value is None:
            return

        # TODO: self.system.get_states() so we can update db
        # self.state[unique_id] = value

        # self.autonomy.update_state(self.state)
        self.db.update_state(self.state)
        # TODO: test publishing to gui
        self.publish(SYNC_TOPIC, self.system.get_gui_sync_data())

    def get_topics(self) -> list[str]:
        """Function for autonomy to get all existing topics."""
        return self.all_topics

    def get_state(self) -> dict:
        return self.state

    # def publisher(self, topic: str, data: dict | list) -> None:
    #     """Function for the autonomy to communicate with MQTT."""
    #     self._publish(topic, data)

    def log(self, level: int, message: str) -> None:
        log = {
            "level": level,
            "message": message,
            "device_id": "master_controller",
            "floor": "floor_100",
        }
        self.publish(GUI_LOG, log)

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
        self.client.publish(topic, payload=self.__json_to_str(data))

    def __handle_gui_command(self, topic: str, data: dict) -> bool:
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

            # no need to inform autonomy
            # it already knows its own state
            return False

        unique_id = get_unique_id(topic)

        command = get_object(unique_id).get_command(**data)

        self.publish(*command)
        return True  # inform autonomy

        # _id = get_last_part(topic)
        # floor = get_floor_from_topic(topic)
        # stage = get_stage_from_topic(topic)

        # command_topic = topic.replace("gui_command", "command")

        # data["id"] = _id
        # data["floor"] = floor
        # data["stage"] = stage

    def on_connect(self, client, userdata, flags, rc) -> None:
        """Handles MQTT connection to broker and subscribes to needed topics."""
        logging.info(f"Connected to {BROKER_HOST} with result code {rc}")

        # subscribe to devices, so they can present themselves
        client.subscribe(DEVICE_TOPIC)

        # subscribing to
        client.subscribe(AUTONOMY_TOPIC)

        client.subscribe(IS_READY_TOPIC)

        # to catch when devices disconnects
        # TODO: handle disconnects and unsub from topics?
        client.subscribe(DEVICES_DISCONNECT_TOPIC)

        # client.subscribe(TEMP_TEST_TOPIC)

        # subscribe to logging
        client.subscribe(LOG_TOPIC)

    def on_message(self, client, userdata, msg) -> None:
        """Handles MQTT messages."""
        topic: str = msg.topic

        if not msg.payload:
            msg.payload = "{}"

        data: dict = json.loads(msg.payload)

        inform_autonomy = False

        data["time"] = time.time()  # add time for later checks

        logging.debug(f"<- {topic} {data}")

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

            logging.warning(f"{node_id} disconnected")
            self.log(1, f"{node_id} disconnected")

            unsubscribe_topics = self.system.delete_objects(node_id)
            self.act_on_topics(False, *unsubscribe_topics)

            self.publish(SYNC_TOPIC, self.system.get_gui_sync())
            return

        if topic_contains(topic, "device"):
            logging.info("Got device message")
            self.setup_device(data)

        if topic_contains(topic, "gui_command"):
            logging.info("Got command from GUI")

            inform_autonomy = self.__handle_gui_command(topic, data)

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

        if not inform_autonomy:
            return

        self.autonomy.add_data({"topic": topic, "type": last_part, **data})

    def act_on_topics(self, subscribe: bool, *args) -> None:
        """Adds topics to global lists of all topics and devices, and
        subscribes to them.

        Args:
            device: A device topic which must be formattable
            *args: Strings which also should be subscribed to
        """
        # TODO: rewrite to handle list instead

        for topic in args:
            if subscribe:
                self.client.subscribe(topic)
                logging.info(f"Subscribed to {topic}")
            else:
                self.client.unsubscribe(topic)
                logging.info(f"Unsubscribed to {topic}")

    # def __append_gui_topic(self, topic: str) -> None:
    #     if topic in self.all_gui_topics:
    #         return

    #     self.all_gui_topics.append(topic)

    # def __get_logic_controllers(
    #     self, data: dict, floor: str, node_id: str
    # ) -> list[set]:
    #     topics = []

    #     generic_topic = PREFIX + "{}/" + f"{floor}/{node_id}/"
    #     logic_controllers = data[floor].get("logic_controllers", [])

    #     for logic_controller in logic_controllers:
    #         # hydroplant/{}/floor_1/plant_information_node/plant_information
    #         topics = generic_topic + logic_controller

    #         # gui_command = topic.format("gui_command")
    #         # receipt = topic.format("command") + "/receipt"

    #         # self.__append_gui_topic(gui_command)

    #         # topics += [gui_command, receipt]

    #     return topics

    # def __get_actuators(
    #     self, data: dict, floor: str, node_id: str, stages: list
    # ) -> list[str]:
    #     topics = []

    #     for stage in stages:
    #         generic_topic = PREFIX + "{}/" + f"{floor}/{stage}/{node_id}/"

    #         actuators = data[floor][stage].get("actuators", [])

    #         for actuator in actuators:
    #             topic = generic_topic + actuator

    #             # gui_command = topic.format("gui_command")
    #             # receipt = topic.format("command") + "/receipt"

    #             # self.__append_gui_topic(gui_command)

    #             # topics += [gui_command, receipt]

    #     return topics

    # def __get_sensors(
    #     self, data: dict, floor: str, node_id: str, stages: list
    # ) -> list[str]:
    #     topics = []

    #     for stage in stages:
    #         generic_topic = PREFIX + "{}/" + f"{floor}/{stage}/{node_id}/"

    #         sensors = data[floor][stage].get("sensors", [])

    #         for sensor in sensors:
    #             topic = generic_topic + sensor

    #             topic = topic.format("sensor/measurement")

    #             topics += [topic]

    #     return topics

    def __handle_device_present(self, data: dict, node_id: str) -> None:
        new_topics = []

        # a device can only be on 1 floor
        floor_name = get_floor(data)

        # get the relevant floor
        floor = self.system.get_floor_by_name(floor_name)

        # floor/(stage)/node/part

        for logic_controller in data[floor].get("logic_controllers", []):
            unique_id = f"{floor}/{node_id}/{logic_controller}"

            obj = floor.add_logic_controller(unique_id)
            new_topics += obj.get_subscribe_topics()

        stages = get_stages(floor, data)

        for stage_name in stages:
            stage = floor.get_stage_by_name(stage_name)

            for actuator in data[floor][stage].get("actuators", []):
                unique_id = f"{floor}/{stage}/{node_id}/{actuator}"
                obj = stage.add_actuator(unique_id)
                new_topics += obj.get_subscribe_topics()

            for sensor in data[floor][stage].get("sensors", []):
                # do we actually need this?
                pass

        self.act_on_topics(True, *new_topics)

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
            # gui doesnt have interesting data for us

        else:
            # other nodes has interesting data
            self.__handle_device_present(data, node_id)

        # update gui with all topics (will only happen when something connects)
        self.__publish_gui_topics()
        self.publish(GUI_TOPICS, {"topics": self.system.get_gui_topics()})
        self.publish(SYNC_TOPIC, self.system.get_gui_sync_data())

    def run(self) -> None:
        """Start the master-controller and keep it running
        indefinitely.
        """
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER_HOST, BROKER_PORT, 60)

        # get previous saved state of the system
        self.state = self.db.get_state()

        logging.debug("Starting MQTT loop")
        # start mqtt communication in thread
        communication = Thread(target=self.client.loop_forever)
        communication.start()

        # nodes listen to this, so they can present themselves
        # if they are already running
        self.client.publish(READY_TOPIC, "")

        logging.debug("Starting autonomy")

        self.autonomy.disable()  # disable while we test
        self.autonomy.run()

        communication.join()
