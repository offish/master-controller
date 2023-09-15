from .config import DATABASE_HOST, DATABASE_PORT

import logging

from pymongo import MongoClient, collection


class Database:
    def __init__(self, host: str = DATABASE_HOST, port: int = DATABASE_PORT) -> None:
        self._client = MongoClient(host=host, port=port)
        self.db = self._client["hydroplant"]
        logging.info("Connected to database")

        self.measurement = self.db["measurements"]
        self.actuator = self.db["actuator"]
        self.sensor = self.db["sensor"]
        self.state = self.db["state"]
        self.logs = self.db["logs"]

    def _get_which_database(self, topic: str) -> collection.Collection:
        """Gets which database to use.

        Args:
            topic: MQTT topic for that message

        Returns:
            A MongoDB collection to use
        """
        if "sensor" in topic:
            return self.sensor

        if "measurement" in topic:
            return self.measurement

        if "actuator" in topic:
            return self.actuator

        return self.db[topic]

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
        return self.db.find_one({})

    def update_state(self, state: dict) -> None:
        data = self.get_state()
        self.state.replace_one(data, state)
        logging.debug(f"Updated state from {data=} to {state=}")


"""
ec.publish("hydroplant/measurement/ec",{"value":3.332362})
"""
