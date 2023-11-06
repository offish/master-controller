from dataclasses import dataclass, asdict
from enum import IntEnum
import time
import logging


class EJobState(IntEnum):
    KILLED = -1
    UNCHECKED = 0
    QUEUED = 1
    PENDING = 2
    DONE = 3


class EJobPriority(IntEnum):
    DEFAULT = 1
    MEDIUM = 2
    HIGH = 3


def set_time() -> float:
    return time.time()


class Step:
    """
    wait: how long to wait after doing a step. say turning off water.
    how long does it take for the containers to empty?
    deadline: relative time which must be met, else it will kill the job
    """

    def __init__(
        self, topic: str, data: dict, wait: float = 0.0, deadline: float = 60.0
    ) -> None:
        self.topic = topic
        self.data = data
        self.wait = wait
        self.deadline = deadline  # will delete if stop passes deadline

        self.timestamp = time.time()
        self.time_sent = 0.0

        self.has_sent = False
        # self.has_finished = False

    def sent(self) -> None:
        self.has_sent = True
        self.time_sent = time.time()

    # def finish(self) -> None:
    #     self.finished = True

    def has_passed_deadline(self) -> bool:
        return time.time() >= self.timestamp + self.deadline

    def __str__(self) -> str:
        return f"{self.topic} {self.data}"


class Job:
    """a job consists of one or more steps"""

    def __init__(self, steps: list[Step]) -> None:
        self.steps: list[Step] = steps
        self.timestamp = time.time()
        self.state = EJobState.UNCHECKED
        self.is_done = False
        self.at_step = 0

    def done_with_steps(self) -> bool:
        # [1,2] max 1 +1 = 2
        return self.at_step == len(self.steps)

    def has_state(self, state: EJobState) -> bool:
        return self.state == state

    def set_state(self, state: EJobState) -> None:
        logging.debug(f"State changed to {state=}")
        self.state = state


# job = Job([Step("topic", {"value": 1})])

# step = Step("topic", {"some": "data"}, time.time())
# print(step)
# time.sleep(1)
# step1 = Step("topic", {"some": "data"}, time.time())
# print(step1)

# job.set_state(EJobState.PENDING)

# print(job)
