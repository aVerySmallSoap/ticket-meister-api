from enum import Enum

class Priorities(int, Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class RequestType(int, Enum):
    hardware_repairs_and_configuration = 0
    network_or_internet_services = 1
    data_services = 2
    system_services = 3
    request_for_system_development = 4
    others = 5
    equipment_repair_report = 6

class Status(int, Enum):
    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CLOSED = 3