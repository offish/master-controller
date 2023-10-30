from utils import get_floor_from_topic, get_stage_from_topic, get_unique_id


class Entity:
    def __init__(self, unique_id: str) -> None:
        self.unique_id = unique_id
        self.data = {}

        self.topic = "hydroplant/{}/" + unique_id
        self.command = self.topic.format("command")
        self.receipt = self.command + "/receipt"
        self.gui_topic = self.topic.format("gui_command")

    def get_command(self, **kwargs) -> tuple[str, dict]:
        # TODO: have access to mqtt instance so it can
        # send instead of just giving the
        return None

    def set_data(self, data: dict) -> None:
        self.data = data

    def get_data(self) -> dict:
        return self.data

    def get_topic(self) -> str:
        return self.topic

    def get_receipt(self) -> str:
        return self.receipt


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

    def get_logic_controller(self, unique_id: str) -> LogicController | None:
        for logic_controller in self.logic_controllers:
            if unique_id != logic_controller.unique_id:
                continue

            return logic_controller
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

    def add_logic_controller(self, unique_id: str) -> None:
        self.logic_controllers.append(LogicController(unique_id))

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


# we want LED actuator
obj = get_object("hydroplant/command/floor_1/stage_1/climate_node/LED/receipt")
print(obj.topic)

# we want plant_information logic controller
obj2 = get_object("hydroplant/command/floor_1/plant_information_node/plant_information")
print(obj2)


# for floor in system.get_floors():
#     for stage in floor.stages:
#         print(stage.name)
