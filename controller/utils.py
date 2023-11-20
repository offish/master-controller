import logging


def get_last_part(topic: str) -> str:
    """Gets the last part of a topic string, usually the `sensor_id`

    Args:
        topic: MQTT topic string

    Returns:
        str: The last part of the input after "/"
    """
    parts = topic.split("/")
    return parts[-1:][0]


def get_second_last_part(topic: str) -> str:
    """Gets the second to last part of a topic string, usually the `node_id`

    Args:
        topic: MQTT topic string

    Returns:
        The last part of the input after "/"
    """
    parts = topic.split("/")
    return parts[-2:][0]


def get_topic_ids(topic: str) -> tuple[str, str]:
    """Gets `node_id` and `sensor_id`

    Args:
        topic: The MQTT topic for that message

    Returns:
        `node_id` and `sensor_id`
    """
    return get_second_last_part(topic), get_last_part(topic)


def get_device_topic(node_id: str, device_id: str, all_devices: list[str]) -> str:
    """Get the MQTT topic for a specific device.

    Args:
        node_id: Node ID.
        device_id: Device ID.
        all_devices: List of MQTT topics.

    Returns:
        The MQTT topic for the specified device, or an empty string if not found.
    """
    for device in all_devices:
        if node_id in device and device_id in device:
            return device
    return ""


def get_all_gui_topics(topics: list[str]) -> list[str]:
    """Gets all topics GUI should subscribe or publish to.

    Args:
        topics: list of all topics master knows of

    Returns:
        All topics GUI should interact with.
    """
    gui_commands = []

    for topic in topics:
        if "gui_command" in topic or "log" in topic:
            gui_commands.append(topic)

    return gui_commands


def get_floor(data: dict) -> str:
    """Gets the floor string from JSON.

    Args:
        data: JSON response

    Returns:
        Returns the first match in the dict as a string. E.g. floor_1
    """
    for i in data:
        if "floor" in i:
            return i
    return ""


def get_stages(floor: str, data: dict) -> list[str]:
    """Loops through floor and gives stages.

    Args:
        floor: name of floor
        data: JSON data

    Returns:
        A list of stage names in given floor.
    """
    stages = []

    if not data.get(floor):
        return stages

    for i in data[floor]:
        if "stage" not in i:
            continue

        stages.append(i)
    return stages


def get_stage_from_topic(topic: str) -> str:
    """Gives stage name given a topic.

    If there is no match, it will return `""`.

    Args:
        topic: The MQTT topic string

    Returns:
        The stage as a string. E.g stage_1
    """
    topics = topic.split("/")

    for i in topics:
        if "stage" in i:
            return i
    return ""


def get_floor_from_topic(topic: str) -> str:
    """Gives floor name given a topic.

    If there is no match, it will return `""`.

    Args:
        topic: The MQTT topic string

    Returns:
        The floor as a string. E.g floor_1
    """
    topics = topic.split("/")

    for i in topics:
        if "floor" in i:
            return i
    return ""


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
    # if not status in ["unchecked", "pending", "done"]:
    #     raise KeyError(f"{status} status does not exist!")
    return data.get("status") == status


def topic_contains(topic: str, *args: str) -> bool:
    """Check if any of the args given exists in the topic.

    Args:
        topic: name of topic
        *args: strings which should be checked for

    Returns:
        Wheter or not the topic contains one or more of the args.
    """
    for arg in args:
        if arg not in topic:
            continue

        return True

    return False


def get_topics_containing(topics: list[str], string: str) -> list[str]:
    """Filter topics that contain a specific string.

    Args:
        topics: List of MQTT topics.
        string: The string to check for in the topics.

    Returns:
        Filtered list of topics that contain the specified string.
    """
    result = []

    for topic in topics:
        if string not in topic:
            continue

        result.append(topic)

    return result


def get_unique_id(topic: str) -> str:
    """Gets a unique id for a device, given topic.

    Args:
        topic: MQTT topic string

    Returns:
        The unique id to be used. E.g. `floor_1/stage_1/climate_node/LED`
    """
    # from receipt
    # hydroplant/<something>/floor_1/stage_1/climate_node/LED
    # unsure which topic
    parts = topic.split("/")
    floor = get_floor_from_topic(topic)

    assert floor != "", "Topic must include floor!"

    stage = get_stage_from_topic(topic)

    offset = 1

    # we might not have stage
    if stage:
        offset = 2

    floor_index = parts.index(floor)
    node = parts[floor_index + offset]
    part = parts[floor_index + offset + 1]

    # floor_1/stage_1/climate_node/LED
    if stage:
        unqiue_id = "/".join([floor, stage, node, part])
    else:
        unqiue_id = "/".join([floor, node, part])

    # logging.debug(f"{unqiue_id=}")

    return unqiue_id


def get_data_type(topic: str) -> str:
    """Get the data type from an MQTT topic.

    Args:
        topic: The MQTT topic.

    Returns:
        The data type ("command", "measurement", "receipt") found in the topic.
    """
    for data_type in ["command", "measurement", "receipt"]:
        if data_type in topic:
            return data_type
    return ""


def is_receipt(topic: str) -> bool:
    """Check if the MQTT topic represents a receipt.

    Args:
        topic: The MQTT topic.

    Returns:
        True if the topic contains "/receipt", False otherwise.
    """
    return topic.find("/receipt") != -1
