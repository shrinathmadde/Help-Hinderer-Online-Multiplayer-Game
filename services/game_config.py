# services/game_config.py
GAME_CONFIG = {
    "board_size": 4,
    "trials": [
        {
            # fixed starting positions for this trial
            "start_positions": {
                "R": [0, 0],    # player 0 (red)
                "B": [3, 3],    # player 1 (blue)
            },
            "target": [2, 1],
            "capturer": "R",   # only R can capture; B blocks
            "time_limit_sec": 20,
        },
        {
            "start_positions": { "R": [3, 0], "B": [0, 3] },
            "target": [1, 2],
            "capturer": "B",
            "time_limit_sec": 20,
        },
        # add more trials...
    ]
}
