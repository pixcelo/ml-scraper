import os
import sys
from loguru import logger

class Logger:
    def __init__(self, log_name, log_level="INFO"):
        logger.remove()
        logger.add(
            f"log/{log_name}.log",
            level="INFO",
            format="{time} - {name} : [{level}] {message}",
            rotation="10 MB"
        )

        # Add console handler to output logs to terminal
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time}</green> - {name} : <yellow>[{level}]</yellow> {message}"
        )

        # Create log folder if it doesn't exist
        if not os.path.exists("log"):
            os.makedirs("log")

    def __call__(self):
        return logger