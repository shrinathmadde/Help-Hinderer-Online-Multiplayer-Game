import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

import conf.conf_game as conf
from backend.move_check import MovementCheckResult, MovementResult
from backend.util import Direction

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# scoring in some class with event based (collection, maxturns/time) interface?
@dataclass
class GameState:
    fieldSize: tuple[int, int]
    targetPosition: tuple[int, int]
    p0Position: tuple[int, int]
    p1Position: tuple[int, int]
    movableBoxesPositions: list[tuple[int, int]]
    disabledBlocks: list[tuple[int, int]]
    wallLocations: list[tuple[int, int, Direction]]
    playerTurn: int
    canMoveBoxes: tuple[bool, bool]
    canEnterTarget: tuple[bool, bool]
    canPlaceBlocks: tuple[bool, bool] = (
        True,
        True,
    )  # Default to both players can place blocks
    playerPlacedBlocks: dict[tuple[int, int], int] = field(
        default_factory=dict
    )  # Empty dict by default
    initialReward: float = 1.0
    currentReward: float = 1.0
    decayReward: bool = False
    rewardDecayAmount: float = 0.0
    movesInCurrentTurn: int = (
        0  # Track how many moves current player has made in this turn
    )
    maxMovesPerTurn: int = 2  # Maximum number of moves allowed per turn

    # Optional: You might want this for resetting
    def resetMovesInTurn(self):
        self.movesInCurrentTurn = 0


def isValidGameState(gameState: GameState, starting: bool = True) -> bool:
    isValid: bool = True
    if (
        gameState.fieldSize[0] < conf.size_min_x
        or gameState.fieldSize[1] < conf.size_min_y
    ):
        logger.warning(f"fieldSize {gameState.fieldSize} too small")
        isValid = False
    if (
        gameState.fieldSize[0] > conf.size_max_x
        or gameState.fieldSize[1] > conf.size_max_y
    ):
        logger.warning(f"fieldSize {gameState.fieldSize} too large")
        isValid = False
    if isOutOfBounds(bounds=gameState.fieldSize, position=gameState.p0Position):
        logger.warning(
            f"p0Position {gameState.p0Position} out of bounds with fieldSize {gameState.fieldSize}"
        )
        isValid = False
    if isOutOfBounds(bounds=gameState.fieldSize, position=gameState.p1Position):
        logger.warning(
            f"p0Position {gameState.p1Position} out of bounds with fieldSize {gameState.fieldSize}"
        )
        isValid = False
    if isOutOfBounds(bounds=gameState.fieldSize, position=gameState.targetPosition):
        logger.warning(
            f"targetPosition {gameState.targetPosition} out of bounds with fieldSize {gameState.fieldSize}"
        )
        isValid = False
    if gameState.p0Position == gameState.p1Position:
        logger.warning(f"players cannot have same position")
        isValid = False
    if any(
        [isOutOfBounds(gameState.fieldSize, pos) for pos in gameState.disabledBlocks]
    ):
        logger.warning(f"disabled block not in bounds")
        isValid = False
    if any(
        [
            isOutOfBounds(gameState.fieldSize, (pos[0], pos[1]))
            for pos in gameState.wallLocations
        ]
    ):
        logger.warning(f"wall position not in bounds")
        isValid = False
    if hasDuplicatePositions(gameState, starting):
        logger.warning(f"two things cannot have same position")
        isValid = False
    return isValid


def isOutOfBounds(bounds: tuple[int, int], position: tuple[int, int]) -> bool:
    return (
        position[0] < 0
        or position[0] >= bounds[0]
        or position[1] < 0
        or position[1] >= bounds[1]
    )


def hasDuplicatePositions(gameState: GameState, starting: bool):
    posSet: set[tuple[int, int]] = {gameState.p0Position}
    if gameState.p1Position in posSet:
        logger.warning("players cannot have same positions")
        return True
    posSet.add(gameState.p1Position)
    if starting and gameState.targetPosition in posSet:
        logger.warning("target pos already full")
        return True
    posSet.add(gameState.targetPosition)
    for movBoxPos in gameState.movableBoxesPositions:
        if movBoxPos in posSet:
            logger.warning("movable box position already full")
            return True
        posSet.add(movBoxPos)
    for disabledBlockPos in gameState.disabledBlocks:
        if disabledBlockPos in posSet:
            logger.warning("disabled block position already full")
            return True


def isExistingAndEmptySquare(gameState: GameState, position: tuple[int, int]) -> bool:
    if isOutOfBounds(gameState.fieldSize, position):
        return False
    return not any(
        [
            position == gameState.p0Position or position == gameState.p1Position,
            position in gameState.disabledBlocks,
            position in gameState.movableBoxesPositions,
            position == gameState.targetPosition,
        ]
    )


