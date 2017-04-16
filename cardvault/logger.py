import config
import enum


class LogLevel(enum.Enum):
    Error = 1
    Warning = 2
    Info = 3


def log(message, log_level):
    if log_level.value <= config.log_level:
        level_string = "[" + log_level.name + "] "
        print(level_string + message)
