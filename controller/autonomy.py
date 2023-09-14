from .utils import has_status, is_topic, is_type, topic_contains

import logging
import time


class Autonomy:
    """Class for running the autonomy logic.

    Defaults to be enabled.
    """

    def __init__(self, publisher, count: int = 1_000, wait: float = 1.0) -> None:
        self.data: list[dict] = []  # data is everything master-controller receives
        self.jobs: list[dict] = []  # all pending jobs
        self.count = count  # amount of data autonomy should remember
        self.is_enabled = True  # turn on/off autonomy logic
        self.publisher = publisher  # callback to communicate with MQTT
        self.wait = wait  # how long autonomy should sleep for each cycle
        self.state = {}  # current state of the system

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

    def update_state(self, state: dict) -> None:
        self.state = state

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
            if job["time"] == j["time"]:
                index = self.jobs.index(j)
                self.jobs[index] = job

    def delete_job(self, job: dict) -> None:
        self.jobs.remove(job)

    def _check(self) -> None:
        ph_threshold = 8

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

        # check all data we know of
        for data in reversed(self.data):
            topic = data.get("topic")

            if not topic_contains(topic, "measurement", "receipt"):
                # added by accident or something -> skip
                continue

            if not has_status("unchecked", data):
                if has_status("pending", data):
                    # we have checked this data, but it can have already
                    # been done or not, we need to check
                    if "done":
                        self._set_data_status("done", data)

                if has_status("done", data):
                    # we have recevied receipt for this, so we delete
                    self._delete_data(data)

                continue

            # we have not checked this data yet
            # we might need to do something

            # oh no! its our ph is too high -> regulate
            if is_type("ph", data) and data["value"] > ph_threshold:
                self._set_data_status("checked", data)

                wished_data = {"value": 0}
                self.add_job("ph", wished_data)

                # self._publish("ph", {"value": 0})

                # mark data as checked
                # self._set_data_status("pending", data)

                print("msg sent", data)
                # wait for receipt, so we know its done

    def add_job(self, topic: str, data: dict) -> None:
        data["topic"] = topic
        data["time"] = time.time()
        data["status"] = "queued"
        self.jobs.append(data)

    def run(self) -> None:
        logging.info("Autonomy is running")

        while self.is_enabled:
            logging.debug("Autonomy is enabled")
            # print("enabled", self.data)
            self._check()
            time.sleep(self.wait)

        logging.warning("Autonomy is disabled")
        time.sleep(self.wait)
