from controller.controller import Controller

import logging
import sys


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/logs.log"),
    ],
)

if __name__ == "__main__":
    controller = Controller()
    controller.run()
