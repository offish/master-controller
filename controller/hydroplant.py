from .utils import (
    get_floor_from_topic,
    get_stage_from_topic,
    get_unique_id,
    get_last_part,
    get_second_last_part,
    is_receipt,
)

from enum import IntEnum
import logging


class EntityType(IntEnum):
    PLANT_MOVER = 1
    PLANT_INFORMATION = 2
    WATER_CONTROLLER = 3
    LED = 4
    STEPPER = 5
    WATER_PUMP = 6
    WATER_PUMP_NUT = 7
    VALVE = 8
    VALVE_FLUSH = 9
    NPK = 10
    NUTRITION_CONTROLLER = 11
    PH_REGULATOR = 12
    EC_REGULATOR = 13
    WATER_CIRC = 14


class Entity:
    """Base class for different entities in the Hydroplant system."""

    def __init__(self, unique_id: str) -> None:
        """Initialize an Entity instance.

        Args:
            unique_id: Unique identifier for the entity.
        """
        # floor_1/stage_1/climate_node/LED or
        # floor_1/plant_information_node/plant_information
        self.unique_id = unique_id

        self.value = None
        self.data = {}

        self.topic = "hydroplant/{}/" + unique_id
        self.command = self.topic.format("command")
        self.receipt = self.command + "/receipt"
        self.gui_topic = self.topic.format("gui_command")

        self.id = get_last_part(unique_id)
        self.floor = get_floor_from_topic(unique_id)
        self.stage = get_stage_from_topic(unique_id)  # could be ""
        self.node_id = get_second_last_part(unique_id)

        self.type = EntityType[self.id.upper()]

        # logging.debug(f"created object for {unique_id=}")

    def get_command(self, **kwargs) -> tuple[str, dict]:
        """Get the command topic and data for the entity.

        Returns:
            Tuple containing the command topic and a dictionary with command data.
        """
        # TODO: add if test here to check if plant_mover and add "command": "goto"

        return (
            self.command,
            {
                **kwargs,
                "device_id": self.node_id,
                "id": self.id,
                "floor": self.floor,
                "stage": self.stage,
            },
        )

    def is_type(self, entity_type: EntityType) -> bool:
        """Check if the entity is of the specified type.

        Args:
            entity_type: The EntityType to check against.

        Returns:
            True if the entity is of the specified type, False otherwise.
        """
        return entity_type == self.type

    def get_value(self) -> float | int | None:
        """Get the value of the entity.

        Returns:
            The value of the entity.
        """
        return self.value

    def set_data(self, data: dict) -> None:
        """Set the data for the entity.

        Args:
            data: The data to set for the entity.
        """
        self.data = data
        self.value = data.get("value")

    def get_data(self) -> dict:
        """Get the data for the entity.

        Returns:
            The data for the entity.
        """
        return self.data

    def get_topic(self) -> str:
        """Get the MQTT topic for the entity.

        Returns:
            The MQTT topic for the entity.
        """
        return self.topic

    def get_receipt(self) -> str:
        """Get the receipt topic for the entity.

        Returns:
            The receipt topic for the entity.
        """
        return self.receipt

    def get_subscribe_topics(self) -> list[str]:
        """Get the topics to subscribe to for the entity.

        Returns:
            A list of topics to subscribe to for the entity.
        """
        return [self.gui_topic, self.receipt]


class LogicController(Entity):
    """Class representing a logic controller entity."""

    def __init__(self, unique_id: str) -> None:
        """Initialize a LogicController instance.

        Args:
            unique_id: Unique identifier for the logic controller.
        """
        super().__init__(unique_id)


class Actuator(Entity):
    """Class representing an actuator entity."""

    def __init__(self, unique_id: str) -> None:
        """Initialize an Actuator instance.

        Args:
            unique_id: Unique identifier for the actuator.
        """
        super().__init__(unique_id)


def stage_name_to_value(stage: str) -> int:
    """Convert a stage name to its corresponding numerical value.

    Args:
        stage: The stage name.

    Returns:
        The numerical value of the stage.
    """
    return int(stage.replace("stage_", ""))


class PlantHolder:
    """Class representing a plant holder entity."""

    def __init__(self, place: int) -> None:
        """Initialize a PlantHolder instance.

        Args:
            place: The place of the plant holder.
        """
        self.place = place
        # self.current_stage = "stage_0"
        # self.wanted_stage = "stage_0"

    # def should_move(self) -> bool:
    #     wanted_stage = stage_name_to_value(self.wanted_stage)
    #     current_stage = stage_name_to_value(self.current_stage)

    #     return wanted_stage > current_stage

    # def update_stage(self, stage: str) -> None:
    #     self.wanted_stage = stage