def movementWouldCrossWall(
    gameState: GameState,
    currentPosition: tuple[int, int],
    positionToMoveTo: tuple[int, int],
    direction: Direction,
) -> bool:
    wouldCross: bool = False
    if (*currentPosition, direction) in gameState.wallLocations:
        wouldCross = True
    match direction:
        case Direction.TOP:
            if (
                *positionToMoveTo,
                Direction.BOTTOM,
            ) in gameState.wallLocations:
                wouldCross = True
        case Direction.RIGHT:
            if (*positionToMoveTo, Direction.LEFT) in gameState.wallLocations:
                wouldCross = True
        case Direction.BOTTOM:
            if (*positionToMoveTo, Direction.TOP) in gameState.wallLocations:
                wouldCross = True
        case Direction.LEFT:
            if (
                *positionToMoveTo,
                Direction.RIGHT,
            ) in gameState.wallLocations:
                wouldCross = True
    return wouldCross


def checkMovement(
    gameState: GameState, direction: Direction, speed: int
) -> MovementCheckResult:
    """does not care about speed atm

    shorter movement is performed if blocked after first free square"""
    if gameState.playerTurn:
        currentPosition: tuple[int, int] = gameState.p1Position
    else:
        currentPosition: tuple[int, int] = gameState.p0Position
    positionToMoveTo = (-1, -1)
    match direction:
        case Direction.TOP:
            positionToMoveTo = (currentPosition[0], currentPosition[1] - 1)
        case Direction.RIGHT:
            positionToMoveTo = (currentPosition[0] + 1, currentPosition[1])
        case Direction.BOTTOM:
            positionToMoveTo = (currentPosition[0], currentPosition[1] + 1)
        case Direction.LEFT:
            positionToMoveTo = (currentPosition[0] - 1, currentPosition[1])
    # out of bounds
    if isOutOfBounds(gameState.fieldSize, positionToMoveTo):
        return MovementCheckResult.OUTOFBOUNDS
    # other player
    if (
        positionToMoveTo == gameState.p0Position
        or positionToMoveTo == gameState.p1Position
    ):
        return MovementCheckResult.OTHERPLAYER
    # wall
    if movementWouldCrossWall(gameState, currentPosition, positionToMoveTo, direction):
        return MovementCheckResult.WALL
    # disabled square
    if positionToMoveTo in gameState.disabledBlocks:
        return MovementCheckResult.DISABLED

    # Check for player-placed blocks
    if (
        hasattr(gameState, "playerPlacedBlocks")
        and positionToMoveTo in gameState.playerPlacedBlocks
    ):
        blockPlacedBy = gameState.playerPlacedBlocks[positionToMoveTo]
        # If the block wasn't placed by the current player, it's an obstacle
        if blockPlacedBy != gameState.playerTurn:
            return MovementCheckResult.PLAYERBLOCK

    # block and cannot move
    if positionToMoveTo in gameState.movableBoxesPositions:
        if not gameState.canMoveBoxes[gameState.playerTurn]:
            return MovementCheckResult.BOXANDCANNOTMOVE
        boxPositionToMoveTo = (-1, -1)
        match direction:
            case Direction.TOP:
                boxPositionToMoveTo = (positionToMoveTo[0], positionToMoveTo[1] - 1)
            case Direction.RIGHT:
                boxPositionToMoveTo = (positionToMoveTo[0] + 1, positionToMoveTo[1])
            case Direction.BOTTOM:
                boxPositionToMoveTo = (positionToMoveTo[0], positionToMoveTo[1] + 1)
            case Direction.LEFT:
                boxPositionToMoveTo = (positionToMoveTo[0] - 1, positionToMoveTo[1])
        if not isExistingAndEmptySquare(gameState, boxPositionToMoveTo):
            return MovementCheckResult.BOXANDBOXBLOCKED
    # target and cannot enter
    if (
        positionToMoveTo == gameState.targetPosition
        and not gameState.canEnterTarget[gameState.playerTurn]
    ):
        return MovementCheckResult.TARGETANDCANNOTENTER
    return MovementCheckResult.VALID


def playerBlocked(gameState: GameState) -> bool:
    return not any(
        [
            checkMovement(gameState, Direction.LEFT, 1) == MovementCheckResult.VALID,
            checkMovement(gameState, Direction.TOP, 1) == MovementCheckResult.VALID,
            checkMovement(gameState, Direction.RIGHT, 1) == MovementCheckResult.VALID,
            checkMovement(gameState, Direction.BOTTOM, 1) == MovementCheckResult.VALID,
        ]
    )


