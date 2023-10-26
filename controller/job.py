from dataclasses import dataclass, asdict
from enum import IntEnum
import time


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


@dataclass
class Step:
    """
    wait:  how long to wait after doing a step. say turning off water.
    how long does it take for the containers to empty?
    deadline: relative time which must be met, else it will kill the job
    """

    topic: str
    data: dict
    timestamp: float
    sent: bool = False
    finished: bool = False
    wait: float = 0.0
    deadline: float = 60.0  # will delete if step passes deadline

    def sent(self) -> None:
        self.sent = True

    def finish(self) -> None:
        self.finished = True


@dataclass
class Job:
    """a job consists of one or more steps"""

    steps: list[Step]
    state: EJobState = EJobState.UNCHECKED
    priority: EJobPriority = EJobPriority.DEFAULT

    def has_state(self, state: EJobState) -> bool:
        return self.state == state

    def set_state(self, state: EJobState) -> None:
        self.state = state


# job = Job([Step("topic", {"value": 1})])

step = Step("topic", {"some": "data"}, time.time())
print(step)
time.sleep(1)
step1 = Step("topic", {"some": "data"}, time.time())
print(step1)

# job.set_state(EJobState.PENDING)

# print(job)
