"""
Network-based player input implementation
"""
from typing import Tuple, Dict, List, Optional
import logging
from backend.player_input import PlayerInput

logger = logging.getLogger(__name__)


class NetworkPlayerInput(PlayerInput):
    """PlayerInput implementation that receives input over network"""

    def __init__(self):
        """Initialize the network player input"""
        self.player_inputs = {0: (None, 0, None), 1: (None, 0, None)}
        self.key_states = [{}, {}]  # For handling key presses
        logger.info("Initialized NetworkPlayerInput")

    def initInput(self) -> List[int]:
        """Initialize the input system

        Returns:
            List[int]: Mock keyboard IDs for compatibility with the engine
        """
        logger.info("Initializing NetworkPlayerInput")
        return [0, 1, 2]  # Return mock keyboard IDs

    def assignKeyboards(self, player1_keyboard_id: int, player2_keyboard_id: int, control_keyboard_id: int) -> None:
        """Assign keyboard IDs to players (not needed for network input)

        Args:
            player1_keyboard_id: Keyboard ID for player 1
            player2_keyboard_id: Keyboard ID for player 2
            control_keyboard_id: Keyboard ID for control
        """
        # Not needed for network input, but implement for compatibility
        pass

    def getInputOfPlayer(self, playerID: int) -> Tuple[Optional[str], int, Optional[str]]:
        """Get the current input for a player

        Args:
            playerID: Player's ID (0 or 1)

        Returns:
            Tuple[Optional[str], int, Optional[str]]: Direction, speed, and special action
        """
        result = self.player_inputs.get(playerID, (None, 0, None))
        # Reset input after it's been read
        self.player_inputs[playerID] = (None, 0, None)
        return result

    def set_player_input(self, player_id: int, direction: Optional[str], speed: int, special: Optional[str]) -> None:
        """Set input for a player from network event

        Args:
            player_id: Player ID (0 or 1)
            direction: Movement direction (UP, DOWN, LEFT, RIGHT)
            speed: Movement speed
            special: Special action (e.g., PLACE_BLOCK)
        """
        self.player_inputs[player_id] = (direction, speed, special)
        logger.debug(f"Set player {player_id} input: dir={direction}, speed={speed}, special={special}")

    def doExit(self) -> bool:
        """Check if the game should exit

        Returns:
            bool: Always False for web version
        """
        # Always return False for web version - we don't want to exit the server
        return False

    def checkForKey(self, key_name: str) -> bool:
        """Check if a key is currently pressed

        Args:
            key_name: Name of the key to check

        Returns:
            bool: True if key is pressed, False otherwise
        """
        # Check if the key is in any player's key_states
        for player_keys in self.key_states:
            if f"KEY_{key_name.upper()}" in player_keys:
                return True
        return False

    def key_down(self, player_id: int, key_name: str) -> None:
        """Register a key press for a player

        Args:
            player_id: Player ID (0 or 1)
            key_name: Name of the key being pressed
        """
        if player_id < len(self.key_states):
            self.key_states[player_id][f"KEY_{key_name.upper()}"] = True
            logger.debug(f"Player {player_id} key down: {key_name}")

    def key_up(self, player_id: int, key_name: str) -> None:
        """Register a key release for a player

        Args:
            player_id: Player ID (0 or 1)
            key_name: Name of the key being released
        """
        if player_id < len(self.key_states) and f"KEY_{key_name.upper()}" in self.key_states[player_id]:
            del self.key_states[player_id][f"KEY_{key_name.upper()}"]
            logger.debug(f"Player {player_id} key up: {key_name}")

    def cleanup(self) -> None:
        """Clean up resources"""
        # Nothing to clean up in network input
        pass