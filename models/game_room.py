"""
Game room model for managing players and game state
"""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class GameRoom:
    """Class representing a game room with players"""

    def __init__(self, room_code: str, max_players: int = 2):
        """Initialize a new game room

        Args:
            room_code: Unique identifier for the room
            max_players: Maximum number of players allowed (excluding moderator)
        """
        self.room_code = room_code
        self.players = {}  # player_id -> player_info
        self.max_players = max_players  # Real players (not including moderator)
        self.started = False
        self.active = True
        self.moderator_id = None  # Special ID for moderator (not a player)
        self.engine = None
        self.ui = None
        self.playerInput = None

        # Import NetworkSaver here to avoid circular import
        from networking.network_saver import NetworkSaver
        self.saver = NetworkSaver()

        logger.info(f"Created game room {room_code} with max {max_players} players")

    def add_player(self, player_id: str, username: str, is_moderator: bool = False) -> bool:
        """Add a player to the room

        Args:
            player_id: Unique identifier for the player
            username: Player's display name
            is_moderator: Whether this player is the room moderator

        Returns:
            bool: True if player was added successfully, False otherwise
        """
        logger.info(
            f"Adding {'moderator' if is_moderator else 'player'} {username} ({player_id}) to room {self.room_code}")

        if is_moderator:
            self.players[player_id] = {
                'username': username,
                'moderator': True,
                'ready': False
            }
            self.moderator_id = player_id
            logger.info(f"Set moderator ID to {player_id}")
            return True

        # Get only non-moderator players
        real_players = [pid for pid, pdata in self.players.items() if not pdata.get('moderator', False)]
        if len(real_players) >= self.max_players:
            logger.warning(f"Room {self.room_code} is full. Cannot add player {player_id}")
            return False

        player_number = len(real_players)
        self.players[player_id] = {
            'username': username,
            'player_number': player_number,
            'ready': False,
            'moderator': False  # explicitly set to false
        }
        logger.info(f"Added player {username} as player number {player_number}")
        return True

    def is_full(self) -> bool:
        """Check if the room has reached maximum capacity

        Returns:
            bool: True if room is full, False otherwise
        """
        real_players = [pid for pid, pdata in self.players.items() if not pdata.get('moderator', False)]
        return len(real_players) >= self.max_players

    def is_empty(self) -> bool:
        """Check if the room has no players

        Returns:
            bool: True if room is empty, False otherwise
        """
        return len(self.players) == 0

    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the room

        Args:
            player_id: ID of player to remove

        Returns:
            bool: True if player was removed, False if player was not found
        """
        if player_id in self.players:
            is_moderator = self.players[player_id].get('moderator', False)

            logger.info(f"Removing player {player_id} from room {self.room_code}")
            del self.players[player_id]

            # If moderator left, find a new moderator or mark room for cleanup
            if is_moderator and self.moderator_id == player_id:
                self.moderator_id = None
                # Try to promote another player to moderator
                for pid in self.players:
                    self.players[pid]['moderator'] = True
                    self.moderator_id = pid
                    logger.info(f"Promoted player {pid} to moderator")
                    break

            # If non-moderator left, reassign player numbers
            if not is_moderator:
                # Reassign player numbers to ensure 0 and 1 are used
                real_players = [pid for pid, pdata in self.players.items() if not pdata.get('moderator', False)]
                for idx, pid in enumerate(real_players):
                    self.players[pid]['player_number'] = idx

                logger.info(f"Reassigned player numbers after player {player_id} left")

            return True
        return False
    def start_game(self) -> bool:
        """Initialize and start the game

        Returns:
            bool: True if game started successfully, False otherwise
        """
        real_players = [pid for pid, pdata in self.players.items() if not pdata.get('moderator', False)]
        if len(real_players) < self.max_players:
            logger.warning(f"Cannot start game. Not enough players: {len(real_players)}/{self.max_players}")
            return False

        self.started = True

        # Import these here to avoid circular import
        from networking.network_input import NetworkPlayerInput
        from networking.network_ui import NetworkUI
        from backend.engine import EngineImpl
        from backend.block_provider import BlockProviderFromPremade
        from backend.trial_provider import TrialProviderFromPremade
        from assets.premade_trials.index import namedPremadeIndex
        from assets.premade_blocks.test_blocks import premade_test_blocks

        self.playerInput = NetworkPlayerInput()
        trialProvider = TrialProviderFromPremade(namedPremadeIndex["Practice"])
        blockProvider = BlockProviderFromPremade(premade_test_blocks)

        logger.info(f"Starting game in room {self.room_code}")
        self.engine = EngineImpl(
            blockProvider=blockProvider,
            playerInput=self.playerInput,
            saver=self.saver
        )

        self.ui = NetworkUI(self.engine, self.room_code)
        logger.info(f"Game successfully started in room {self.room_code}")
        return True

    def to_dict(self) -> dict:
        """Convert room data to a dictionary for JSON serialization

        Returns:
            dict: Room data as a dictionary
        """
        return {
            'room_code': self.room_code,
            'players': self.players,
            'max_players': self.max_players,
            'started': self.started
        }