def performMovement(
    gameState: GameState, direction: Direction, speed: int
) -> MovementResult:
    """assumes valid movement is possible!

    cannot jump over anything with speed > 1
    """
    if gameState.playerTurn:
        currentPosition: tuple[int, int] = gameState.p1Position
    else:
        currentPosition: tuple[int, int] = gameState.p0Position
    positionsOnPath: list[tuple[int, int]] = []
    for i in range(1, speed + 1, 1):
        match direction:
            case Direction.TOP:
                positionsOnPath.append((currentPosition[0], currentPosition[1] - i))
            case Direction.RIGHT:
                positionsOnPath.append((currentPosition[0] + i, currentPosition[1]))
            case Direction.BOTTOM:
                positionsOnPath.append((currentPosition[0], currentPosition[1] + i))
            case Direction.LEFT:
                positionsOnPath.append((currentPosition[0] - i, currentPosition[1]))
    # remove potential positions outside field
    while isOutOfBounds(gameState.fieldSize, positionsOnPath[-1]):
        positionsOnPath.pop(-1)
    # remove all positions after a wall block
    if len(positionsOnPath) > 1:
        for i in range(len(positionsOnPath) - 1):
            if movementWouldCrossWall(
                gameState, positionsOnPath[0], positionsOnPath[1], direction
            ):
                positionsOnPath = positionsOnPath[0 : i + 1]

    firstNonEmptyIndex: int = -1
    for i in range(len(positionsOnPath)):
        if not isExistingAndEmptySquare(gameState, positionsOnPath[i]):
            firstNonEmptyIndex = i
            break
    # all positions of path are empty, move to last position
    if firstNonEmptyIndex == -1:
        if gameState.playerTurn:
            gameState.p1Position = positionsOnPath[-1]
        else:
            gameState.p0Position = positionsOnPath[-1]
        return MovementResult.NORMAL
    # has to be box or target, otherwise movement would be invalid
    if firstNonEmptyIndex == 0:
        if positionsOnPath[0] == gameState.targetPosition:
            if gameState.playerTurn:
                gameState.p1Position = positionsOnPath[0]
            else:
                gameState.p0Position = positionsOnPath[0]
            return MovementResult.ENTEREDTARGET
        else:
            boxPositionToMoveTo = (-1, -1)
            match direction:
                case Direction.TOP:
                    boxPositionToMoveTo = (
                        positionsOnPath[0][0],
                        positionsOnPath[0][1] - 1,
                    )
                case Direction.RIGHT:
                    boxPositionToMoveTo = (
                        positionsOnPath[0][0] + 1,
                        positionsOnPath[0][1],
                    )
                case Direction.BOTTOM:
                    boxPositionToMoveTo = (
                        positionsOnPath[0][0],
                        positionsOnPath[0][1] + 1,
                    )
                case Direction.LEFT:
                    boxPositionToMoveTo = (
                        positionsOnPath[0][0] - 1,
                        positionsOnPath[0][1],
                    )
            if gameState.playerTurn:
                gameState.p1Position = positionsOnPath[0]
            else:
                gameState.p0Position = positionsOnPath[0]
            for i in range(len(gameState.movableBoxesPositions)):
                if gameState.movableBoxesPositions[i] == positionsOnPath[0]:
                    gameState.movableBoxesPositions[i] = boxPositionToMoveTo
            return MovementResult.MOVEDBOX
    # is first non-empty blocked
    if any(
        [
            positionsOnPath[firstNonEmptyIndex] == gameState.p0Position,
            positionsOnPath[firstNonEmptyIndex] == gameState.p1Position,
            positionsOnPath[firstNonEmptyIndex] in gameState.disabledBlocks,
            positionsOnPath[firstNonEmptyIndex] in gameState.movableBoxesPositions
            and not gameState.canMoveBoxes[gameState.playerTurn],
            positionsOnPath[firstNonEmptyIndex] == gameState.targetPosition
            and not gameState.canEnterTarget[gameState.playerTurn],
        ]
    ):
        if gameState.playerTurn:
            gameState.p1Position = positionsOnPath[firstNonEmptyIndex - 1]
        else:
            gameState.p0Position = positionsOnPath[firstNonEmptyIndex - 1]
        return MovementResult.SHORTENED
    if positionsOnPath[firstNonEmptyIndex] in gameState.movableBoxesPositions:
        boxPositionToMoveTo = (-1, -1)
        match direction:
            case Direction.TOP:
                boxPositionToMoveTo = (
                    positionsOnPath[firstNonEmptyIndex][0],
                    positionsOnPath[firstNonEmptyIndex][1] - 1,
                )
            case Direction.RIGHT:
                boxPositionToMoveTo = (
                    positionsOnPath[firstNonEmptyIndex][0] + 1,
                    positionsOnPath[firstNonEmptyIndex][1],
                )
            case Direction.BOTTOM:
                boxPositionToMoveTo = (
                    positionsOnPath[firstNonEmptyIndex][0],
                    positionsOnPath[firstNonEmptyIndex][1] + 1,
                )
            case Direction.LEFT:
                boxPositionToMoveTo = (
                    positionsOnPath[firstNonEmptyIndex][0] - 1,
                    positionsOnPath[firstNonEmptyIndex][1],
                )
        if not isExistingAndEmptySquare(gameState, boxPositionToMoveTo):
            if gameState.playerTurn:
                gameState.p1Position = positionsOnPath[firstNonEmptyIndex - 1]
            else:
                gameState.p0Position = positionsOnPath[firstNonEmptyIndex - 1]
            return MovementResult.SHORTENED
        if gameState.playerTurn:
            gameState.p1Position = positionsOnPath[firstNonEmptyIndex]
        else:
            gameState.p0Position = positionsOnPath[firstNonEmptyIndex]
        for i in range(len(gameState.movableBoxesPositions)):
            if (
                gameState.movableBoxesPositions[i]
                == positionsOnPath[firstNonEmptyIndex]
            ):
                gameState.movableBoxesPositions[i] = boxPositionToMoveTo
        return MovementResult.MOVEDBOX
    if positionsOnPath[firstNonEmptyIndex] == gameState.targetPosition:
        if gameState.playerTurn:
            gameState.p1Position = positionsOnPath[firstNonEmptyIndex]
        else:
            gameState.p0Position = positionsOnPath[firstNonEmptyIndex]
        return MovementResult.ENTEREDTARGET

    raise RuntimeError(
        f"some movement case not handled. gameState: {gameState}, direction: {direction}, speed: {speed}"
    )


