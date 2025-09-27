# Add this to your sound_manager.py file or where your SoundManager class is defined


class SoundManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SoundManager()
        return cls._instance

    def __init__(self):
        self.sounds = {}
        self.sound_enabled = True

    def initialize_sounds(self):
        """Initialize all game sounds"""
        try:
            from psychopy import sound
            import os.path as p

            # Define sound file paths - update these to match your actual file locations
            sound_path = p.join("assets", "sounds")

            # Create dictionary of sounds with proper file paths
            sound_files = {
                "target_reached": p.join(sound_path, "target_reached.wav"),
                "invalid_move": p.join(sound_path, "invalid_move.wav"),
                "turn_change": p.join(sound_path, "turn_change.wav"),
                "game_over": p.join(sound_path, "game_over.wav"),
                "block_placed": p.join(
                    sound_path, "block_placed.wav"
                ),  # Add block_placed sound
            }

            # Load all sounds
            for sound_name, file_path in sound_files.items():
                if p.exists(file_path):
                    self.sounds[sound_name] = sound.Sound(file_path)
                else:
                    print(f"Sound file not found: {file_path}")

            print(f"Initialized {len(self.sounds)} sounds")
        except Exception as e:
            print(f"Error initializing sounds: {str(e)}")
            self.sound_enabled = False

    def play_sound(self, sound_name):
        """Play a sound by name"""
        if not self.sound_enabled:
            return

        if sound_name in self.sounds:
            try:
                self.sounds[sound_name].play()
            except Exception as e:
                print(f"Error playing sound '{sound_name}': {str(e)}")
        else:
            print(f"Sound '{sound_name}' not found!")
            # List available sounds for debugging
            print(f"Available sounds: {list(self.sounds.keys())}")
