"""
Network-based game state saver implementation
"""
from datetime import datetime
import logging
from backend.saver import Saver

logger = logging.getLogger(__name__)


class NetworkSaver(Saver):
    """Saver implementation that stores data in memory for web access"""

    def __init__(self):
        """Initialize the network saver"""
        self.data = []
        self.grids = []
        self.block_provider = None
        self.current_block = None
        self.current_trial = None
        self.game_states = []
        self.flips = []
        self.trial_results = []
        logger.info("Initialized NetworkSaver")

    def saveBlockProvider(self, tick: int, blockProvider) -> None:
        """Save block provider state

        Args:
            tick: Current game tick
            blockProvider: The block provider instance
        """
        self.block_provider = {"tick": tick, "time": datetime.now().isoformat()}
        logger.debug(f"Saved block provider at tick {tick}")

    def saveBlock(self, tick: int, block) -> None:
        """Save block state

        Args:
            tick: Current game tick
            block: The block instance
        """
        self.current_block = {
            "tick": tick,
            "time": datetime.now().isoformat(),
            "descriptor": block.blockDescriptor if hasattr(block, "blockDescriptor") else "Unknown"
        }
        logger.debug(f"Saved block at tick {tick}: {getattr(block, 'blockDescriptor', 'Unknown')}")

    def saveTrial(self, tick: int, trial) -> None:
        """Save trial state

        Args:
            tick: Current game tick
            trial: The trial instance
        """
        self.current_trial = {
            "tick": tick,
            "time": datetime.now().isoformat(),
            "descriptor": trial.trialDescriptor if hasattr(trial, "trialDescriptor") else "Unknown"
        }
        logger.debug(f"Saved trial at tick {tick}: {getattr(trial, 'trialDescriptor', 'Unknown')}")

    def saveTick(self, tick: int, time: datetime, state) -> None:
        """Save tick state

        Args:
            tick: Current game tick
            time: Current time
            state: Game state at this tick
        """
        self.data.append({"tick": tick, "time": time.isoformat(), "state": str(state)})
        logger.debug(f"Saved tick {tick}, state: {state}")

    def saveGrids(self, tick: int, blockDescriptor: str, trialDescriptor: str, gridCoordinates) -> None:
        """Save grid coordinates

        Args:
            tick: Current game tick
            blockDescriptor: Block descriptor
            trialDescriptor: Trial descriptor
            gridCoordinates: Grid coordinates
        """
        self.grids.append({
            "tick": tick,
            "time": datetime.now().isoformat(),
            "block": blockDescriptor,
            "trial": trialDescriptor
        })
        logger.debug(f"Saved grids at tick {tick}")

    def saveGameState(self, tick: int, blockDescriptor: str, trialDescriptor: str, gameState) -> None:
        """Save game state

        Args:
            tick: Current game tick
            blockDescriptor: Block descriptor
            trialDescriptor: Trial descriptor
            gameState: Game state object
        """
        # Convert GameState to serializable format
        state_dict = {}
        for attr in dir(gameState):
            if not attr.startswith('__') and not callable(getattr(gameState, attr)):
                value = getattr(gameState, attr)
                # Handle tuple conversion for JSON serialization
                if isinstance(value, tuple):
                    value = list(value)
                # Handle dict with tuple keys
                elif isinstance(value, dict) and any(isinstance(k, tuple) for k in value.keys()):
                    new_dict = {}
                    for k, v in value.items():
                        if isinstance(k, tuple):
                            new_dict[str(k)] = v
                        else:
                            new_dict[k] = v
                    value = new_dict
                state_dict[attr] = value

        self.game_states.append({
            "tick": tick,
            "time": datetime.now().isoformat(),
            "block": blockDescriptor,
            "trial": trialDescriptor,
            "state": state_dict
        })
        logger.debug(f"Saved game state at tick {tick}")

    def saveFlip(self, tick: int, time: datetime, trigger: str) -> None:
        """Save UI flip event

        Args:
            tick: Current game tick
            time: Current time
            trigger: What triggered the flip
        """
        self.flips.append({"tick": tick, "time": time.isoformat(), "trigger": trigger})
        logger.debug(f"Saved flip at tick {tick}, trigger: {trigger}")

    def saveTrialResult(self, tick: int, blockDescriptor: str, trialDescriptor: str,
                        result, totalTime: float, inputs) -> None:
        """Save trial result

        Args:
            tick: Current game tick
            blockDescriptor: Block descriptor
            trialDescriptor: Trial descriptor
            result: Trial result
            totalTime: Total time elapsed
            inputs: Player inputs
        """
        self.trial_results.append({
            "tick": tick,
            "time": datetime.now().isoformat(),
            "block": blockDescriptor,
            "trial": trialDescriptor,
            "result": str(result),
            "totalTime": totalTime,
            "inputs": inputs
        })
        logger.debug(f"Saved trial result at tick {tick}: {result}")

    def saveConf(self, tick: int, conf_data) -> None:
        """Save configuration data

        Args:
            tick: Current game tick
            conf_data: Configuration data
        """
        self.data.append({
            "tick": tick,
            "time": datetime.now().isoformat(),
            "type": "conf",
            "data": conf_data
        })
        logger.debug(f"Saved configuration at tick {tick}")

    def saveEvent(self, tick: int, event_type: str, event_data) -> None:
        """Save event data

        Args:
            tick: Current game tick
            event_type: Type of event
            event_data: Event data
        """
        self.data.append({
            "tick": tick,
            "time": datetime.now().isoformat(),
            "type": "event",
            "event_type": event_type,
            "data": event_data
        })
        logger.debug(f"Saved event at tick {tick}: {event_type}")