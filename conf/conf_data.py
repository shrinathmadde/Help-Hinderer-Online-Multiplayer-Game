import os.path as p

# recordings_dir: str = p.join(
#     "C:",
#     "shri_code",
#     "Psychologyminjob",
#     "helperhinderer-main",
#     "recordings",
# )
recordings_dir: str = r"/home/shrinath/helperhinderer/recordings"

if not p.exists(recordings_dir):
    raise ValueError(
        f"recordings_dir {recordings_dir} in conf_data.py does not exist, please create it"
    )

append_saver_blockProviderFilename: str = "block_provider.txt"
append_saver_blockFilename: str = "blocks.txt"
append_saver_trialFilename: str = "trials.txt"
append_saver_tickFilename: str = "engine_ticks.csv"
append_saver_flipFilename: str = "ui_last_flip.csv"
append_saver_gameStateFilename: str = "gameStates.txt"
