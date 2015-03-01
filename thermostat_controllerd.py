#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import argparse
import sys
import time
import signal, os
import RPi.GPIO as GPIO

# Defaults
LOG_FILENAME = "/var/log/thermostat_controllerd.log"
LOG_LEVEL = logging.WARNING  # Could be e.g. "DEBUG" or "WARNING"
OPERATION_MODE_FILENAME = "/var/www/thermostat_operation_mode"

# Define and parse command line arguments
parser = argparse.ArgumentParser(description="thermostat_controllerd Python service")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")

# If the log file is specified on the command line then override the default
args = parser.parse_args()
if args.log:
    LOG_FILENAME = args.log

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
    def __init__(self, logger, level):
        """Needs a logger and a logger level."""
        self.logger = logger
        self.level = level

    def write(self, message):
        # Only log if there is a message (not just a new line)
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)

### Settings ###
PIN_THERMOSTAT_MODE = 17
UPDATE_OPERATION_MODE_INTERVAL = 15

# Configure pin for relay control
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_THERMOSTAT_MODE, GPIO.OUT)
GPIO.output(PIN_THERMOSTAT_MODE, False)

# Function to handle cleaning up the GPIO
def handler(signum, frame):
    logger.info("Caught SIGTERM. Cleaning up GPIO and exiting")
    GPIO.cleanup()
    exit()

# Register handler function on SIGTERM
signal.signal(signal.SIGTERM, handler)

def thermostat_manual_mode():
    GPIO.output(PIN_THERMOSTAT_MODE, True)

def thermostat_auto_mode():
    GPIO.output(PIN_THERMOSTAT_MODE, False)

def update_operation_mode():
    try:
        with open(OPERATION_MODE_FILENAME) as f:
            operation_mode = f.readline()
            operation_mode = operation_mode.rstrip()
            logger.debug("Reading operation mode in " +\
            OPERATION_MODE_FILENAME + ": " +\
            operation_mode)
            if operation_mode == "auto":
                thermostat_auto_mode()
            elif operation_mode == "manual":
                thermostat_manual_mode()
            else:
                logger.warning(
                    "Unknown operation mode " +\
                    operation_mode +\
                    " in " +\
                    OPERATION_MODE_FILENAME)

    except IOError:
        logger.warning(
            "Could not read operation mode from " +\
            OPERATION_MODE_FILENAME)

# Loop forever, doing something useful hopefully:
while True:
    try:
        logger.debug("Updating operation mode...")
        update_operation_mode()
        time.sleep(UPDATE_OPERATION_MODE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Caught KeyboardInterrupt. Cleaning up GPIO and exiting")
        GPIO.cleanup()
        exit()