class Stage:
    """Class representing a stage in the Hydroplant system."""

    # stage_1
    def __init__(self, name: str) -> None:
        """Initialize a Stage instance.

        Args:
            name: The name of the stage.
        """
        self.name = name
        self.actuators: list[Actuator] = []
        self.plant_holders: list[PlantHolder] = []

    def get_plant_holders(self) -> list[PlantHolder]:
        """Get the plant holders in the stage.

        Returns:
            A list of plant holders in the stage.
        """
        return self.plant_holders

    def add_actuator(self, unique_id: str) -> Actuator:
        """Add an actuator to the stage.

        Args:
            unique_id: Unique identifier for the actuator.

        Returns:
            The added actuator.
        """
        actuator = Actuator(unique_id)
        self.actuators.append(actuator)
        return actuator

    def get_actuator(self, unique_id: str) -> Actuator | None:
        """Get an actuator by its unique ID.

        Args:
            unique_id: Unique identifier for the actuator.

        Returns:
            The actuator with the specified unique ID, or None if not found.
        """
        for actuator in self.get_actuators():
            if unique_id != actuator.unique_id:
                continue

            return actuator
        return None

    def get_actuators(self) -> list[Actuator]:
        """Get all actuators in the stage.

        Returns:
            A list of actuators in the stage.
        """
        return self.actuators


class Floor:
    """Class representing a floor in the Hydroplant system."""

    # floor_1
    def __init__(self, name: str, *stage_names) -> None:
        """Initialize a Floor instance.

        Args:
            name: The name of the floor.
            stage_names: Names of the stages in the floor.
        """
        self.name = name
        self.stages: list[Stage] = [Stage(stage_name) for stage_name in stage_names]
        self.logic_controllers: list[LogicController] = []

    def get_logic_controllers(self) -> list[LogicController]:
        """Get the logic controllers in the floor.

        Returns:
            A list of logic controllers in the floor.
        """
        return self.logic_controllers

    def get_logic_controller(self, unique_id: str) -> LogicController | None:
        """Get a logic controller by its unique ID.

        Args:
            unique_id: Unique identifier for the logicc ontroller.

        Returns:
            The logic controller with the specified unique ID, or None if not found.
        """
        for logic_controller in self.get_logic_controllers():
            if unique_id != logic_controller.unique_id:
                continue

            return logic_controller
        return None

    def get_stage_by_name(self, name: str) -> Stage | None:
        """Get a stage in the floor by its name.

        Args:
            name: The name of the stage.

        Returns:
            The stage with the specified name, or None if not found.
        """
        for s in self.get_stages():
            if name != s.name:
                continue

            return s
        return None

    def get_stage(self, unique_id: str) -> Stage | None:
        """Get a stage in the floor by its unique ID.

        Args:
            unique_id: Unique identifier for the stage.

        Returns:
            The stage with the specified unique ID, or None if not found.
        """
        stage = get_stage_from_topic(unique_id)

        if not stage:
            return None

        for s in self.get_stages():
            if stage != s.name:
                continue

            return s
        return None

    def get_stages(self) -> list[Stage]:
        """Get all stages in the floor.

        Returns:
            A list of stages in the floor.
        """
        return self.stages

    def add_logic_controller(self, unique_id: str) -> LogicController:
        """Add a logic controller to the floor.

        Args:
            unique_id: Unique identifier for the logic controller.

        Returns:
            The added logic controller.
        """
        logic_controller = LogicController(unique_id)
        self.logic_controllers.append(logic_controller)
        return logic_controller

    def get_stages(self) -> list[Stage]:
        """Get all stages in the floor.

        Returns:
            A list of stages in the floor.
        """
        return [stage for stage in self.stages]


