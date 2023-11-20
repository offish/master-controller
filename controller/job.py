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


# def set_time() -> float:
#     return time.time()


class Step:
    def __init__(
        self, topic: str, data: dict, wait: float = 0.0, deadline: float = 60.0
    ) -> None:
        """A step in a job.

        Args:
            topic: The MQTT topic for the step.
            data: Data associated with the step.
            wait: How long to wait after performing the step.
            deadline: The relative time within which the step must be completed.
        """
        self.topic = topic
        self.data = data
        self.wait = wait
        self.deadline = deadline  # will delete if stop passes deadline

        self.timestamp = time.time()
        self.time_sent = 0.0

        self.has_sent = False
        # self.has_finished = False

    def sent(self) -> None:
        """Mark the step as sent."""
        self.has_sent = True
        self.time_sent = time.time()

    # def finish(self) -> None:
    #     self.finished = True

    def has_passed_deadline(self) -> bool:
        """Check if the step has passed its deadline.

        Returns:
            True if the step has passed its deadline, False otherwise.
        """
        return time.time() >= self.timestamp + self.deadline

    def __str__(self) -> str:
        """Return a string representation of the step."""
        return f"{self.topic} {self.data}"


class Job:
    def __init__(self, steps: list[Step]) -> None:
        """Initialize a Job instance.

        Args:
            steps: List of steps in the job.
        """
        self.steps: list[Step] = steps
        self.timestamp = time.time()
        self.state = EJobState.UNCHECKED
        self.is_done = False
        self.at_step = 0

    def done_with_steps(self) -> bool:
        """Check if all steps in the job are done.

        Returns:
            True if all steps are done, False otherwise.
        """
        return self.at_step == len(self.steps)

    def has_state(self, state: EJobState) -> bool:
        """Check if the job has a specific state.

        Args:
            state: The state to check.

        Returns:
            True if the job has the specified state, False otherwise.
        """
        return self.state == state

    def set_state(self, state: EJobState) -> None:
        """Set the state of the job.

        Args:
            state: The new state.
        """
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
