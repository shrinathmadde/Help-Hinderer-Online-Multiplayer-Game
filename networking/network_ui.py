"""
Network-based UI implementation
"""
import logging
from typing import Any, Dict, List, Tuple, Optional
from backend.engine_state import EngineState
from backend.engine import TrialResult

# This will be set by the main application
socketio = None

logger = logging.getLogger(__name__)


class NetworkUI:
    """UI implementation that sends game state over network"""

    def __init__(self, engine, room_code: str):
        """Initialize the network UI

        Args:
            engine: Game engine instance
            room_code: Room code for Socket.IO communication
        """
        self._engine = engine
        self.room_code = room_code
        self._lastEngineState = None
        logger.info(f"NetworkUI initialized for room {room_code}")

    def flip(self) -> None:
        """Update the UI (send game state to clients)"""
        try:
            current_state = self._engine.getEngineState()

            # Only send updates when state changes or for gameplay states
            if current_state != self._lastEngineState or current_state in [
                EngineState.P0TURN, EngineState.P1TURN, EngineState.WAITSTART,
                EngineState.LOADTRIALUI, EngineState.RESULT
            ]:
                # Prepare game data for network transmission
                try:
                    # Get field size (default to 8x8 if not available)
                    field_size = self._engine.getFieldSize() if hasattr(self._engine, 'getFieldSize') else (8, 8)

                    game_data = {
                        'engine_state': str(current_state),
                        'field_size': field_size,
                        'p0_position': self._engine.getPlayerPosition(0) if hasattr(self._engine,
                                                                                    'getPlayerPosition') else (0, 0),
                        'p1_position': self._engine.getPlayerPosition(1) if hasattr(self._engine,
                                                                                    'getPlayerPosition') else (7, 7),
                        'target_position': self._engine.getTargetPosition() if hasattr(self._engine,
                                                                                       'getTargetPosition') else (4, 4),
                        'wall_locations': self._engine.getWallPositions() if hasattr(self._engine,
                                                                                     'getWallPositions') else [],
                        'disabled_blocks': self._engine.getDisabledBlocks() if hasattr(self._engine,
                                                                                       'getDisabledBlocks') else [],
                        'movable_boxes_positions': self._engine.getBoxPositions() if hasattr(self._engine,
                                                                                             'getBoxPositions') else [],
                        'player_placed_blocks': self._engine.getPlayerPlacedBlocks() if hasattr(self._engine,
                                                                                                'getPlayerPlacedBlocks') else {},
                        'player_turn': self._engine._gameState.playerTurn if hasattr(self._engine,
                                                                                     '_gameState') and hasattr(
                            self._engine._gameState, 'playerTurn') else 0,
                        'scores': self._engine.getScores() if hasattr(self._engine, 'getScores') else [0, 0]
                    }

                    # Add can enter target info if available
                    if hasattr(self._engine, '_gameState') and hasattr(self._engine._gameState, 'canEnterTarget'):
                        game_data['canEnterTarget'] = self._engine._gameState.canEnterTarget

                    # Convert tuples to lists for JSON serialization
                    for key, value in game_data.items():
                        if isinstance(value, tuple):
                            game_data[key] = list(value)
                        elif isinstance(value, list) and value and isinstance(value[0], tuple):
                            game_data[key] = [list(item) if isinstance(item, tuple) else item for item in value]

                    # Handle player_placed_blocks dict with tuple keys
                    if isinstance(game_data['player_placed_blocks'], dict):
                        new_dict = {}
                        for k, v in game_data['player_placed_blocks'].items():
                            if isinstance(k, tuple):
                                new_dict[str(k)] = v
                            else:
                                new_dict[k] = v
                        game_data['player_placed_blocks'] = new_dict

                    # Log game state changes
                    if current_state != self._lastEngineState:
                        logger.info(
                            f"Game state changed in room {self.room_code}: {self._lastEngineState} -> {current_state}")

                    # Send update to clients
                    if socketio:
                        socketio.emit('game_update', game_data, to=self.room_code)
                        logger.debug(f"Sent game update to room {self.room_code}")
                    else:
                        logger.error(f"Cannot send game update: socketio not set")

                    # Handle specific state transitions
                    if current_state == EngineState.RESULT and self._lastEngineState != EngineState.RESULT:
                        # Send trial result when entering RESULT state
                        result = self._engine.getLastTrialResult() if hasattr(self._engine,
                                                                              'getLastTrialResult') else None
                        winner = None

                        if result == TrialResult.P0SCORED:
                            winner = 0
                        elif result == TrialResult.P1SCORED:
                            winner = 1

                        logger.info(f"Player {winner} scored in room {self.room_code}, result: {result}")

                        if socketio:
                            socketio.emit('player_scored', {
                                'player_number': winner if winner is not None else -1,
                                'result': str(result) if result else "NO_RESULT",
                                'scores': self._engine.getScores() if hasattr(self._engine, 'getScores') else [0, 0]
                            }, to=self.room_code)
                        else:
                            logger.error(f"Cannot send player_scored event: socketio not set")

                    # Update last state
                    self._lastEngineState = current_state

                except Exception as e:
                    logger.exception(f"Error preparing game data in NetworkUI.flip(): {e}")

            else:
                # No need to send an update
                pass

        except Exception as e:
            logger.exception(f"Error in NetworkUI.flip(): {e}")
            # Don't update last state on error to try again next frame

    # Add other UI methods as needed