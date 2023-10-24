from dataclasses import dataclass


@dataclass
class Step:
    pass


@dataclass
class Job:
    steps: list[Step]
    pass
