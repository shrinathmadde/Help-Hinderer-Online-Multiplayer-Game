from backend.game_state import GameState
from backend.trial import Trial
from backend.trial import RewardStrategy, TrialType
import random

premadeTestTrials0: list[Trial] =  [
    # Trial 1 – Player 0 practices reaching the star, Player 1 tests box movement
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(0, 4),
            p0Position=(4, 0),
            p1Position=(4, 4),
            disabledBlocks=[],
            movableBoxesPositions=[(4, 3)],  # Near Player 1
            wallLocations=[],
            playerTurn=0,
            canEnterTarget=(True, False),
            canMoveBoxes=(False, True),
            canPlaceBlocks=(False, True),
            playerPlacedBlocks={},
            initialReward=0.0,
            currentReward=0.0,
            decayReward=False,
            rewardDecayAmount=0.0,
        ),
        maxTurns=20,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.rand,
        countScores=False,
    ),

    # Trial 2 – Player 1 practices reaching the star, Player 0 tests box movement
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(4, 0),
            p0Position=(0, 0),
            p1Position=(0, 4),
            disabledBlocks=[],
            movableBoxesPositions=[(0, 1)],  # Near Player 0
            wallLocations=[],
            playerTurn=0,
            canEnterTarget=(False, True),
            canMoveBoxes=(True, False),
            canPlaceBlocks=(True, False),
            playerPlacedBlocks={},
            initialReward=0.0,
            currentReward=0.0,
            decayReward=False,
            rewardDecayAmount=0.0,
        ),
        maxTurns=20,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.rand,
        countScores=False,
    )
]

premadeTestTrials1: list[Trial] = [
    # Trial 1 – Target: middle-left
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(2, 0),
            p1Position=(0, 4),  # Attacker (opposite corner)
            p0Position=(0, 0),  # Other (same side)
            movableBoxesPositions=[(2, 1)],  # Near target
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(False, True),
            canMoveBoxes=(True, False),
            canPlaceBlocks=(True, False),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.hinder,
        countScores=True,
    ),

    # Trial 2 – Target: top-middle (rotated 90° clockwise)
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(0, 2),
            p1Position=(4, 4),  # Attacker (opposite side)
            p0Position=(0, 4),  # Other (same side corner)
            movableBoxesPositions=[(0, 3)],  # Near target
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(False, True),
            canMoveBoxes=(True, False),
            canPlaceBlocks=(True, False),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.hinder,
        countScores=True,
    ),

    # Trial 3 – Target: middle-right (rotated 180°)
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(2, 4),
            p0Position=(4, 0),  # Attacker (opposite corner)
            p1Position=(4, 4),  # Other (same side)
            movableBoxesPositions=[(2, 3)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(True, False),
            canMoveBoxes=(False, True),
            canPlaceBlocks=(False, True),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.hinder,
        countScores=True,
    ),

    # Trial 4 – Target: bottom-middle (rotated 270°)
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(4, 2),
            p0Position=(0, 0),  # Attacker
            p1Position=(4, 0),  # Other
            movableBoxesPositions=[(4, 1)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(True, False),
            canMoveBoxes=(False, True),
            canPlaceBlocks=(False, True),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.hinder,
        countScores=True,
    ),
]



premadeTestTrials2: list[Trial] = [
    # Trial 1 – Target: middle-left, Player 1 attacks
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(2, 0),
            p1Position=(0, 0),  # Helper/Hinderer
            p0Position=(0, 4),  # Attacker
            movableBoxesPositions=[(1, 0)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(True, False),
            canMoveBoxes=(False, True),
            canPlaceBlocks=(False, True),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.help,
        countScores=True,
    ),

    # Trial 2 – Target: top-middle, Player 1 attacks
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(0, 2),
            p1Position=(0, 4),
            p0Position=(4, 4),
            movableBoxesPositions=[(1, 2)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(True, False),
            canMoveBoxes=(False, True),
            canPlaceBlocks=(False, True),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.help,
        countScores=True,
    ),

    # Trial 3 – Target: middle-right, Player 1 attacks
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(2, 4),
            p0Position=(4, 4),
            p1Position=(4, 0),
            movableBoxesPositions=[(1, 4)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(False, True),
            canMoveBoxes=(True, False),
            canPlaceBlocks=(True, False),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=15,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.help,
        countScores=True,
    ),

    # Trial 4 – Target: bottom-middle, Player 1 attacks
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(4, 2),
            p0Position=(4, 0),
            p1Position=(0, 0),
            movableBoxesPositions=[(4, 1)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(False, True),
            canMoveBoxes=(True, False),
            canPlaceBlocks=(True, False),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=RewardStrategy.WINNER_TAKES_ALL,
        trialType=TrialType.help,
        countScores=True,
    ),
]



premadeTestTrials3: list[Trial] = [
    # Trial 1 – Player 0 attacks from top-right
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(2, 0),
            p0Position=(0, 4),  # Attacker
            p1Position=(0, 0),  # Other player
            movableBoxesPositions=[(1, 0)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(True, False),
            canMoveBoxes=(False, True),
            canPlaceBlocks=(False, True),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=random.choice([
            RewardStrategy.WINNER_TAKES_ALL,
            RewardStrategy.SPLIT_IF_WIN
        ]),
        trialType=TrialType.rand,
        countScores=True,
    ),

    # Trial 2 – Player 1 attacks from bottom-middle
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(0, 2),
            p1Position=(0, 0),
            p0Position=(4, 0),
            movableBoxesPositions=[(1, 2)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(True, False),
            canMoveBoxes=(False, True),
            canPlaceBlocks=(False, True),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=random.choice([
            RewardStrategy.WINNER_TAKES_ALL,
            RewardStrategy.SPLIT_IF_WIN
        ]),
        trialType=TrialType.rand,
        countScores=True,
    ),

    # Trial 3 – Player 0 attacks from bottom-left
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(2, 4),
            p1Position=(4, 0),
            p0Position=(4, 4),
            movableBoxesPositions=[(1, 4)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(False, True),
            canMoveBoxes=(True, False),
            canPlaceBlocks=(True, False),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=random.choice([
            RewardStrategy.WINNER_TAKES_ALL,
            RewardStrategy.SPLIT_IF_WIN
        ]),
        trialType=TrialType.rand,
        countScores=True,
    ),

    # Trial 4 – Player 1 attacks from top-middle
    Trial(
        initialGameState=GameState(
            fieldSize=(5, 5),
            targetPosition=(4, 2),
            p0Position=(4, 4),
            p1Position=(0, 4),
            movableBoxesPositions=[(4, 1)],
            wallLocations=[],
            disabledBlocks=[],
            playerTurn=0,
            canEnterTarget=(False, True),
            canMoveBoxes=(True, False),
            canPlaceBlocks=(True, False),
            playerPlacedBlocks={},
            initialReward=10.0,
            currentReward=10.0,
            decayReward=True,
            rewardDecayAmount=0.5,
        ),
        maxTurns=12,
        rewardStrategy=random.choice([
            RewardStrategy.WINNER_TAKES_ALL,
            RewardStrategy.SPLIT_IF_WIN
        ]),
        trialType=TrialType.rand,
        countScores=True,
    ),
]

