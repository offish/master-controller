from .job import Job, Step, EJobState
from .hydroplant import HydroplantSystem, EntityType, Entity

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
        wait: float = 1.0,
    ) -> None:
        """Initialize Autonomy object.

        Args:
            system: The HydroplantSystem instance.
            publish_callback: Callback to communicate with MQTT.
            log_callback: Callback for logging.
            wait: How long autonomy should sleep for each cycle.
        """
        self.data: list[dict] = []  # specific data master-controller receives
        self.jobs: list[Job] = []  # all pending jobs

        self.is_enabled = True  # turn on/off autonomy logic
        self.publish = publish_callback  # callback to communicate with MQTT
        self.system: HydroplantSystem = system

        self.log = log_callback  # callback for logging
        self.wait = wait  # how long autonomy should sleep for each cycle
        self.time = 0.0  # current time, used for lights
        self.last_status_print = 0.0
        self.status_interval = 30  #
        self.last_interval_check = 0.0
        # TODO: turn this up after demo
        self.interval_check_timeout = 15  # every 300 seconds

        self.inspected_demo_plants = True
        self.moved_demo_plants = True

    def enable(self) -> None:
        """Enable the autonomy."""
        self.is_enabled = True

    def disable(self) -> None:
        """Disable the autonomy."""
        self.is_enabled = False

    def __delete_job(self, job: Job) -> None:
        """Delete a job from the list.

        Args:
            job: The Job instance to be deleted.
        """
        self.jobs.remove(job)
        logging.debug(f"Deleted job {job}")

    def __check_lights(self) -> None:
        """Check and control the lights based on the current hour."""
        hour = dt.datetime.now().hour

        logging.debug(f"current hour {hour}")

        for actuator in self.system.get_actuators():
            if not actuator.is_type(EntityType.LED):
                continue

            # TODO: replace with actuator.ruleset
            if 7 < hour and hour < 21:
                logging.debug("turn on lights")
                step = Step(*actuator.get_command(value=1))
            else:
                logging.debug("turn off lights")
                step = Step(*actuator.get_command(value=0))

            self.__add_job([step])

    def __inspect_plants(self) -> None:
        """Inspect plants and queue jobs if ready to move."""
        # loop through each place
        # take pic
        # if ready to move -> add job
        # this job includes turn off water, then move
        # job must use moving algo

        # TODO: change just for demo
        if self.inspected_demo_plants:
            logging.debug("already inspected plants")
            return

        plant_information = self.system.get_object_from_unique_id(
            "floor_1/plant_information_node/plant_information"
        )

        # not connected yet
        if plant_information is None:
            logging.warning("Plant plant_information still not connected")
            return

        logging.warning("Plant plant_information connected!!! QUEUE JOBS!!")

        # TODO: need to change command not use from
        self.__add_job(
            [
                Step(
                    *plant_information.get_command(to=i),
                    deadline=240,
                    wait=10,
                )
                for i in range(5, 8 + 1)
            ]
        )

        logging.debug("INSPECTED DEMO PLANTS")

        self.inspected_demo_plants = True

    def __check_water(self):
        pass

    def __check_move_plants(self) -> None:
        """Check if plants should be moved and queue jobs accordingly."""
        # first check if we should move or not

        if self.moved_demo_plants:
            logging.debug("already moved plants")
            return

        # TODO: change all of this afterwards
        # for demonstration purposes
        # move every plant holder in stage 2
        # to stage 3

        plant_mover = self.system.get_object_from_unique_id(
            "floor_1/plant_mover_node/plant_mover"
        )

        # not connected yet
        if plant_mover is None:
            logging.warning("Plant mover still not connected")
            return

        logging.warning("Plant mover connected!!! QUEUE JOBS!!")

        # TODO: need to change command not use from
        self.__add_job(
            [
                Step(
                    *plant_mover.get_command(
                        **{"command": "goto", "from": 8, "to": 12}
                    ),
                    deadline=240,
                ),
                Step(
                    *plant_mover.get_command(
                        **{"command": "goto", "from": 7, "to": 11}
                    ),
                    deadline=240,
                ),
                Step(
                    *plant_mover.get_command(
                        **{"command": "goto", "from": 6, "to": 10}
                    ),
                    deadline=240,
                ),
                Step(
                    *plant_mover.get_command(**{"command": "goto", "from": 5, "to": 9}),
                    deadline=240,
                ),
            ]
        )

        logging.debug("SET MOVED DEMO PLANTS TO TRUE")

        self.moved_demo_plants = True

        # any_should_move = False

        # for plant_holder in self.system.get_plant_holders():
        #     if plant_holder.should_move():
        #         any_should_move = True
        #         break

        # if not any_should_move:
        #     return

        # algorithm for queueing which plant holders to move where

    def __check_interval_jobs(self):
        """Check interval jobs and queue if necessary."""
        if self.time < self.last_interval_check + self.interval_check_timeout:
            return

        logging.info("Checking interval jobs")
        self.__check_lights()
        self.__inspect_plants()
        self.__check_move_plants()
        self.__check_water()
        self.last_interval_check = self.time

    def __has_step_awaited_value(self, step: Step) -> bool:
        """Check if the step has awaited value.

        Args:
            step: The Step instance.

        Returns:
            True if the step has the awaited value, else False.
        """
        obj = self.system.get_object(step.topic)

        if not obj:
            return False

        # TODO: change after demo
        # we do not have "value" for plant_mover logic controller
        if obj.id == "plant_mover":
            # TODO: change stage to something else
            # logging.debug(f"checking awaited value {obj.__dict__} {step.__dict__}")
            return step.data["to"] == obj.data.get("stage")

        if obj.id == "plant_information":
            return step.data["to"] == obj.data.get("to")

        return step.data["value"] == obj.value

    def __do_job(self) -> None:
        """Execute one job at a time, following the FIFO principle."""
        # we have pending jobs
        if len(self.jobs) == 0:
            # logging.debug("No new jobs available")
            return

        # we only want to do one job at a time
        # first job is the one we care about
        job = self.jobs[0]

        # job has been killed -> delete
        if job.has_state(EJobState.KILLED):
            logging.warning("Job has been killed")
            self.__delete_job(job)
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

            # for step in job.steps:
            if job.done_with_steps():
                logging.debug(f"Done with all steps in job {job=}")
                job.set_state(EJobState.DONE)
                return

            step = job.steps[job.at_step]

            if not step.has_sent:
                # actually do step
                self.publish(step.topic, step.data)
                step.sent()
                return

            if step.has_passed_deadline():
                job.set_state(EJobState.KILLED)
                return

            if self.__has_step_awaited_value(step):
                # wait is time to wait AFTER step is done
                logging.debug(f"Step has finished!")
                time.sleep(step.wait)
                job.at_step += 1
                return

            # logging.debug(f"Waiting for step {step=} to finish, has been sent")

    def __entity_has_step_value(self, step: Step, entity: Entity) -> bool:
        """Check if the entity has the expected value for the given step.

        Args:
            step: The Step instance.
            entity: The Entity instance.

        Returns:
            True if the entity has the expected value, else False.
        """
        # TODO: remove
        print(step.data)

        value = step.data.get("value")

        if value is None:
            return False

        return value == entity.get_value()

    def __step_already_in_queue(self, step: Step) -> bool:
        """Check if the step is already in the job queue.

        Args:
            step: The Step instance.

        Returns:
            True if the step is already in the queue, else False.
        """
        for job in self.jobs:
            # only compare with queued jobs
            if job.state != EJobState.QUEUED:
                continue

            for queued_step in job.steps:
                # equal means duplicate
                if str(step) == str(queued_step):
                    # logging.debug(f"STEP IS ALREADY IN QUEUE {step.__dict__}")
                    return True

        return False

    def __add_job(self, steps: list[Step]) -> None:
        """Add a new job to the job queue.

        Args:
            steps: List of Step instances to be included in the new job.
        """
        # TODO: check if value != current value
        # no need to add job if it already is set to that
        steps_to_do = []

        for step in steps:
            entity = self.system.get_object(step.topic)

            # logging.debug(f"{entity.__dict__=}")
            # logging.debug(f"{step.__dict__=}")

            # TODO: make exception for this later
            if entity.get_value() is None:
                # not turned on yet?
                pass

            # check if entity already has this value
            if self.__entity_has_step_value(step, entity):
                continue

            if self.__step_already_in_queue(step):
                continue

            steps_to_do.append(step)

        logging.debug(f"{steps_to_do=}")

        if not steps_to_do:
            return

        job = Job(steps_to_do)
        job.set_state(EJobState.QUEUED)
        self.jobs.append(job)

        logging.info(f"Added job!")

    def run(self) -> None:
        """Run the autonomy logic continuously."""
        while True:
            self.time = time.time()

            if self.is_enabled:
                if self.time > self.last_status_print + self.status_interval:
                    logging.debug("Autonomy is enabled")
                    logging.debug(f"{self.jobs=}")
                    self.last_status_print = self.time

                self.__check_interval_jobs()
                # self.__check_move_plants()
                self.__do_job()
            else:
                logging.warning("Autonomy is disabled")

            time.sleep(self.wait)
