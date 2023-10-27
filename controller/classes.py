class Entity:
    def __init__(
        self, unique_id: str, command_topic: str, gui_topic: str = "", data: dict = {}
    ) -> None:
        self.unique_id = unique_id
        self.command_topic = command_topic
        self.gui_topic = gui_topic
        self.receipt_topic = command_topic + "/receipt"
        self.data = data

    def set_data(self, data: dict) -> None:
        self.data = data

    def get_data(self) -> dict:
        return self.data

    def get_topic(self) -> str:
        return self.topic


class LED(Entity):
    def __init__(
        self, unique_id: str, command_topic: str, gui_topic: str = "", data: dict = {}
    ) -> None:
        super().__init__(unique_id, command_topic, gui_topic, data)


class PlantHolder:
    def __init__(self) -> None:
        self.plants: list[Plant] = []


class Actuator(Entity):
    def __init__(
        self, unique_id: str, command_topic: str, gui_topic: str = "", data: dict = {}
    ) -> None:
        super().__init__(unique_id, command_topic, gui_topic, data)


class Stage:
    # stage_1
    def __init__(self, name: str) -> None:
        self.name = name
        self.actuators: list[Actuator] = []
        self.plant_holders: list[PlantHolder] = []


class LogicController:
    def __init__(self) -> None:
        pass


class PlantMoverNode(LogicController):
    name = "plant_mover"

    def __init__(self) -> None:
        pass


class PlantInformationNode(LogicController):
    name = "plant_information"

    def __init__(self) -> None:
        pass


class ClimateNode:
    name = "climate"

    def __init__(self) -> None:
        pass


ALL_LOGIC_CONTROLLERS: list[LogicController] = [
    PlantMoverNode,
    PlantInformationNode,
    ClimateNode,
]


class Floor:
    # floor_1
    def __init__(self, name: str, *stage_names) -> None:
        self.name = name
        self.stages: list[Stage] = [Stage(stage_name) for stage_name in stage_names]
        self.logic_controllers: list[LogicController] = []
        self.plant_mover: PlantMoverNode = None
        self.plant_information: PlantInformationNode = None
        self.climate: ClimateNode = None

    def get_stages(self) -> list[Stage]:
        return [stage for stage in self.stages]

    # def add_stage(self, stage_name: str) -> None:
    #     self.stages.append(Stage(stage_name))

    # def add_stages(self, *stage_names) -> None:
    #     [self.add_stage(stage_name) for stage_name in stage_names]


class Plant:
    pass


class GUI:
    def __init__(self) -> None:
        # all topics GUI wants?
        self.topics: list[str] = []


class HydroplantSystem:
    def __init__(self, *floors) -> None:
        self.floors: list[Floor] = [floor for floor in floors]
        self.gui: GUI = None

    def add_floor(self, name: str) -> None:
        self.floors.append(Floor(name))

    def get_floors(self) -> list[Floor]:
        return self.floors


a = Actuator("a", "dsa")

print(a.super())

# system = HydroplantSystem(
#     Floor("floor_1", "stage_1", "stage_2", "stage_3"),
#     Floor("floor_2", "stage_1", "stage_2", "stage_3"),
#     Floor("floor_3", "stage_1", "stage_2", "stage_3"),
# )

# print([floor.name for floor in system.get_floors()])

# # for floor in system.get_floors():
# #     floor.add_stages("stage_1", "stage_2", "stage_3")


# for floor in system.get_floors():
#     for stage in floor.stages:
#         print(stage.name)
