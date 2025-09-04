from datetime import datetime

from abc import ABC, abstractmethod
from collections.abc import Callable

from enum import Enum

import logging

from backend.clock import Clock
from backend.trial import RewardStrategy

from backend.block import Block
from backend.block_provider import BlockProvider
from backend.game_state import (
    GameState,
    isValidGameState,
    isOutOfBounds,
    checkMovement,
    playerBlocked,
    performMovement,
)
from backend.move_check import MovementCheckResult, MovementResult
from backend.saver import Saver
from backend.engine_state import EngineState, isEngineStateTransitionAllowed
from backend.trial import Trial
from backend.player_input import PlayerInput
from backend.util import Direction
from backend.scoring import Scoring, ScoringImpl

import os.path as p

import conf.conf_game as conf_game


logger = logging.getLogger(__name__)


# TODO split up RESULT state?
#   p0,p1Collected, Maxturns/time(, stuck?)
#   might make UI feedback easier to handle?
# TODO what to save
#   see Pad
#   save all inputs including invalid ones?
#   save every frame like in dyadic?
#       save some data
#       more predictable
#   save only on event?
#       less pointless data
# TODO measure frame time during load of trial
#   how does psychopy handle one frame being longer than surrounding ones?
#       pygame did some compensating to make average fps as constant as possible?
#       current model of waiting for drawing of players and targets for some frames might prevent something going wrong?
# TODO abstract game state changing (might be useful for central point for event sending)
#   can gameState only change during turns?
#       save event on exiting turn? (first entering is not during change but after WAITSTART)
#       turn handling should be more readable, atm just guardlike returns and random important events in middle of if forest
#           better:
#               check time/turns passed
#               check if input
#               check if actionable
#               act
#
class TrialResult(Enum):
    P0SCORED = 0
    P1SCORED = 1
    MAXTURNSREACHED = 2
    MAXTURNTIMEREACHED = 3
    MAXTOTALTIMEREACHED = 4
    PLAYERTRAPPED = 5
    ERROR = 10


class Engine(ABC):
    """main game controller

    call tick to progress game
    """

    @abstractmethod
    def getEngineState(self) -> EngineState:
        pass

    # In Engine abstract class (usually in engine.py)
    @abstractmethod
    def isActive(self) -> bool:
        pass

    @abstractmethod
    def getFieldSize(self) -> tuple[int, int]:
        pass

    @abstractmethod
    def getTargetPosition(self) -> tuple[int, int]:
        pass

    @abstractmethod
    def getPlayerPosition(self, pID: int) -> tuple[int, int]:
        pass

    @abstractmethod
    def getWallPositions(self) -> list[tuple[int, int, Direction]]:
        pass

    @abstractmethod
    def getDisabledBlocks(self) -> list[tuple[int, int]]:
        pass

    @abstractmethod
    def getBoxPositions(self) -> list[tuple[int, int]]:
        pass

    @abstractmethod
    def getScores(self) -> tuple[int, int]:
        pass

    @abstractmethod
    def getLastTrialResult(self) -> TrialResult:
        pass

    @abstractmethod
    def getTrigger(self) -> int:
        pass

    @abstractmethod
    def tick(self) -> None:
        pass

    @abstractmethod
    def saveFlip(self, time: datetime, trigger: int) -> None:
        pass

    @abstractmethod
    def saveGrids(
        self, gridCoordinates: list[dict[tuple[int, int], tuple[int, int]]]
    ) -> None:
        pass

    @abstractmethod
    def ended(self) -> bool:
        pass

    @abstractmethod
    def getPlayerPlacedBlocks(self) -> dict[tuple[int, int], int]:
        pass


