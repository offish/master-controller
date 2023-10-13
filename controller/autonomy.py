from .utils import has_status, get_unique_id, get_last_part, get_data_type

import datetime as dt
import logging
import time


class Autonomy:
    """Class for running the autonomy logic.

    Defaults to be enabled.
    """

    def __init__(
        self,
        publish_callback,
        topics_callback,
        state_callback,
        log_callback,
        count: int = 1_000,
        wait: float = 1.0,
    ) -> None:
        self.data: list[dict] = []  # specific data master-controller receives
        self.jobs: list[dict] = []  # all pending jobs
        self.count = count  # amount of data autonomy should remember
        self.is_enabled = True  # turn on/off autonomy logic
        self.publish = publish_callback  # callback to communicate with MQTT
        self.topics = topics_callback  # all topics master knows of
        self.state = state_callback  # current state of master
        self.log = log_callback  # current state of master
        self.wait = wait  # how long autonomy should sleep for each cycle

    def enable(self) -> None:
        """Enable the autonomy."""
        self.is_enabled = True

    def disable(self) -> None:
        """Disable the autonomy."""
        self.is_enabled = False

    def add_data(self, data: dict) -> None:
        data["status"] = "unchecked"
        self.data.append(data)
        self.data = self.data[-self.count :]  # only keep x latest records

    def __delete_data(self, data: dict) -> None:
        self.data.remove(data)

    def __set_status(self, status: str, data: dict) -> dict:
        data["status"] = status
        return data

    def __set_data_status(self, status: str, data: dict) -> None:
        index = self.data.index(data)
        data = self.__set_status(status, data)
        self.data[index] = data

    def __replace_job(self, job: dict) -> None:
        for j in self.jobs:
            if j["time"] != job["time"]:
                continue

            index = self.jobs.index(j)
            self.jobs[index] = job

    def __delete_job(self, job: dict) -> None:
        self.jobs.remove(job)

    def __get_topics(self, string: str) -> list[str]:
        topics = self.topics()
        result = []

        for topic in topics:
            if string not in topic:
                continue

            result.append(topic)
        return result

    def __get_state(self) -> dict:
        return self.state()

    def __check_lights(self):
        # TODO: rewrite to if-check time, turn lights
        # only on/off if they dont match state and
        # make function for adding jobs
        hour = dt.datetime.now().hour

        logging.debug(f"current hour {hour}")

        if hour < 21 or hour > 7:
            # gets all LEDs from stages
            topics = self.__get_topics("LED")

            logging.debug(f"{topics=}")

            for topic in topics:
                if "receipt" in topic:
                    continue

                self.__add_job(topic, {"value": 1})
                logging.debug(f"added job {self.jobs=}")

        else:
            topics = self.__get_topics("LED")

            for topic in topics:
                if "receipt" in topic:
                    continue

                self.__add_job(topic, {"value": 0})

    def __check_water(self):
        pass

    def __check_interval_jobs(self):
        self.__check_lights()
        self.__check_water()

    def __process_measurement(self, topic: str, data: dict) -> None:
        unique_id = get_unique_id(topic)
        current_value = self.__get_state()[unique_id]

        value = data.get("value")

        # TODO: make sure current state is not matching
        if value == current_value:
            logging.warning("Device already has this value!")
            self.log(1, "device already has this value!")
            return

        # lights

        # moving

        # water interval

        pass

    def __process_data(self, topic: str, data: dict) -> None:
        """here jobs gets added"""
        # topic:

        data_type = get_data_type(topic)

        if not data_type:
            return

        # measurement -> camera -> move
        # receipt -> delete
        # command -> do

        match data_type:
            # case "command":
            #     self.__process_command(topic, data)
            #     pass

            case "measurement":
                self.__process_measurement(topic, data)
                pass

            case "receipt":
                # self.__process_receipt(topic,data)
                pass

        # the data goes from unchecked -> checked
        self.__set_data_status("checked", data)

    def __check(self) -> None:
        # we have pending jobs
        for job in self.jobs:
            if has_status("queued", job):
                # publish message and set to pending
                self.publish(job["topic"], job)

                # we published, now a pending job
                pending_job = self.__set_status("pending", job)
                self.__replace_job(pending_job)

                # we continue to save a couple of ms

            if has_status("pending", job):
                # check if it is done or not

                # loop through receipts
                pass

            if has_status("done", job):
                # job is done,
                self.__delete_job(job)

        self.data = [{}]

        # check all data we know of, reversed since newest gets appended
        for data in reversed(self.data):
            topic = data.get("topic")

            # if not topic_contains(topic, "measurement", "receipt"):
            #     # irrelevant -> skip
            #     continue

            if has_status("checked", data):
                # we have checked this data, but it can have already
                # been done or not, we need to check
                if False:
                    self.__set_data_status("done", data)

            if has_status("done", data):
                # we have recevied receipt for this, so we delete
                self.__delete_data(data)
                continue  # done with this data

            self.__check_interval_jobs()
            # -> data is unchecked
            # we need to check it
            self.__process_data(topic, data)

    def __add_job(self, topic: str, data: dict) -> None:
        data["topic"] = topic
        data["time"] = time.time()
        data["status"] = "queued"
        self.jobs.append(data)

    def run(self) -> None:
        while True:
            logging.info("Autonomy is running")

            if self.is_enabled:
                logging.debug("Autonomy is enabled")
                self.__check()
            else:
                logging.warning("Autonomy is disabled")

            time.sleep(self.wait)
