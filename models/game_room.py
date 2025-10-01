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

        # --- NEW: game config snapshot on room creation ---
        # We read the game config immediately and store:
        #   - self.trials: full list of trials
        #   - self.current_trial_index: index of the active trial (starts at 0)
        self.trials: List[dict] = []
        self.current_trial_index: int = 0
        try:
            # Import here to avoid unexpected import cycles
            from conf import game_config  # contains GAME_CONFIG
            cfg = getattr(game_config, "GAME_CONFIG", {}) or {}
            trials = cfg.get("trials", [])
            # Make a shallow copy so room has its own snapshot
            self.trials = list(trials) if isinstance(trials, list) else []
            self.current_trial_index = 0
            # logger.info(
            #     f"[{self.room_code}] Loaded game config: {len(self.trials)} trials; current_trial_index set to 0"
            # )
        except Exception as e:
            logger.exception(f"[{self.room_code}] Failed to load GAME_CONFIG trials: {e}")
            # leave trials empty and index 0; game_service can still populate later if needed

        # logger.info(f"Created game room {room_code} with max {max_players} players")
    
    def update_player_position(self, player_id: str, dx: int, dy: int) -> bool:
        """
        Update a player's position in the current trial and toggle turn.

        Args:
            player_id: ID of the player moving
            dx: delta x
            dy: delta y

        Returns:
            bool: True if update succeeded, False otherwise
        """
        try:
            current_trial_index = int(self.current_trial_index or 0)
        except Exception:
            current_trial_index = 0

        if not self.trials or not (0 <= current_trial_index < len(self.trials)):
            logger.warning(f"[{self.room_code}] update_player_position: No active trial")
            return False

        trial = self.trials[current_trial_index]

        # Determine role (R or B) based on player_number
        player_info = self.players.get(player_id)
        if not player_info:
            logger.warning(f"[{self.room_code}] update_player_position: Player not found {player_id}")
            return False

        role = "R" if player_info.get("player_number") == 0 else "B"

        old_pos = trial.get("start_positions", {}).get(role)
        if not old_pos:
            logger.warning(f"[{self.room_code}] update_player_position: No old pos for {role}")
            return False

        # Compute new position
        new_pos = [old_pos[0] + dx, old_pos[1] + dy]
        trial["start_positions"][role] = new_pos

        logger.info(f"[{self.room_code}] Player {player_id} ({role}) moved {dx},{dy} → {new_pos}")

        # Toggle turn
        trial["turn"] = "B" if trial.get("turn") == "R" else "R"

        return True
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
            f"Adding {'moderator' if is_moderator else 'player'} {username} ({player_id}) to room {self.room_code}"
        )

        if is_moderator:
            self.players[player_id] = {
                "username": username,
                "moderator": True,
                "ready": False,
                "role": None,  # moderators don’t get a role
            }
            self.moderator_id = player_id
            logger.info(f"Set moderator ID to {player_id}")
            return True

        # Get only non-moderator players
        real_players = [pid for pid, pdata in self.players.items() if not pdata.get("moderator", False)]
        if len(real_players) >= self.max_players:
            logger.warning(f"Room {self.room_code} is full. Cannot add player {player_id}")
            return False

        player_number = len(real_players)

        # Assign role based on join order
        role = "R" if player_number == 0 else "B"

        self.players[player_id] = {
            "username": username,
            "player_number": player_number,
            "ready": False,
            "moderator": False,  # explicitly set to false
            "role": role,
        }

        logger.info(f"Added player {username} as player number {player_number} with role {role}")
        return True


    def is_full(self) -> bool:
        """Check if the room has reached maximum capacity"""
        real_players = [pid for pid, pdata in self.players.items() if not pdata.get('moderator', False)]
        return len(real_players) >= self.max_players

    def is_empty(self) -> bool:
        """Check if the room has no players"""
        return len(self.players) == 0

    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the room"""
        if player_id in self.players:
            is_moderator = self.players[player_id].get('moderator', False)

            logger.info(f"Removing player {player_id} from room {self.room_code}")
            del self.players[player_id]

            if is_moderator and self.moderator_id == player_id:
                self.moderator_id = None
                # Try to promote another player to moderator
                for pid in self.players:
                    self.players[pid]['moderator'] = True
                    self.moderator_id = pid
                    logger.info(f"Promoted player {pid} to moderator")
                    break

            if not is_moderator:
                # Reassign player numbers to ensure 0 and 1 are used
                real_players = [pid for pid, pdata in self.players.items() if not pdata.get('moderator', False)]
                for idx, pid in enumerate(real_players):
                    self.players[pid]['player_number'] = idx

                logger.info(f"Reassigned player numbers after player {player_id} left")

            return True
        return False

    def start_game(self) -> bool:
        """Initialize and start the game.
        Returns True if started, False otherwise.
        """
        real_players = [pdata for pid, pdata in self.players.items() if not pdata.get("moderator", False)]

        # 1. Check if the expected number of players is present
        if len(real_players) < self.max_players:
            logger.warning(
                f"Cannot start game in room {self.room_code}. Not enough players: "
                f"{len(real_players)}/{self.max_players}"
            )
            return False

        # 2. Check readiness of all non-moderator players
        not_ready = [pdata["username"] for pdata in real_players if not pdata.get("ready", False)]
        if not_ready:
            logger.warning(
                f"Cannot start game in room {self.room_code}. Players not ready: {not_ready}"
            )
            return False

        # 3. All conditions met → start the game
        self.started = True
        logger.info(f"Game successfully started in room {self.room_code}")
        return True


    def to_dict(self) -> dict:
        """Convert room data to a dictionary for JSON serialization"""
        return {
            'room_code': self.room_code,
            'players': self.players,
            'max_players': self.max_players,
            'started': self.started,
            # --- NEW (optional to expose in debug/UI): ---
            'trials_count': len(self.trials),
            'current_trial_index': self.current_trial_index,
        }

    def to_meta(self) -> dict:
        """Serialize only room metadata (no engine/UI)."""
        return {
            "room_code": self.room_code,
            "players": self.players,
            "max_players": self.max_players,
            "started": self.started,
            "active": self.active,
            "moderator_id": self.moderator_id,
            # --- NEW: persist config snapshot & pointer ---
            "trials": self.trials,
            "current_trial_index": self.current_trial_index,
        }

    @staticmethod
    def from_meta(meta: dict) -> "GameRoom":
        """Rebuild a GameRoom (engine/ui will be None; attach later if present)."""
        room = GameRoom(meta["room_code"], meta.get("max_players", 2))
        room.players = meta.get("players", {})
        room.started = meta.get("started", False)
        room.active = meta.get("active", True)
        room.moderator_id = meta.get("moderator_id")

        # --- NEW: restore config snapshot & pointer ---
        room.trials = meta.get("trials", [])
        room.current_trial_index = int(meta.get("current_trial_index", 0))

        return room
