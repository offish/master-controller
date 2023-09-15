from .utils import has_status, get_unique_id

import datetime as dt
import logging
import time


class Autonomy:
    """Class for running the autonomy logic.

    Defaults to be enabled.
    """

    def __init__(
        self,
        publisher_callback,
        topics_callback,
        state_callback,
        count: int = 1_000,
        wait: float = 1.0,
    ) -> None:
        self.data: list[dict] = []  # data is everything master-controller receives
        self.jobs: list[dict] = []  # all pending jobs
        self.count = count  # amount of data autonomy should remember
        self.is_enabled = True  # turn on/off autonomy logic
        self.publisher = publisher_callback  # callback to communicate with MQTT
        self.topics = topics_callback  # all topics master knows of
        self.state = state_callback  # current state of master
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

    def _publish(self, topic: str, data: dict | list) -> None:
        self.publisher(topic, data)

    def _delete_data(self, data: dict) -> None:
        self.data.remove(data)

    def _set_status(self, status: str, data: dict) -> dict:
        data["status"] = status
        return data

    def _set_data_status(self, status: str, data: dict) -> None:
        index = self.data.index(data)
        data = self._set_status(status, data)
        self.data[index] = data

    def replace_job(self, job: dict) -> None:
        for j in self.jobs:
            if j["time"] == job["time"]:
                index = self.jobs.index(j)
                self.jobs[index] = job

    def delete_job(self, job: dict) -> None:
        self.jobs.remove(job)

    def get_topics(self, string: str) -> list[str]:
        topics = self.topics()
        result = []

        for topic in topics:
            if string in topic:
                result.append(topic)
        return result

    def _get_state(self) -> dict:
        return self.state()

    def process_data(self, topic: str, data: dict) -> None:
        """here jobs gets added"""
        hour = dt.datetime.now().hour

        logging.debug(f"current hour {hour}")

        # TODO: make sure current state is not matching
        unique_id = get_unique_id(topic)
        state = self._get_state()

        if hour < 21 or hour > 7:
            topics = self.get_topics("LED")

            logging.debug(f"{topics=}")

            for topic in topics:
                if "receipt" in topic:
                    continue

                self.add_job(topic, {"value": 1})
                logging.debug(f"added job {self.jobs=}")

        else:
            topics = self.get_topics("LED")

            for topic in topics:
                if "receipt" in topic:
                    continue

                self.add_job(topic, {"value": 0})

        # lights

        # moving

        # water interval

        # the data goes from unchecked -> checked
        self._set_data_status("checked", data)

    def _check(self) -> None:
        # we have pending jobs
        for job in self.jobs:
            if has_status("queued", job):
                # publish message and set to pending
                self._publish(job["topic"], job)

                # we published, now a pending job
                pending_job = self._set_status("pending", job)
                self.replace_job(pending_job)

                # we continue to save a couple of ms

            if has_status("pending", job):
                # check if it is done or not

                # loop through receipts
                pass

            if has_status("done", job):
                # job is done,
                self.delete_job(job)

        # check all data we know of, reversed since newest gets appended
        self.data = [{}]

        for data in reversed(self.data):
            topic = data.get("topic")

            # if not topic_contains(topic, "measurement", "receipt"):
            #     # irrelevant -> skip
            #     continue

            if has_status("checked", data):
                # we have checked this data, but it can have already
                # been done or not, we need to check
                if False:
                    self._set_data_status("done", data)

            if has_status("done", data):
                # we have recevied receipt for this, so we delete
                self._delete_data(data)
                continue  # done with this data

            # -> data is unchecked
            # we might need to check it
            self.process_data(topic, data)

    def add_job(self, topic: str, data: dict) -> None:
        data["topic"] = topic
        data["time"] = time.time()
        data["status"] = "queued"
        self.jobs.append(data)

    def run(self) -> None:
        while True:
            logging.info("Autonomy is running")

            if self.is_enabled:
                logging.debug("Autonomy is enabled")
                self._check()
            else:
                logging.warning("Autonomy is disabled")

            time.sleep(self.wait)
