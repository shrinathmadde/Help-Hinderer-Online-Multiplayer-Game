from enum import Enum


class Direction(Enum):
    TOP = 0
    RIGHT = 1
    BOTTOM = 2
    LEFT = 3

if __name__ == "__main__":
    print(Direction.TOP.name)
    print(Direction[Direction.TOP.name])
    print(Direction(0))
