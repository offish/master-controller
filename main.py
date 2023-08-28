from controller.database import Database
from controller.config import BROKER_HOST, BROKER_PORT

import json

import paho.mqtt.client as mqtt


client = mqtt.Client("master")
database = Database()

DEVICE_TOPIC = "hydroplant/device"
COMMAND_TOPIC = "hydroplant/command"

all_topics = []


def on_connect(client, userdata, flags, rc):
    print("Connected to", BROKER_HOST, "with result code " + str(rc))
    # print(userdata, flags)

    client.subscribe(DEVICE_TOPIC)


def handle_device(data: dict) -> None:
    # print(payload, type(payload))

    node_id = data["device_id"]

    for sensor_id in data["sensors"]:
        sensor = f"hydroplant/sensor/{node_id}/{sensor_id}"
        measurement = f"hydroplant/{node_id}/measurement/{sensor_id}"

        for topic in [sensor, measurement]:
            # already added? -> skip
            if topic in all_topics:
                continue

            client.subscribe(topic)

            print("Now subscribing to new topic:", topic)

            all_topics.append(topic)


def get_sensor_id(topic: str) -> str:
    parts = topic.split("/")
    return parts[-1:][0]


def on_message(client, userdata, msg):
    topic = msg.topic.replace("hydroplant/", "")
    data = json.loads(msg.payload)

    print("Got a new", topic, "message from", data.get("device_id"))
    # database.add_data(topic, data)
    added_to_database = False

    # if topic in ["device", "command"]:
    #     exec(f"handle_{topic}(data)")

    if topic == "device":
        handle_device(data)

    elif "sensor" in topic:
        # print("sensor data")
        pass

    elif "measurement" in topic:
        # print("got new sensor measurement")
        sensor_id = get_sensor_id(topic)
        database.add_measurement(sensor_id, data)
        added_to_database = True

    # add data to database if not already added
    if not added_to_database:
        database.add_data(topic, data)


if __name__ == "__main__":
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)

    client.loop_forever()