gameStateCsvHeader = ", ".join(["fieldX", "fieldY", "p0X", "p0Y", "p1X", "p1Y"])


def gameStateToCsvString(gameState: GameState) -> str:
    return ", ".join(
        [
            str(gameState.fieldSize[0]),
            str(gameState.fieldSize[1]),
            str(gameState.p0Position[0]),
            str(gameState.p0Position[1]),
            str(gameState.p1Position[0]),
            str(gameState.p1Position[1]),
            str(gameState.targetPosition[0]),
            str(gameState.targetPosition[1]),
        ]
    )


def _wallLocationToSerializable(
    wallLocation: list[tuple[int, int, Direction]]
) -> list[tuple[int, int, str]]:
    return list(map(lambda x: (x[0], x[1], x[2].name), wallLocation))


class GameStateJsonEncoder(json.JSONEncoder):
    def default(self, gameState: GameState) -> dict:
        return {
            "fieldSize": gameState.fieldSize,
            "targetPosition": gameState.targetPosition,
            "p0Position": gameState.p0Position,
            "p1Position": gameState.p1Position,
            "movableBoxesPositions": gameState.movableBoxesPositions,
            "disabledBlocks": gameState.disabledBlocks,
            "wallLocations": _wallLocationToSerializable(gameState.wallLocations),
            "playerTurn": gameState.playerTurn,
            "canMoveBoxes": gameState.canMoveBoxes,
            "canEnterTarget": gameState.canEnterTarget,
        }


def _wallSerializableToState(
    wallLocation: list[tuple[int, int, str]]
) -> list[tuple[int, int, Direction]]:
    return list(map(lambda x: (x[0], x[1], Direction[x[2]]), wallLocation))


def gameStateToJsonString(gameState: GameState) -> str:
    return json.dumps(gameState, cls=GameStateJsonEncoder)


def decodeGameStateJsonString(jsonString: str) -> GameState:
    gameStateDict: dict = json.loads(jsonString)
    return GameState(
        fieldSize=gameStateDict["fieldSize"],
        targetPosition=gameStateDict["targetPosition"],
        p0Position=gameStateDict["p0Position"],
        p1Position=gameStateDict["p1Position"],
        movableBoxesPositions=gameStateDict["movableBoxesPositions"],
        disabledBlocks=gameStateDict["disabledBlocks"],
        wallLocations=_wallSerializableToState(gameStateDict["wallLocations"]),
        playerTurn=gameStateDict["playerTurn"],
        canMoveBoxes=gameStateDict["canMoveBoxes"],
        canEnterTarget=gameStateDict["canEnterTarget"],
    )


if __name__ == "__main__":
    from assets.premade_trials.test_trials import premadeTestTrials

    str1: str = json.dumps(
        premadeTestTrials[0].initialGameState, cls=GameStateJsonEncoder
    )
    str2: str = json.dumps(decodeGameStateJsonString(str1), cls=GameStateJsonEncoder)
    print(str1 == str2)
    print(str1)
