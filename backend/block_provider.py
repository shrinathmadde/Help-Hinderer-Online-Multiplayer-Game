from abc import ABC, abstractmethod
import json

from backend.block import Block, BlockJsonEncoder


class BlockProvider(ABC):
    @abstractmethod
    def getNextBlock(self) -> Block | None:
        pass

    @abstractmethod
    def toJsonString(self):
        pass


class BlockProviderFromPremade(BlockProvider):
    _blocks: list[Block]
    _currentBlock: int = 0

    def __init__(self, blocks: list[Block]):
        self._blocks = blocks

    def getNextBlock(self) -> Block | None:
        if self._currentBlock == len(self._blocks):
            return None
        self._currentBlock += 1
        return self._blocks[self._currentBlock - 1]

    def toJsonString(self) -> str:
        return json.dumps(
            json.dumps(
                {
                    "blockProviderType": "premade",
                    "blocks": list(
                        [
                            json.dumps(block, cls=BlockJsonEncoder)
                            for block in self._blocks
                        ]
                    ),
                }
            )
        )
