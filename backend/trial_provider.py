from abc import ABC, abstractmethod
import json

from backend.game_state import GameState
from backend.trial import Trial, TrialJsonEncoder
from backend.scoring import ConstantRewardCalculator


class TrialProvider(ABC):

    @abstractmethod
    def getNextTrial(self) -> Trial | None:
        pass

    @abstractmethod
    def toJsonString(self):
        pass


class TrialProviderFromPremade(TrialProvider):
    _currentTrial: int = 0
    _trials: list[Trial]

    def __init__(self, trials: list[Trial]):
        self._trials = trials

    def getNextTrial(self) -> Trial | None:
        self._currentTrial += 1
        if self._currentTrial - 1 >= len(self._trials):
            return None
        if sum(self._trials[self._currentTrial - 1].initialGameState.canEnterTarget) != 1:
            raise ValueError("only one can be collector for this trial provider")
        if self._trials[self._currentTrial - 1].initialGameState.canEnterTarget[0]:
            collectingPlayer = 0
        else:
            collectingPlayer = 1
        return self._trials[self._currentTrial - 1]

        # return self._trials[self._currentTrial - 1]

    def toJsonString(self):
        return json.dumps({"trialProviderType": "premade",
                           "trials": list([json.dumps(trial, cls=TrialJsonEncoder) for trial in self._trials]),
                           })
