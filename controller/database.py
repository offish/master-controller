from .config import DATABASE_HOST, DATABASE_PORT

import logging

from pymongo import MongoClient, collection


class Database:
    def __init__(self, host: str = DATABASE_HOST, port: int = DATABASE_PORT) -> None:
        self.__client = MongoClient(host=host, port=port)
        self.db = self.__client["hydroplant"]
        logging.info("Connected to database")

        self.measurement = self.db["measurements"]
        self.actuator = self.db["actuator"]
        self.sensor = self.db["sensor"]
        self.state = self.db["state"]
        self.logs = self.db["logs"]

    def add_measurement(self, node_id: str, sensor_id: str, data: dict) -> None:
        """Insert measurement into database.

        Args:
            node_id: Name of the node.
            sensor_id: Name of the sensor.
            data: Data which should be added, time will also be added to the
              measurement.
        """
        data["node_id"] = node_id
        data["sensor_id"] = sensor_id

        self.measurement.insert_one(data)
        logging.debug(f"Added to measurement {data=}")

    def add_log(self, node_id: str, sensor_id: str, data: dict) -> None:
        """Insert log into database.

        Used for logging.

        Args:
            node_id: Name of the node.
            sensor_id: Name of the sensor.
            data: Data which should be added message.
        """
        data["node_id"] = node_id
        data["sensor_id"] = sensor_id

        self.logs.insert_one(data)
        logging.debug(f"Added to logs {data=}")

    def get_state(self) -> dict:
        result = self.state.find_one({})

        if not result:
            result = {}

        # mongo db adds this
        del result["_id"]

        return result

    def update_state(self, state: dict) -> None:
        data = self.get_state()

        # only the case if collection is empty
        if not data:
            self.state.insert_one(state)
            return

        self.state.replace_one(data, state)
        logging.debug(f"Updated state from {data=} to {state=}")


"""
ec.publish("hydroplant/measurement/ec",{"value":3.332362})
"""
