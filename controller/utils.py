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
