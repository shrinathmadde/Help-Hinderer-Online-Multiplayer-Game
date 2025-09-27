from enum import Enum


class MovementCheckResult(Enum):
    VALID = 0
    OUTOFBOUNDS = 10
    WALL = 11
    DISABLED = 12
    BOXANDCANNOTMOVE = 13
    BOXANDBOXBLOCKED = 14
    TARGETANDCANNOTENTER = 15
    OTHERPLAYER = 16
    PLAYERBLOCK = 17  # New result for player-placed blocks

class MovementResult(Enum):
    NORMAL = 0
    MOVEDBOX = 1
    ENTEREDTARGET = 2
    SHORTENED = 3

# TODO
def movementCheckResultToTrigger(res: MovementCheckResult) -> int:
    pass