class HydroplantSystem:
    """Class representing the entire Hydroplant system."""

    def __init__(self, *floors) -> None:
        """Initialize a HydroplantSystem instance.

        Args:
            *floors: Variable number of Floor instances.
        """
        self.floors: list[Floor] = [floor for floor in floors]
        # self.gui: GUI = None

    def get_plant_holders(self) -> list[PlantHolder]:
        """Get all plant holders in the system.

        Returns:
            A list of plant holders in the system.
        """
        plant_holders = []

        for floor in self.get_floors():
            for stage in floor.get_stages():
                plant_holders += stage.get_plant_holders()

        return plant_holders

    def get_actuators(self) -> list[Actuator]:
        """Get all actuators in the system.

        Returns:
            A list of actuators in the system.
        """
        actuators = []

        for floor in self.get_floors():
            for stage in floor.get_stages():
                actuators += stage.get_actuators()

        return actuators

    def add_floor(self, name: str) -> None:
        """Add a floor to the system.

        Args:
            name: The name of the floor to add.
        """
        self.floors.append(Floor(name))

    def delete_objects(self, node_id: str, floor_name: str) -> list[str]:
        """Delete actuators or logic controllers which has this node_id.

        Args:
            node_id: The node ID to search for.
            floor_name: The floor name to filter objects, or None to search all floors.

        Returns:
            A list of topics the deleted objects subscribed to.
        """
        topics = []

        for floor in self.get_floors():
            if floor_name and floor_name != floor.name:
                continue

            # must copy or else we wont delete all objects
            for logic_controller in floor.get_logic_controllers().copy():
                if node_id != logic_controller.node_id:
                    continue

                topics += logic_controller.get_subscribe_topics()
                floor.logic_controllers.remove(logic_controller)
                # logging.debug(
                #     f"deleted {logic_controller=} with {node_id=} {floor_name=}"
                # )

            for stage in floor.get_stages():
                # must copy or else we wont delete all objects
                for actuator in stage.get_actuators().copy():
                    logging.debug(f"{actuator.unique_id=}")

                    if node_id != actuator.node_id:
                        continue

                    topics += actuator.get_subscribe_topics()
                    stage.actuators.remove(actuator)
                    # logging.debug(
                    #     f"deleted {actuator.unique_id=} with {node_id=} {floor_name=}"
                    # )

        return topics

    def get_gui_topics(self) -> list[str]:
        """Get all GUI topics in the system.

        Returns:
            A list of GUI topics in the system.
        """
        topics = []

        for floor in self.get_floors():
            for logic_controller in floor.get_logic_controllers():
                topics.append(logic_controller.gui_topic)

            for stage in floor.get_stages():
                for actuator in stage.get_actuators():
                    topics.append(actuator.gui_topic)

        return topics

    def get_logic_controllers(self) -> list[LogicController]:
        """Get all logic controllers for all floors.

        Returns:
            A list of logic controllers for all floors.
        """
        logic_controllers = []

        for floor in self.get_floors():
            for logic_controller in floor.get_logic_controllers():
                logic_controllers.append(logic_controller)

        return logic_controllers

    def get_state(self) -> dict:
        """Get the state of the system.

        Returns:
            A dictionary representing the state of the system.
        """
        data = {}

        for actuator in self.get_actuators():
            data[actuator.unique_id] = actuator.get_value()

        return data

    def get_gui_sync_data(self) -> dict:
        """Get GUI synchronization data for the system.

        Returns:
            A dictionary containing GUI synchronization data for the system.
        """
        data = {}

        for actuator in self.get_actuators():
            data[actuator.gui_topic] = actuator.get_value()

        # TODO: are there states for logic controllers?
        for logic_controller in self.get_logic_controllers():
            data[logic_controller.gui_topic] = logic_controller.get_value()

        return data

    def get_floor_by_name(self, name: str) -> Floor | None:
        """Get a floor by its name.

        Args:
            name: The name of the floor.

        Returns:
            The floor with the specified name, or None if not found.
        """
        for f in self.get_floors():
            if name != f.name:
                continue

            return f
        return None

    def get_floor(self, unique_id: str) -> Floor | None:
        """Get a floor by its unique ID.

        Args:
            unique_id: Unique identifier for the floor.

        Returns:
            The floor with the specified unique ID, or None if not found.
        """
        floor = get_floor_from_topic(unique_id)

        if not floor:
            return None

        for f in self.get_floors():
            if floor != f.name:
                continue

            return f
        return None

    def get_floors(self) -> list[Floor]:
        """Get all floors in the system.

        Returns:
            A list of floors in the system.
        """
        return self.floors

    def get_object_from_unique_id(
        self, unique_id: str
    ) -> LogicController | Actuator | None:
        """Get an object (LogicController or Actuator) by its unique ID.

        Args:
            unique_id: Unique identifier for the object.

        Returns:
            The object with the specified unique ID, or None if not found.
        """
        floor = self.get_floor(unique_id)
        stage = floor.get_stage(unique_id)

        # most likely a logic controller
        # which only exists in floor, no stage
        if not stage:
            return floor.get_logic_controller(unique_id)

        return stage.get_actuator(unique_id)

    def get_object(self, topic: str) -> LogicController | Actuator | None:
        """Get an object (LogicController or Actuator) by its MQTT topic.

        Args:
            topic: The MQTT topic for the object.

        Returns:
            The object with the specified topic, or None if not found.
        """
        if is_receipt(topic):
            topic.replace("/receipt", "")

        unique_id = get_unique_id(topic)
        return self.get_object_from_unique_id(unique_id)


# system = HydroplantSystem(
#     Floor("floor_1", "stage_1", "stage_2", "stage_3"),
#     Floor("floor_2", "stage_1", "stage_2", "stage_3"),
#     Floor("floor_3", "stage_1", "stage_2", "stage_3"),
# )

# print([floor.name for floor in system.get_floors()])

# for floor in system.get_floors():
#     floor.add_stages("stage_1", "stage_2", "stage_3")

# add in floor1
# system.floors[0].stages[0].actuators.append(
#     Actuator("floor_1/stage_1/climate_node/LED")
# )
# system.floors[0].add_logic_controller(
#     "floor_1/plant_information_node/plant_information"
# )


# print([floor.name for floor in system.get_floors()])
