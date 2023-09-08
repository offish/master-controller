import time


class Autonomy:
    """Class for running the autonomy logic.

    Defaults to be enabled.
    """

    def __init__(self, publisher, count: int = 1000, wait: float = 1.0) -> None:
        self.data = []  # data is everything master-controller receives
        self.count = count  # amount of data autonomy should remember
        self.is_enabled = True  # turn on/off autonomy logic
        self.publisher = publisher  # callback to communicate with MQTT
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

    def _set_status(self, status: str, data: dict) -> None:
        index = self.data.index(data)
        data["status"] = status
        self.data[index] = data

    def _check(self) -> None:
        ph_threshold = 8

        for data in reversed(self.data):
            if not is_topic("measurement", data):
                # if something else than measurement -> skip
                continue

            if not has_status("unchecked", data):
                if has_status("pending", data):
                    # we have checked this data, but it can have already
                    # been done or not, we need to check
                    if "done":
                        self._set_status("done", data)

                if has_status("done", data):
                    # we have recevied receipt for this, so we delete
                    self._delete_data(data)

                continue

            # we have not checked this data yet
            # we might need to do something

            if is_type("ph", data) and data["value"] > ph_threshold:
                self._publish("ph", {"value": 0})

                # mark data as checked
                self._set_status("pending", data)

                print("msg sent", data)
                # wait for receipt, so we know its done

    def run(self) -> None:
        while self.is_enabled:
            print("enabled", self.data)
            self._check()
            time.sleep(self.wait)

        print("disabled")
        time.sleep(self.wait)


def is_type(type_name: str, data: dict) -> bool:
    """Check if data is given type.

    Args:
        type_name: name of type to match
        data: data dictionary

    Returns:
        Wheter or not the type matches
    """
    return data["type"] == type_name


def is_topic(topic_name: str, data: dict) -> bool:
    """Check if data is given topic.

    Args:
        topic_name: name of topic to match
        data: data dictionary

    Returns:
        Wheter or not the topic matches
    """
    return topic_name in data["topic"]


def has_status(status: str, data: dict) -> bool:
    """Check if data has given status.

    Args:
        status: status name to check for, `unchecked`, `pending` or `done`
        data: data dictionary

    Returns:
        Wheter or not the status match
    """
    if not status in ["unchecked", "pending", "done"]:
        raise KeyError(f"{status} status does not exist!")
    return data.get("status") == status
