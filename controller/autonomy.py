from .utils import get_unique_id, get_last_part, get_data_type
from .job import Job, Step, EJobState
from .hydroplant import HydroplantSystem, EntityType

import datetime as dt
import logging
import time


class Autonomy:
    """Class for running the autonomy logic.

    Defaults to be enabled.
    """

    def __init__(
        self,
        system,
        publish_callback,
        log_callback,
        count: int = 1_000,
        wait: float = 1.0,
    ) -> None:
        self.data: list[dict] = []  # specific data master-controller receives
        self.jobs: list[Job] = []  # all pending jobs
        self.count = count  # amount of data autonomy should remember
        self.is_enabled = True  # turn on/off autonomy logic
        self.publish = publish_callback  # callback to communicate with MQTT
        self.system: HydroplantSystem = system

        self.log = log_callback  # callback for logging
        self.wait = wait  # how long autonomy should sleep for each cycle
        self.time = 0.0  # current time, used for lights

    def enable(self) -> None:
        """Enable the autonomy."""
        self.is_enabled = True

    def disable(self) -> None:
        """Disable the autonomy."""
        self.is_enabled = False

    def __delete_job(self, job: Job) -> None:
        self.jobs.remove(job)

    def __check_lights(self) -> None:
        hour = dt.datetime.now().hour

        logging.debug(f"current hour {hour}")

        for actuator in self.system.get_actuators():
            if not actuator.is_type(EntityType.LED):
                continue

            # TODO: replace with actuator.ruleset
            if hour < 21 or hour > 7:
                step = Step(*actuator.get_command(value=1))
            else:
                step = Step(*actuator.get_command(value=0))

            self.__add_job([step])

    def __check_plants_ready_to_move(self) -> None:
        # loop through each place
        # take pic
        # if ready to move -> add job
        # this job includes turn off water, then move
        # job must use moving algo

        pass

    def __check_water(self):
        pass

    def __check_interval_jobs(self):
        # TODO: check time here, time now last check + timeout
        self.__check_plants_ready_to_move()
        self.__check_lights()
        self.__check_water()

    # def __process_data(self, topic: str, data: dict) -> None:
    #     """here jobs gets added"""
    #     # topic:

    #     data_type = get_data_type(topic)

    #     if not data_type:
    #         return

    #     # measurement -> camera -> move
    #     # receipt -> delete
    #     # command -> do

    #     match data_type:
    #         # case "command":
    #         #     self.__process_command(topic, data)
    #         #     pass

    #         # case "measurement":
    #         #     self.__process_measurement(topic, data)
    #         #     pass

    #         case "receipt":
    #             # self.__process_receipt(topic,data)
    #             pass

    #     # the data goes from unchecked -> checked
    #     self.__set_data_status("checked", data)

    def __has_step_awaited_value(self, step: Step) -> bool:
        obj = self.system.get_object(step.topic)

        if step.data["value"] != obj.value:
            return False
        return True

    def __do_job(self) -> None:
        """does one job at a time, FIFO"""
        # we have pending jobs
        if len(self.jobs) == 0:
            logging.debug("No new jobs available")
            return

        # we only want to do one job at a time
        # first job is the one we care about
        job = self.jobs[0]

        # job has been killed -> delete
        if job.has_state(EJobState.KILLED):
            self.jobs.remove(job)
            logging.warning(f"Deleted killed job {job=}")
            return

        if job.has_state(EJobState.DONE):
            # job is done,
            self.__delete_job(job)
            return

        # set next job in line to queued->pending
        if job.has_state(EJobState.QUEUED):
            job.set_state(EJobState.PENDING)

        if job.has_state(EJobState.PENDING):
            # actually do job
            # get step
            step = job.steps[job.at_step]

            # for step in job.steps:
            if job.done_with_steps():
                logging.debug(f"Done with all steps in job {job=}")
                job.set_state(EJobState.DONE)
                return

            if not step.has_sent:
                # actually do step
                self.publish(step.topic, step.data)
                step.sent()
                return

            if step.has_passed_deadline():
                job.set_state(EJobState.KILLED)
                return

            if step.has_passed_wait_time():
                job.set_state(EJobState.KILLED)
                return

            if self.__has_step_awaited_value():
                # wait is time to wait AFTER step is done
                logging.debug(f"Step has finished!")
                time.sleep(step.wait)
                job.at_step += 1
                return

            logging.debug(f"Waiting for step {step=} to finish, has been sent")

    def __add_job(self, steps: list[Step]) -> None:
        job = Job(steps)
        job.set_state(EJobState.QUEUED)
        self.jobs.append(job)

        logging.info(f"Added job! jobs is now{self.jobs=}")

    def run(self) -> None:
        while True:
            logging.info("Autonomy is running")
            # self.time = time.time()

            if self.is_enabled:
                logging.debug("Autonomy is enabled")
                self.__check_interval_jobs()
                self.__do_job()
            else:
                logging.warning("Autonomy is disabled")

            time.sleep(self.wait)