class EngineImpl(Engine):
    _state: EngineState = EngineState.ENGINESTART
    _gameState: GameState
    _currentBlock: Block
    _blockProvider: BlockProvider
    _input: PlayerInput
    _maxTurns: int
    _tickCount: int = 0
    _saver: Saver
    _scoring: Scoring

    def __init__(
        self, blockProvider: BlockProvider, playerInput: PlayerInput, saver: Saver
    ):
        self._blockProvider = blockProvider
        self._input = playerInput
        self._input.initInput()
        self._saver = saver
        self._initStateHandlers()
        self._scoring = ScoringImpl()
        self._saver.saveBlockProvider(self._tickCount, self._blockProvider)
        self._enter_pressed = False

        # Initialize sounds
        self._initSounds()

    def _initSounds(self):
        """Initialize sound effects for game events"""
        try:
            # Use the singleton sound manager
            from backend.sound_manager import SoundManager

            self._sound_manager = SoundManager.get_instance()
            self._sound_manager.initialize_sounds()
            self._sound_enabled = True
        except Exception as e:
            print(f"Error initializing sounds: {str(e)}")
            self._sound_enabled = False

    def _playSound(self, sound_name):
        """Play a sound if sound is enabled"""
        if self._sound_enabled:
            try:
                self._sound_manager.play_sound(sound_name)
            except Exception as e:
                print(f"Error playing sound '{sound_name}': {str(e)}")

    # In Engine abstract class (usually in engine.py)
    # In EngineImpl class
    def isActive(self) -> bool:
        """Returns True if the engine is in an active state that should continue running"""
        active_states = [
            EngineState.ENGINESTART,
            EngineState.GETNEXTBLOCK,
            EngineState.BLOCKSTART,
            EngineState.BLOCKINSTRUCTIONS,
            EngineState.BLOCKEND,
            EngineState.TRIALNOTSTARTED,
            EngineState.WAITSTART,
            EngineState.P0TURN,
            EngineState.P1TURN,
            EngineState.LOADTRIALUI,
            EngineState.RESULT,
            EngineState.FINISHED,
            EngineState.PAUSED,
            EngineState.INVALIDGAMESTATE,
            EngineState.ENGINEEND,  # Important: Include ENGINEEND
        ]
        return self._state in active_states

    def getEngineState(self) -> EngineState:
        return self._state

    def getFieldSize(self) -> tuple[int, int]:
        return self._gameState.fieldSize

    def getPlayerPosition(self, pID: int) -> tuple[int, int]:
        if pID == 0:
            return self._gameState.p0Position
        else:
            return self._gameState.p1Position

    def getTargetPosition(self) -> tuple[int, int]:
        return self._gameState.targetPosition

    def getWallPositions(self) -> list[tuple[int, int, Direction]]:
        return self._gameState.wallLocations

    def getDisabledBlocks(self) -> list[tuple[int, int]]:
        return self._gameState.disabledBlocks

    def getBoxPositions(self) -> list[tuple[int, int]]:
        return self._gameState.movableBoxesPositions

    def getScores(self) -> tuple[int, int]:
        """Returns the current scores for both players (player0, player1)"""
        try:
            return self._scoring.getTotalScores()
        except Exception as e:
            print(f"Error getting scores: {str(e)}")
            return (0, 0)  # Return default scores on error

    def getLastTrialResult(self) -> TrialResult:
        return self._lastTrialResult

    def getTrigger(self) -> int:
        tempTrigger = self._trigger
        self._trigger = -1
        return tempTrigger

    _stateClock: Clock = Clock()
    _trialClock: Clock = Clock()
    _waited_for_frames: int = 0
    _current_turn: int = 0
    _lastTrialResult: TrialResult = TrialResult.ERROR
    _trigger: int = -1

    # TODO track last state to allow doing something on first frame of state -> only necessary for starting clocks
    def tick(self) -> None:
        # print(
        #     f'engine_tick: {self.__hash__()} - {datetime.now().isoformat(sep=" ", timespec="milliseconds")}'
        # )
        # TODO: does this need to be more graceful? (press twice, press two in succession, prevent accidental exit)
        if self._input.doExit():
            exit()
        # TODO pause functionality (start, end, save/restore current state time/ticks, log pausing)
        self._tickCount += 1

        self._stateHandlers[self._state]()
        self._saver.saveTick(self._tickCount, datetime.now(), self._state)

    _stateHandlers: dict[EngineState, Callable[[], None]]

    def _initStateHandlers(self) -> None:
        """map states to functions that handle them"""
        self._stateHandlers = {
            EngineState.ENGINESTART: lambda: self._transitionState(
                EngineState.GETNEXTBLOCK
            ),
            EngineState.GETNEXTBLOCK: self._handleGETNEXTBLOCK,
            EngineState.BLOCKSTART: lambda: self._transitionState(
                EngineState.BLOCKINSTRUCTIONS
            ),
            EngineState.BLOCKINSTRUCTIONS: self._handleBLOCKINSTRUCTIONS,
            EngineState.BLOCKEND: self._handleBLOCKEND,
            EngineState.ENGINEEND: self._handleENGINEEND,  # Changed to use our new handler
            EngineState.TRIALNOTSTARTED: self._handleTRIALNOTSTARTED,
            EngineState.WAITSTART: self._handleWAITSTART,
            EngineState.P0TURN: self._handleP0TURN,
            EngineState.P1TURN: self._handleP1TURN,
            EngineState.LOADTRIALUI: lambda: self._transitionState(
                EngineState.WAITSTART
            ),
            EngineState.RESULT: self._handleRESULT,
            EngineState.ENDED: lambda: logger.warning(
                f"ticked when game already ended"
            ),
            EngineState.FINISHED: lambda: self._transitionState(EngineState.BLOCKEND),
            EngineState.PAUSED: lambda: logger.warning(
                f"pausing, resume not implemented"
            ),
            EngineState.INVALIDGAMESTATE: self._handleINVALIDGAMESTATE,
            EngineState.ENGINECRASH: self._handleENGINECRASH,
        }

    # Modify the _handleGETNEXTBLOCK method to transition to ENGINEEND properly
    def _handleGETNEXTBLOCK(self) -> None:
        self._currentBlock = self._blockProvider.getNextBlock()
        if self._currentBlock is None:
            print("No more blocks available. Transitioning to ENGINEEND state.")
            # Reset waited_for_frames to ensure proper initialization in ENGINEEND state
            self._waited_for_frames = 0
            self._enter_pressed = False
            self._transitionState(EngineState.ENGINEEND)
        else:
            self._saver.saveBlock(self._tickCount, self._currentBlock)
            self._transitionState(EngineState.BLOCKSTART)

    # Modify the _handleTRIALNOTSTARTED method in EngineImpl class
    # Modify the _handleTRIALNOTSTARTED method in EngineImpl class
    def _handleTRIALNOTSTARTED(self) -> None:
        """Properly get next trial or finish block"""
        print("Getting next trial...")

        # Get the next trial from the current block
        self._currentBlock.getNextTrial()

        # Check if there are more trials in this block
        if self._currentBlock.currentTrial is None:
            print("No more trials in current block, finishing block")
            self._transitionState(EngineState.FINISHED)
        else:
            print("Starting new trial")
            # Save the new trial information
            self._saver.saveTrial(self._tickCount, self._currentBlock.currentTrial)

            # Set up the game state for the new trial
            self._gameState = self._currentBlock.currentTrial.initialGameState

            # Determine which player can enter the target, and make them go first
            if (
                hasattr(self._gameState, "canEnterTarget")
                and len(self._gameState.canEnterTarget) == 2
            ):
                if (
                    self._gameState.canEnterTarget[0]
                    and not self._gameState.canEnterTarget[1]
                ):
                    # Player 0 can enter target, Player 1 cannot - Make Player 0 go first
                    self._gameState.playerTurn = 0
                    print("Player 0 can enter target - setting Player 0 to go first")
                elif (
                    not self._gameState.canEnterTarget[0]
                    and self._gameState.canEnterTarget[1]
                ):
                    # Player 1 can enter target, Player 0 cannot - Make Player 1 go first
                    self._gameState.playerTurn = 1
                    print("Player 1 can enter target - setting Player 1 to go first")
                else:
                    # Either both can enter or neither can enter - keep default turn order
                    print(f"Keep default player turn: {self._gameState.playerTurn}")
            else:
                print("canEnterTarget not defined - using default player turn")

            # Reset any reward decay
            if hasattr(self._gameState, "initialReward"):
                self._gameState.currentReward = self._gameState.initialReward

            # Reset moves in current turn
            if hasattr(self._gameState, "movesInCurrentTurn"):
                self._gameState.movesInCurrentTurn = 0

            # Validate the game state and transition
            if not isValidGameState(self._gameState):
                print("Invalid game state detected!")
                self._transitionState(EngineState.INVALIDGAMESTATE)
            else:
                print(
                    f"Loading trial UI with Player {self._gameState.playerTurn} going first"
                )
                self._saver.saveGameState(
                    self._tickCount,
                    self._currentBlock.blockDescriptor,
                    self._currentBlock.currentTrial.trialDescriptor,
                    self._currentBlock.currentTrial.initialGameState,
                )
                self._transitionState(EngineState.LOADTRIALUI)

    # TODO: start trial clock on transition to Turn -> one frame delay in actual time, relevant?
    def _handleWAITSTART(self) -> None:
        self._current_turn = 0
        # Reset moves in turn counter
        self._gameState.movesInCurrentTurn = 0

        if self._waited_for_frames >= conf_game.wait_for_trial_start_frames:
            self._waited_for_frames = 0
            self._input.getInputOfPlayer(self._gameState.playerTurn)
            if self._gameState.playerTurn == 0:
                self._transitionState(EngineState.P0TURN)
            else:
                self._transitionState(EngineState.P1TURN)
            self._trialClock.reset()
        else:
            self._waited_for_frames += 1

    # TODO: is there something that has to happens, which makes these still necessary?
    def _handleP0TURN(self) -> None:
        self._handleTurn()

    def _handleP1TURN(self) -> None:
        self._handleTurn()

    # TODO: handle max total time reached -> start clock on transition from WAITSTART
    # TODO: handle max turn time reached -> state clock?
    # Updated code for _handleTurn method to modify the reward calculation at trial end

    def _handleTurn(self) -> None:
        trial = self._currentBlock.currentTrial

        # Max turns reached
        if self._current_turn >= self._currentBlock.getMaxTurns():
            self._playSound("game_over")
            self._lastTrialResult = TrialResult.MAXTURNSREACHED

            # If trial ends without target reached, no one gets the reward
            reward = (0.0, 0.0)  # No reward if max turns reached

            if trial.countScores:
                self._scoring.addScore(
                    self._currentBlock.blockDescriptor, trial.trialDescriptor, reward
                )

            self._transitionState(EngineState.RESULT)
            return

        # Max total time reached
        if self._maxTotalTimeReached():
            self._playSound("game_over")
            self._lastTrialResult = TrialResult.MAXTOTALTIMEREACHED

            # If trial ends due to time limit, no one gets the reward
            reward = (0.0, 0.0)  # No reward if max total time reached

            if trial.countScores:
                self._scoring.addScore(
                    self._currentBlock.blockDescriptor,
                    trial.trialDescriptor,
                    reward,
                )

            self._transitionState(EngineState.RESULT)
            return

        # Max turn time reached - Handle this BEFORE processing input
        if self._maxTurnTimeReached():
            self._playSound("turn_change")
            self._lastTrialResult = (
                TrialResult.MAXTURNTIMEREACHED
            )  # Record this result if needed
            self._gameState.movesInCurrentTurn = 0
            self._gameState.playerTurn = 1 - self._gameState.playerTurn
            self._transitionState(
                EngineState.P1TURN
                if self._gameState.playerTurn == 1
                else EngineState.P0TURN
            )
            self._input.getInputOfPlayer(0)
            self._input.getInputOfPlayer(1)
            self._current_turn += 1

            if self._gameState.decayReward:
                self._gameState.currentReward = max(
                    0.0,
                    self._gameState.currentReward - self._gameState.rewardDecayAmount,
                )
            return

        # Player blocked
        if playerBlocked(self._gameState):
            self._playSound("game_over")
            self._lastTrialResult = TrialResult.PLAYERTRAPPED

            # If player is trapped, no one gets the reward
            reward = (0.0, 0.0)

            if trial.countScores:
                self._scoring.addScore(
                    self._currentBlock.blockDescriptor,
                    trial.trialDescriptor,
                    reward,
                )

            self._transitionState(EngineState.RESULT)
            return

        # Get input
        direction, speed, special = self._input.getInputOfPlayer(
            self._gameState.playerTurn
        )

        if special == "PLACE_BLOCK":
            self._handleBlockPlacement()
            return

        if direction is None:
            return

        moveStatus = checkMovement(self._gameState, direction, speed)
        if moveStatus != MovementCheckResult.VALID:
            self._playSound("invalid_move")
            return

        movementResult = performMovement(self._gameState, direction, speed)
        self._gameState.movesInCurrentTurn += 1

        # Play sound after each valid move
        self._playSound("turn_change")

        # Target reached
        if movementResult == MovementResult.ENTEREDTARGET:
            self._playSound("target_reached")
            winner = self._gameState.playerTurn
            self._lastTrialResult = (
                TrialResult.P1SCORED if winner == 1 else TrialResult.P0SCORED
            )

            if trial.rewardStrategy == RewardStrategy.WINNER_TAKES_ALL:
                reward = (
                    self._gameState.currentReward if winner == 0 else 0.0,
                    self._gameState.currentReward if winner == 1 else 0.0,
                )
            elif trial.rewardStrategy == RewardStrategy.SPLIT_IF_WIN:
                reward = (
                    self._gameState.currentReward / 2,
                    self._gameState.currentReward / 2,
                )
            else:
                reward = (0.0, 0.0)

            if trial.countScores:
                self._scoring.addScore(
                    self._currentBlock.blockDescriptor, trial.trialDescriptor, reward
                )

            self._transitionState(EngineState.RESULT)
            return

        # Max moves per turn
        if self._gameState.movesInCurrentTurn >= self._gameState.maxMovesPerTurn:
            self._gameState.movesInCurrentTurn = 0
            self._gameState.playerTurn = 1 - self._gameState.playerTurn
            self._transitionState(
                EngineState.P1TURN
                if self._gameState.playerTurn == 1
                else EngineState.P0TURN
            )
            self._input.getInputOfPlayer(0)
            self._input.getInputOfPlayer(1)
            self._current_turn += 1

            if self._gameState.decayReward:
                self._gameState.currentReward = max(
                    0.0,
                    self._gameState.currentReward - self._gameState.rewardDecayAmount,
                )

    def _handleENGINEEND(self) -> None:
        """Display final scores and wait for Enter to exit the game"""
        print(f"In ENGINEEND state, frame: {self._waited_for_frames}")

        # Get all keys that are currently pressed
        all_pressed_keys = []
        if hasattr(self._input, "key_states"):
            # Handle key_states as a list of dictionaries
            for player_idx, player_dict in enumerate(self._input.key_states):
                if player_dict:  # Check if the dictionary exists and is not empty
                    all_pressed_keys.extend(list(player_dict.keys()))
                    print(f"Player {player_idx} keys: {list(player_dict.keys())}")

        # Print currently pressed keys for debugging
        if all_pressed_keys:
            print(f"Currently pressed keys: {all_pressed_keys}")

        # Check for Enter key directly in all pressed keys
        if "KEY_ENTER" in all_pressed_keys:
            print("ENTER detected through direct key state check!")
            # Clear the Enter key state after detecting it
            for player_idx in range(len(self._input.key_states)):
                if player_idx < len(self._input.key_states):
                    self._input.key_states[player_idx].pop("KEY_ENTER", None)
            self._enter_pressed = True

        # Also try the standard check
        keys = self._input.checkForKey("return")
        if keys:
            print("ENTER detected through checkForKey method!")
            self._enter_pressed = True

        # If Enter was pressed, exit the game
        if self._enter_pressed:
            print("Exiting game!")
            self._transitionState(EngineState.ENDED)
        else:
            # Increment frame counter
            self._waited_for_frames += 1
            if (
                self._waited_for_frames % 60 == 0
            ):  # Log every ~1 second (assuming 60fps)
                print(
                    f"Waiting for ENTER key to exit... (frames: {self._waited_for_frames})"
                )

    # Make sure ended() method doesn't consider ENGINEEND as an ended state
    def ended(self) -> bool:
        return self._state in [EngineState.ENDED, EngineState.ENGINECRASH]

    def getPlayerPlacedBlocks(self) -> dict[tuple[int, int], int]:
        """Returns dictionary mapping positions to player IDs for player-placed blocks"""
        if hasattr(self._gameState, "playerPlacedBlocks"):
            return self._gameState.playerPlacedBlocks
        else:
            return {}  # Return empty dict if the attribute doesn't exist

    def _handleBlockPlacement(self) -> None:
        """Handle a player's request to place a block"""
        currentPlayer = self._gameState.playerTurn

        # Check permission to place blocks
        if not self._gameState.canPlaceBlocks[currentPlayer]:
            print(f"Player {currentPlayer} is not allowed to place blocks.")
            self._playSound("invalid_move")
            return

        playerPos = (
            self._gameState.p0Position
            if currentPlayer == 0
            else self._gameState.p1Position
        )

        # Check if there's already a block at this position
        if (
            playerPos in self._gameState.playerPlacedBlocks
            or playerPos in self._gameState.disabledBlocks
        ):
            self._playSound("invalid_move")
            return

        if not hasattr(self._gameState, "playerPlacedBlocks"):
            self._gameState.playerPlacedBlocks = {}

        # Play block placed sound
        self._playSound("block_placed")

        # Place the block
        self._gameState.playerPlacedBlocks[playerPos] = currentPlayer

        # Increment moves counter instead of switching turns immediately
        self._gameState.movesInCurrentTurn += 1

        # If max moves reached, switch turns
        if self._gameState.movesInCurrentTurn >= self._gameState.maxMovesPerTurn:
            # Reset moves counter
            self._gameState.movesInCurrentTurn = 0

            # Switch player turns
            self._gameState.playerTurn = 1 - currentPlayer
            self._transitionState(
                EngineState.P1TURN
                if self._gameState.playerTurn == 1
                else EngineState.P0TURN
            )

            # Clear input buffers
            self._input.getInputOfPlayer(0)
            self._input.getInputOfPlayer(1)  # Increment turn counter

            self._current_turn += 1

            # Play turn change sound
            self._playSound("turn_change")

            # Apply reward decay if configured
            if self._gameState.decayReward:
                self._gameState.currentReward = max(
                    0.0,
                    self._gameState.currentReward - self._gameState.rewardDecayAmount,
                )
        # Otherwise, player can continue their turn
        else:
            print(
                f"Player {currentPlayer} placed a block. Moves used: {self._gameState.movesInCurrentTurn}/{self._gameState.maxMovesPerTurn}"
            )

    def _maxTotalTimeReached(self) -> bool:
        return self._trialClock.getTime() > self._currentBlock.getMaxTotalTime()

    def _maxTurnTimeReached(self) -> bool:
        return self._stateClock.getTime() > self._currentBlock.getMaxTurnTime()

    # In the EngineImpl class, update the _handleBLOCKINSTRUCTIONS method:

    def _handleBLOCKINSTRUCTIONS(self) -> None:
        """Wait for Enter key to continue from instructions"""
        print("In block instructions state, waiting for ENTER")

        # Get all keys that are currently pressed
        all_pressed_keys = []
        if hasattr(self._input, "key_states"):
            # Handle key_states as a list of dictionaries
            for player_idx, player_dict in enumerate(self._input.key_states):
                if player_dict:  # Check if the dictionary exists and is not empty
                    all_pressed_keys.extend(list(player_dict.keys()))
                    print(f"Player {player_idx} keys: {list(player_dict.keys())}")

        # Print currently pressed keys for debugging
        if all_pressed_keys:
            print(f"Currently pressed keys: {all_pressed_keys}")

        # Look specifically for the Enter key
        if "KEY_ENTER" in all_pressed_keys:
            print("ENTER detected through direct key state check!")
            # Clear the Enter key state after detecting it
            for player_idx in range(len(self._input.key_states)):
                if player_idx < len(self._input.key_states):
                    self._input.key_states[player_idx].pop("KEY_ENTER", None)

            # Transition to the next state
            self._transitionState(EngineState.TRIALNOTSTARTED)
            return

        # Also try the standard check
        if self._input.checkForKey("return"):
            print("ENTER detected through checkForKey method!")
            # Clear the Enter key state after detecting it
            for player_idx in range(len(self._input.key_states)):
                if player_idx < len(self._input.key_states):
                    self._input.key_states[player_idx].pop("KEY_ENTER", None)

            # Transition to the next state
            self._transitionState(EngineState.TRIALNOTSTARTED)

    # Modify _handleBLOCKEND method in EngineImpl class
    def _handleBLOCKEND(self) -> None:
        """Display block end screen and wait for Enter before loading next block"""
        print("In block end state, waiting for ENTER to proceed to next block")

        # If this is the first time we're entering this state
        if self._waited_for_frames == 0:
            # Reset the flag that we'll use to track if Enter was pressed
            self._enter_pressed = False

            # Reset current turn counter to 0 for the next block
            self._current_turn = 0

            # If we'll be showing trials left text, make sure it displays max trials
            if hasattr(self, "_trialClock"):
                self._trialClock.reset()
            if hasattr(self, "_stateClock"):
                self._stateClock.reset()

        # Get all keys that are currently pressed
        all_pressed_keys = []
        if hasattr(self._input, "key_states"):
            # Handle key_states as a list of dictionaries
            for player_idx, player_dict in enumerate(self._input.key_states):
                if player_dict:  # Check if the dictionary exists and is not empty
                    all_pressed_keys.extend(list(player_dict.keys()))
                    print(f"Player {player_idx} keys: {list(player_dict.keys())}")

        # Print currently pressed keys for debugging
        if all_pressed_keys:
            print(f"Currently pressed keys: {all_pressed_keys}")

        # Check for Enter key directly in all pressed keys
        if "KEY_ENTER" in all_pressed_keys:
            print("ENTER detected through direct key state check!")
            # Clear the Enter key state after detecting it
            for player_idx in range(len(self._input.key_states)):
                if player_idx < len(self._input.key_states):
                    self._input.key_states[player_idx].pop("KEY_ENTER", None)
            self._enter_pressed = True

        # Also try the standard check
        keys = self._input.checkForKey("return")
        if keys:
            print("ENTER detected through checkForKey method!")
            self._enter_pressed = True

        # If Enter was pressed, proceed to next block
        if self._enter_pressed:
            print("Proceeding to next block!")
            self._waited_for_frames = 0
            self._enter_pressed = False
            self._transitionState(EngineState.GETNEXTBLOCK)
        else:
            # Increment frame counter
            self._waited_for_frames += 1
            if (
                self._waited_for_frames % 60 == 0
            ):  # Log every ~1 second (assuming 60fps)
                print(f"Waiting for ENTER key... (frames: {self._waited_for_frames})")

    def _handleRESULT(self) -> None:
        """Handle the RESULT state with proper transition to next trial"""
        print(
            f"In RESULT state, waiting for {conf_game.wait_for_result_screen_frames} frames"
        )

        if self._waited_for_frames >= conf_game.wait_for_result_screen_frames:
            print("Result screen timer complete, transitioning to next trial")
            self._waited_for_frames = 0
            self._transitionState(EngineState.TRIALNOTSTARTED)
        else:
            self._waited_for_frames += 1
            # Debug output every 30 frames to show progress
            if self._waited_for_frames % 30 == 0:
                print(
                    f"Result wait frames: {self._waited_for_frames}/{conf_game.wait_for_result_screen_frames}"
                )

    def _handleINVALIDGAMESTATE(self) -> None:
        if self._waited_for_frames >= conf_game.show_error_for_frames:
            self._waited_for_frames = 0
            logger.warning(f"invalid game state, crashing"),
            self._transitionState(EngineState.ENGINECRASH)
        else:
            self._waited_for_frames += 1

    def _handleENGINECRASH(self) -> None:
        logger.error(f"!!! engine crashed !!!")
        self._transitionState(EngineState.ENDED)

    def saveFlip(self, time: datetime, trigger: int) -> None:
        self._saver.saveFlip(self._tickCount, time, trigger)
        pass

    def saveGrids(
        self, gridCoordinates: list[dict[tuple[int, int], tuple[int, int]]]
    ) -> None:
        self._saver.saveGrids(
            self._tickCount,
            self._currentBlock.blockDescriptor,
            self._currentBlock.currentTrial.trialDescriptor,
            gridCoordinates,
        )
        pass

    def ended(self) -> bool:
        return self._state in [EngineState.ENDED, EngineState.ENGINEEND]

    def _transitionState(self, newState: EngineState):
        """Transition to a new state with proper clock resets and logging"""
        if not isEngineStateTransitionAllowed(self._state, newState):
            raise ValueError(
                f"Disallowed state transition from {self._state} to {newState}"
            )

        # Log the transition for debugging
        print(f"Transitioning from {self._state} to {newState}")

        # Store the old state for reference
        old_state = self._state

        # Update state
        self._state = newState

        # Reset clocks
        self._stateClock.reset()
        self._waited_for_frames = 0

        # Reset trial clock when entering WAITSTART (beginning of gameplay)
        if newState == EngineState.WAITSTART:
            print("Resetting trial clock for new trial")
            self._trialClock.reset()

        # Inform input system if it has the updateGameState method
        if hasattr(self._input, "updateGameState"):
            self._input.updateGameState(self._state)
