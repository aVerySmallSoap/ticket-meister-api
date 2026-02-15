from enum import Enum


class Priorities(int, Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    HIGHEST = 4

class RequestType(int, Enum):
    hardware_repairs_and_configuration = 0
    network_or_internet_services = 1
    data_services = 2
    system_services = 3
    request_for_system_development = 4
    others = 5