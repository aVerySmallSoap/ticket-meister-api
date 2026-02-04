from enum import Enum


class Priorities(int, Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    HIGHEST = 4