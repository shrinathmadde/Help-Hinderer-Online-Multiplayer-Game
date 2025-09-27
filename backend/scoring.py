from abc import ABC, abstractmethod
import json


class Scoring(ABC):
    @abstractmethod
    def addScore(self, blockDescriptor: str, trialDescriptor: str, score: tuple[float, float]) -> None:
        pass

    @abstractmethod
    def getBlockScores(self) -> dict[str, list[float]]:
        pass

    @abstractmethod
    def getTrialScores(self) -> dict[str, dict[str, list[float]]]:
        pass

    @abstractmethod
    def getTotalScores(self) -> tuple[float, float]:
        pass


class ScoringImpl(Scoring):
    _p0TotalScore: float = 0.0
    _p1TotalScore: float = 0.0
    _blockScores: dict[str, list[float]] = {}
    _trialScores: dict[str, dict[str, list[float]]] = {}  # block -> trial -> score

    def addScore(self, blockDescriptor: str, trialDescriptor: str, score: tuple[float, float]) -> None:
        self._p0TotalScore += score[0]
        self._p1TotalScore += score[1]
        if blockDescriptor not in self._blockScores:
            self._blockScores[blockDescriptor] = [*score]
        else:
            self._blockScores[blockDescriptor][0] += score[0]
            self._blockScores[blockDescriptor][1] += score[1]
        if blockDescriptor not in self._trialScores:
            self._trialScores[blockDescriptor] = {}
        if trialDescriptor not in self._trialScores[blockDescriptor]:
            self._trialScores[blockDescriptor][trialDescriptor] = [*score]
        else:
            self._trialScores[blockDescriptor][trialDescriptor][0] += score[0]
            self._trialScores[blockDescriptor][trialDescriptor][1] += score[1]

    def getBlockScores(self) -> dict[str, list[float]]:
        return self._blockScores

    def getTrialScores(self) -> dict[str, dict[str, list[float]]]:
        return self._trialScores

    def getTotalScores(self) -> tuple[float, float]:
        return self._p0TotalScore, self._p1TotalScore


# TODO: RewardCalculator should rely less on correct array indexing
# TODO: different methods for different results?
class RewardCalculator(ABC):
    def calculateReward(self, turnsPassed: int, timePassed: str) -> dict[int, tuple[float, float]]:
        """ keys: 0 for not-collected, 1 for collected """
        rewardValues: tuple[tuple[float, float], tuple[float, float]] = self._calculateRewardValues(turnsPassed,
                                                                                                    timePassed)
        return {0: rewardValues[0], 1: rewardValues[1]}

    @abstractmethod
    def _calculateRewardValues(self, turnsPassed: int, timePassed: str) -> tuple[
        tuple[float, float], tuple[float, float]]:
        pass

    @abstractmethod
    def toJsonString(self) -> str:
        pass


class ConstantRewardCalculator(RewardCalculator):
    _collector: int
    _reward: float

    def __init__(self, collector: int, reward: float):
        if collector != 0 and collector != 1:
            raise ValueError("Invalid collector")
        self._collector = collector
        self._reward = reward

    def _calculateRewardValues(self, turnsPassed: int, timePassed: str) -> tuple[tuple[float, float], tuple[float, float]]:
        if self._collector:
            return (self._reward, 0), (0, self._reward)
        else:
            return (0, self._reward), (self._reward, 0)

    def toJsonString(self) -> str:
        return json.dumps({"calculaterId": 0, "collector": self._collector, "reward": self._reward})


def rewardCalculatorFromJsonString(jsonString: str | None) -> RewardCalculator | None:
    if jsonString is None:
        return None
    if jsonString == "null":
        return None
    rewardJsonDict: dict = json.loads(jsonString)
    if rewardJsonDict["calculaterId"] == 0:
        return ConstantRewardCalculator(rewardJsonDict["collector"], rewardJsonDict["reward"])
    raise ValueError(f"Invalid calculatorId in json string {jsonString}")
