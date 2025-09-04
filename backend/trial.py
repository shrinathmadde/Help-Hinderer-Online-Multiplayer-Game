import json
from dataclasses import dataclass, field

from backend.game_state import (
    GameState,
    GameStateJsonEncoder,
    decodeGameStateJsonString,
)
from backend.scoring import RewardCalculator, rewardCalculatorFromJsonString

from enum import Enum, auto


class TrialType(Enum):
    """
    Enum to define different types of trials
    A trial can be Practice or Competitive,
    and independently can have scoring enabled or disabled
    """

    hinder = auto()
    help = auto()
    rand = auto()

class RewardStrategy(Enum):
    WINNER_TAKES_ALL = 1
    SPLIT_IF_WIN = 2


@dataclass
class Trial:
    initialGameState: GameState
    rewardCalculator: RewardCalculator | None = None
    trialDescriptor: str = "trial"
    maxTurns: int | None = None
    maxTurnTime: float | None = None
    maxTotalTime: float | None = None
    rewardStrategy: RewardStrategy = RewardStrategy.WINNER_TAKES_ALL
    decayReward: bool = False  # Whether to decrease reward after this trial
    rewardDecayAmount: float = 0.1  # How much to decrease (e.g. 0.1)
    trialType: TrialType = TrialType.hinder
    countScores : bool = True

    def __post_init__(self):
        if not self.trialDescriptor.isalnum():
            raise ValueError("trial descriptor can only be alphanumeric")


class TrialJsonEncoder(json.JSONEncoder):
    def default(self, trial: Trial) -> dict:
        return {
            "initialGameState": json.dumps(
                trial.initialGameState, cls=GameStateJsonEncoder
            ),
            "rewardCalculator": (
                trial.rewardCalculator.toJsonString()
                if trial.rewardCalculator is not None
                else None
            ),
            "trialDescriptor": trial.trialDescriptor,
            "maxTurns": trial.maxTurns,
            "maxTurnTime": trial.maxTurnTime,
            "maxTotalTime": trial.maxTotalTime,
        }


def trialToJsonString(trial: Trial) -> str:
    return json.dumps(trial, cls=TrialJsonEncoder)
    pass


def trialFromJsonString(trialJsonString: str) -> Trial:
    trialDict: dict = json.loads(trialJsonString)
    return Trial(
        initialGameState=decodeGameStateJsonString(trialDict["initialGameState"]),
        rewardCalculator=rewardCalculatorFromJsonString(trialDict["rewardCalculator"]),
        trialDescriptor=trialDict["trialDescriptor"],
        maxTurns=trialDict["maxTurns"],
        maxTurnTime=trialDict["maxTurnTime"],
        maxTotalTime=trialDict["maxTotalTime"],
    )
    pass


# if __name__ == "__main__":
#     from assets.premade_trials.index import namedPremadeIndex
#     from backend.trial_provider import TrialProvider, TrialProviderFromPremade
#
#     trialProvider: TrialProvider = TrialProviderFromPremade(namedPremadeIndex["test"])
#     t: Trial = trialProvider.getNextTrial()
#     print(t.initialGameState)
#     print(type(t))
#     print(trialToJsonString(t))
#     trialDict: dict = json.loads(trialToJsonString(t))
#     decodeGameStateJsonString(trialDict["initialGameState"])
#     rewardCalculatorFromJsonString(trialDict["rewardCalculator"])
#     print(
#         trialToJsonString(trialFromJsonString(trialToJsonString(t)))
#         == trialToJsonString(t)
#     )
#     print("here")
#     print(t)
#     print("here2")
#     print(trialFromJsonString(trialToJsonString(t)))
#     exit()
