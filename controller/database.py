from .config import DATABASE_HOST, DATABASE_PORT

import time

from pymongo import MongoClient, collection


class Database:
    def __init__(self, host: str = DATABASE_HOST, port: int = DATABASE_PORT) -> None:
        self._client = MongoClient(host=host, port=port)
        self.db = self._client["hydroplant"]

        self.measurement = self.db["measurements"]
        self.actuator = self.db["actuator"]
        self.sensor = self.db["sensor"]

    def _get_which_database(self, topic: str) -> collection.Collection:
        if "sensor" in topic:
            return self.sensor

        if "measurement" in topic:
            return self.measurement

        if "actuator" in topic:
            return self.actuator

        return self.db[topic]

    def add_measurement(self, sensor_id: str, data: dict) -> None:
        data["sensor_id"] = sensor_id
        self.measurement.insert_one(data)

    def add_data(self, topic: str, data: dict) -> None:
        db = self._get_which_database(topic)

        # if db is self.measurement:
        #     self.add_measurement_data(topic,data)
        #     return

        data["time"] = time.time()
        db.insert_one(data)
        print("Data was added to database in collection", db.name)


"""
ec.publish("hydroplant/measurement/ec",{"value":3.332362})
"""
