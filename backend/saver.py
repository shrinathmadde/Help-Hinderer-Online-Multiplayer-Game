from os import mkdir
import os.path as p

from datetime import datetime

from io import TextIOWrapper
from abc import ABC, abstractmethod
import json

from conf.conf_current_dyad import dyadN
import conf.conf_data as conf_data

from backend.block import Block
from backend.block_provider import BlockProvider
from backend.game_state import GameState, GameStateJsonEncoder
from backend.engine_state import EngineState
from backend.trial import Trial, TrialJsonEncoder


def generateRecordingDir() -> str:
    runN: int = 0
    if p.exists(p.join(conf_data.recordings_dir, str(dyadN))):
        while p.exists(p.join(conf_data.recordings_dir, str(dyadN), str(runN))):
            runN += 1
    else:
        mkdir(p.join(conf_data.recordings_dir, str(dyadN)))
    mkdir(p.join(conf_data.recordings_dir, str(dyadN), str(runN)))
    if not p.exists(p.join(conf_data.recordings_dir, str(dyadN), str(runN))):
        raise OSError(
            f"dir {p.join(conf_data.recordings_dir, str(dyadN), str(runN))} not created"
        )
    return p.join(conf_data.recordings_dir, str(dyadN), str(runN))


# TODO: all saving with frameN?
# TODO: function params must include trial and block info?
class Saver(ABC):

    @abstractmethod
    def saveConf(self):
        pass

    @abstractmethod
    def saveBlockProvider(self, frameN: int, blocProvider: BlockProvider):
        pass

    @abstractmethod
    def saveBlock(self, frameN: int, block: Block):
        pass

    @abstractmethod
    def saveTrial(self, frameN: int, trial: Trial):
        pass

    @abstractmethod
    def saveGrids(
        self,
        frameN: int,
        blockDescriptor: str,
        trialDescriptor: str,
        gridCoordinates: list[dict[tuple[int, int], tuple[int, int]]],
    ):
        pass

    @abstractmethod
    def saveTick(self, frameN: int, time: datetime, state: EngineState):
        pass

    @abstractmethod
    def saveFlip(self, frameN: int, time: datetime, trigger: int):
        pass

    @abstractmethod
    def saveEvent(
        self,
        frameN: int,
        blockDescriptor: str,
        trialDescriptor: str,
        gameState: GameState,
        event: str,
    ):
        pass

    @abstractmethod
    def saveGameState(
        self,
        frameN: int,
        blockDescriptor: str,
        trialDescriptor: str,
        gameState: GameState,
    ):
        pass


class AppendFileSaver(Saver):
    _recordingDir: str
    _file = TextIOWrapper
    _blocksFile = TextIOWrapper
    _trialsFile = TextIOWrapper
    _tickFile = TextIOWrapper
    _flipFile = TextIOWrapper
    _gameStateFile = TextIOWrapper

    def __init__(self):
        self._recordingDir = generateRecordingDir()
        self._blocksFile = open(
            p.join(self._recordingDir, conf_data.append_saver_blockFilename),
            "a",
            buffering=1,
        )
        self._trialsFile = open(
            p.join(self._recordingDir, conf_data.append_saver_trialFilename),
            "a",
            buffering=1,
        )
        self._tickFile = open(
            p.join(self._recordingDir, conf_data.append_saver_tickFilename),
            "a",
            buffering=1,
        )
        self._flipFile = open(
            p.join(self._recordingDir, conf_data.append_saver_flipFilename),
            "a",
            buffering=1,
        )
        self._gameStateFile = open(
            p.join(self._recordingDir, conf_data.append_saver_gameStateFilename),
            "a",
            buffering=1,
        )

    def saveConf(self):
        pass

    def saveBlockProvider(self, frameN: int, blocProvider: BlockProvider):
        with open(
            p.join(self._recordingDir, conf_data.append_saver_blockProviderFilename),
            "w",
        ) as f:
            f.write(f"{frameN}\n{blocProvider.toJsonString()}\n")

    def saveBlock(self, frameN: int, block: Block):
        self._blocksFile.write(f"{frameN} {datetime.now().time()}\n")
        self._blocksFile.write(f"{block.toJsonString()}\n\n")

    def saveTrial(self, frameN: int, trial: Trial):
        self._trialsFile.write(f"{frameN} {datetime.now().time()}\n")
        self._trialsFile.write(f"{json.dumps(trial, cls=TrialJsonEncoder)}\n\n")

    def saveGrids(
        self,
        frameN: int,
        blockDescriptor: str,
        trialDescriptor: str,
        gridCoordinates: list[dict[tuple[int, int], tuple[int, int]]],
    ):
        pass

    def saveTick(self, frameN: int, time: datetime, state: EngineState):
        self._tickFile.write(f"{frameN}, {str(time.time())}, {state.name}\n")
        pass

    def saveFlip(self, frameN: int, time: datetime, trigger: int):
        self._flipFile.write(f"{frameN}, {str(time.time())}, {trigger}\n")
        pass

    def saveEvent(
        self,
        frameN: int,
        blockDescriptor: str,
        trialDescriptor: str,
        gameState: GameState,
        event: str,
    ):
        pass

    def saveGameState(
        self,
        frameN: int,
        blockDescriptor: str,
        trialDescriptor: str,
        gameState: GameState,
    ):
        self._gameStateFile.write(f"{frameN}, {blockDescriptor}, {trialDescriptor}\n")
        self._gameStateFile.write(
            f"{json.dumps(gameState, cls=GameStateJsonEncoder)}\n"
        )
        pass
