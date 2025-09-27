import json

from backend.scoring import RewardCalculator
from backend.trial import Trial
from backend.trial_provider import TrialProvider
from conf.conf_game import (
    DEFAULT_MAX_TURNS,
    DEFAULT_MAX_TURN_TIME,
    DEFAULT_MAX_TOTAL_TIME,
)

_DEFAULT_MAX_TURNS: int = DEFAULT_MAX_TURNS
_DEFAULT_MAX_TURN_TIME: float = DEFAULT_MAX_TURN_TIME
_DEFAULT_MAX_TOTAL_TIME: float = DEFAULT_MAX_TOTAL_TIME


# TODO: fromJson
class Block:
    blockDescriptor: str
    trialProvider: TrialProvider
    rewardCalculator: RewardCalculator
    instructions: list[str] = []  # TODO: some other type?
    currentTrial: Trial = None
    maxTurns: int
    maxTurnTime: float
    maxTotalTime: float

    def __init__(
        self,
        blockDescriptor: str,
        instructions: list[str],
        trialProvider: TrialProvider,
        rewardCalculator: RewardCalculator,
        maxTurns: int = _DEFAULT_MAX_TURNS,
        maxTurnTime: float = _DEFAULT_MAX_TURN_TIME,
        maxTotalTime: float = _DEFAULT_MAX_TOTAL_TIME,
    ):
        if not blockDescriptor.isalnum():
            raise ValueError("block descriptor can only be alphanumeric")
        self.blockDescriptor = blockDescriptor
        self.instructions = instructions
        self.trialProvider = trialProvider
        self.rewardCalculator = rewardCalculator
        self.maxTurns = maxTurns
        self.maxTurnTime = maxTurnTime
        self.maxTotalTime = maxTotalTime

    def getNextTrial(self):
        self.currentTrial = self.trialProvider.getNextTrial()
        return self.currentTrial

    def getCurrentRewardValues(self, turnsPassed: int, timePassed: str):
        if self.currentTrial is None:
            raise ValueError("No current trial")
        if self.currentTrial.rewardCalculator is not None:
            return self.currentTrial.rewardCalculator.calculateReward(
                turnsPassed, timePassed
            )
        return self.rewardCalculator.calculateReward(turnsPassed, timePassed)

    def getMaxTurns(self):
        if self.currentTrial is None:
            raise ValueError("No current trial")
        if self.currentTrial.maxTurns is not None:
            return self.currentTrial.maxTurns
        return self.maxTurns

    def getMaxTurnTime(self):
        if self.currentTrial is None:
            raise ValueError("No current trial")
        if self.currentTrial.maxTurnTime is not None:
            return self.currentTrial.maxTurnTime
        return self.maxTurnTime

    def getMaxTotalTime(self):
        if self.currentTrial is None:
            raise ValueError("No current trial")
        if self.currentTrial.maxTotalTime is not None:
            return self.currentTrial.maxTotalTime
        return self.maxTotalTime

    def toJsonString(self):
        return json.dumps(self, cls=BlockJsonEncoder)


class BlockJsonEncoder(json.JSONEncoder):
    def default(self, block: Block) -> dict:
        return {
            "blockDescriptor": block.blockDescriptor,
            "instructions": block.instructions,
            "trialProvider": block.trialProvider.toJsonString(),
            "rewardCalculator": block.rewardCalculator.toJsonString(),
            "maxTurns": block.maxTurns,
            "maxTurnTime": block.maxTurnTime,
            "maxTotalTime": block.maxTotalTime,
        }
