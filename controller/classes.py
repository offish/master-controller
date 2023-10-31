from utils import (
    get_floor_from_topic,
    get_stage_from_topic,
    get_unique_id,
    get_last_part,
    get_second_last_part,
)


class Entity:
    def __init__(self, unique_id: str) -> None:
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

    def get_command(self, **kwargs) -> tuple[str, dict]:
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

    def get_value(self) -> float | None:
        return self.value

    def set_data(self, data: dict) -> None:
        self.data = data
        self.value = data.get("value")

    def get_data(self) -> dict:
        return self.data

    def get_topic(self) -> str:
        return self.topic

    def get_receipt(self) -> str:
        return self.receipt

    def get_subscribe_topics(self) -> list[str]:
        return [self.gui_topic, self.receipt]


class LogicController(Entity):
    def __init__(self, unique_id: str) -> None:
        super().__init__(unique_id)


class Actuator(Entity):
    def __init__(self, unique_id: str) -> None:
        super().__init__(unique_id)


class Stage:
    # stage_1
    def __init__(self, name: str) -> None:
        self.name = name
        self.actuators: list[Actuator] = []

    def add_actuator(self, unique_id: str) -> Actuator:
        actuator = Actuator(unique_id)
        self.actuators.append(actuator)
        return actuator

    def get_actuator(self, unique_id: str) -> Actuator | None:
        for actuator in self.get_actuators():
            if unique_id != actuator.unique_id:
                continue

            return actuator
        return None

    def get_actuators(self) -> list[Actuator]:
        return self.actuators


class Floor:
    # floor_1
    def __init__(self, name: str, *stage_names) -> None:
        self.name = name
        self.stages: list[Stage] = [Stage(stage_name) for stage_name in stage_names]
        self.logic_controllers: list[LogicController] = []

    def get_logic_controllers(self) -> list[LogicController]:
        return self.logic_controllers

    def get_logic_controller(self, unique_id: str) -> LogicController | None:
        for logic_controller in self.get_logic_controllers():
            if unique_id != logic_controller.unique_id:
                continue

            return logic_controller
        return None

    def get_stage_by_name(self, name: str) -> Stage | None:
        for s in self.get_stages():
            if name != s.name:
                continue

            return s
        return None

    def get_stage(self, unique_id: str) -> Stage | None:
        stage = get_stage_from_topic(unique_id)

        if not stage:
            return None

        for s in self.get_stages():
            if stage != s.name:
                continue

            return s
        return None

    def get_stages(self) -> list[Stage]:
        return self.stages

    def add_logic_controller(self, unique_id: str) -> LogicController:
        logic_controller = LogicController(unique_id)
        self.logic_controllers.append(logic_controller)
        return logic_controller

    # def add_stage(self, stage_name: str) -> None:
    #     self.stages.append(Stage(stage_name))

    # def add_stages(self, *stage_names) -> None:
    #     [self.add_stage(stage_name) for stage_name in stage_names]


class Plant:
    pass


# have this class?
# class GUI:
#     def __init__(self) -> None:
#         pass


class HydroplantSystem:
    def __init__(self, *floors) -> None:
        self.floors: list[Floor] = [floor for floor in floors]
        # self.gui: GUI = None

    def add_floor(self, name: str) -> None:
        self.floors.append(Floor(name))

    def delete_objects(self, node_id: str) -> list[str]:
        """Delete actuators or logiccontrollers which has this node_id.
        returns the topics it subscribed to"""
        topics = []

        for floor in self.get_floors():
            for logic_controller in floor.get_logic_controllers():
                if node_id != logic_controller.node_id:
                    continue

                topics += logic_controller.get_subscribe_topics()
                floor.logic_controllers.remove(logic_controller)

            for stage in floor.get_stages():
                for actuator in stage.get_actuators():
                    if node_id != actuator.node_id:
                        continue

                    topics += actuator.get_subscribe_topics()
                    stage.actuators.remove(actuator)
        return topics

    def get_gui_topics(self) -> list[str]:
        topics = []

        # TODO: does this make sense? already gets these topics
        # when sending sync, maybe GUI already can handle this?

        for floor in self.get_floors():
            for logic_controller in floor.get_logic_controllers():
                topics.append(logic_controller.gui_topic)

            for stage in floor.get_stages():
                for actuator in stage.get_actuators():
                    topics.append(actuator.gui_topic)

        return topics

    def get_gui_sync_data(self) -> dict:
        data = {}

        for floor in self.get_floors():
            for logic_controller in floor.get_logic_controllers():
                data[logic_controller.gui_topic] = logic_controller.get_value()

            for stage in floor.get_stages():
                for actuator in stage.get_actuators():
                    data[actuator.gui_topic] = actuator.get_value()

        return data

    def get_floor_by_name(self, name: str) -> Floor | None:
        for f in self.get_floors():
            if name != f.name:
                continue

            return f
        return None

    def get_floor(self, unique_id: str) -> Floor | None:
        floor = get_floor_from_topic(unique_id)

        if not floor:
            return None

        for f in self.get_floors():
            if floor != f.name:
                continue

            return f
        return None

    def get_floors(self) -> list[Floor]:
        return self.floors


system = HydroplantSystem(
    Floor("floor_1", "stage_1", "stage_2", "stage_3"),
    Floor("floor_2", "stage_1", "stage_2", "stage_3"),
    Floor("floor_3", "stage_1", "stage_2", "stage_3"),
)

# add in floor1
system.floors[0].stages[0].actuators.append(
    Actuator("floor_1/stage_1/climate_node/LED")
)
system.floors[0].add_logic_controller(
    "floor_1/plant_information_node/plant_information"
)


# print([floor.name for floor in system.get_floors()])


def is_receipt(topic: str) -> bool:
    return topic.find("/receipt") != -1


def get_object(topic: str) -> LogicController | Actuator | None:
    if is_receipt(topic):
        topic.replace("/receipt", "")

    unique_id = get_unique_id(topic)

    floor = system.get_floor(unique_id)
    stage = floor.get_stage(unique_id)

    # most likely a logic controller
    # which only exists in floor, no stage
    if not stage:
        return floor.get_logic_controller(unique_id)

    return stage.get_actuator(unique_id)


# TODO: when connect, send command on previous state to have correct state
# if lights were on, send them to be on


# we want LED actuator
obj = get_object("hydroplant/command/floor_1/stage_1/climate_node/LED/receipt")
print(obj)

obj.set_data({"value": 1.03})

# we want plant_information logic controller
obj2 = get_object("hydroplant/command/floor_1/plant_information_node/plant_information")
print(obj2)


print(system.get_gui_sync_data())
# print(system.get_all_topics)

# for floor in system.get_floors():
#     for stage in floor.stages:
#         print(stage.name)
