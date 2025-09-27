from abc import ABC, abstractmethod
from select import select
import threading
import time
import evdev
from evdev import ecodes
from backend.util import Direction



class PlayerInput(ABC):
    @abstractmethod
    def initInput(self):
        pass

    @abstractmethod
    def doExit(self):
        pass

    @abstractmethod
    def getInputOfPlayer(self, pID: int) -> tuple[Direction, int, str] | None:
        pass

    @abstractmethod
    def checkForKey(self, key_name: str) -> bool:
        pass


class EnhancedMultiKeyboardInput(PlayerInput):
    def __init__(self):
        self.keyboards = []  # List of all available keyboard devices
        self.key_states = [{}, {}, {}]  # Key states for players (0, 1) and control (2)
        self.player_keyboard_map = {}  # Map player IDs to keyboards
        self.control_keyboard = None  # Keyboard for game control
        self.running = True  # Flag to control input thread
        self.input_thread = None  # Thread for processing input events

        # Store keyboard IDs for manual assignment
        self.keyboard_ids = []  # Will store device IDs or paths

    def initInput(self):
        """Find all available keyboards and store their IDs for later assignment"""
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

        # Filter only real typing keyboards (must support KEY_A, KEY_LEFT, KEY_SPACE etc.)
        self.keyboards = []

        for dev in devices:
            caps = dev.capabilities()
            if ecodes.EV_KEY in caps:
                key_codes = caps[ecodes.EV_KEY]
                if any(
                    code in key_codes
                    for code in [ecodes.KEY_A, ecodes.KEY_LEFT, ecodes.KEY_SPACE]
                ):
                    self.keyboards.append(dev)
                    self.keyboard_ids.append(dev.path)  # Store device path as ID

        print(f"Found {len(self.keyboards)} usable keyboards:")
        for i, kb in enumerate(self.keyboards):
            print(f"{i+1}. {kb.name} (path: {kb.path})")

        # Start input processing thread
        self.input_thread = threading.Thread(target=self._process_events, daemon=True)
        self.input_thread.start()

        return (
            self.keyboard_ids
        )  # Return IDs so they can be shown to the user for selection

    def assignKeyboards(self, player1_id, player2_id, control_id=None):
        """Assign specific keyboards to players and control based on their IDs"""
        try:
            # Find and assign Player 1 keyboard
            player1_kb = next(
                (kb for kb in self.keyboards if kb.path == player1_id), None
            )
            if player1_kb:
                self.player_keyboard_map[0] = player1_kb
                print(f"Player 1 will use: {player1_kb.name}")
            else:
                print(f"⚠️ Could not find keyboard with ID {player1_id} for Player 1")

            # Find and assign Player 2 keyboard
            player2_kb = next(
                (kb for kb in self.keyboards if kb.path == player2_id), None
            )
            if player2_kb:
                self.player_keyboard_map[1] = player2_kb
                print(f"Player 2 will use: {player2_kb.name}")
            else:
                print(f"⚠️ Could not find keyboard with ID {player2_id} for Player 2")

            # Find and assign Control keyboard (if provided)
            if control_id:
                control_kb = next(
                    (kb for kb in self.keyboards if kb.path == control_id), None
                )
                if control_kb:
                    self.control_keyboard = control_kb
                    self.player_keyboard_map[2] = control_kb  # Use index 2 for control
                    print(f"Control will use: {control_kb.name}")
                else:
                    print(f"⚠️ Could not find keyboard with ID {control_id} for Control")
            else:
                # If no control keyboard specified, use Player 1's keyboard as control
                self.player_keyboard_map[2] = self.player_keyboard_map.get(0, None)

            return True
        except Exception as e:
            print(f"Error assigning keyboards: {str(e)}")
            return False

    def _process_events(self):
        """Process input events from all keyboards"""
        while self.running:
            # Get unique devices without using set()
            unique_devices = []
            for device in self.player_keyboard_map.values():
                if device and device not in unique_devices:
                    unique_devices.append(device)

            devices = unique_devices

            if not devices:
                time.sleep(0.1)
                continue

            r, _, _ = select(devices, [], [], 0.1)
            for device in r:
                try:
                    for event in device.read():
                        if event.type == ecodes.EV_KEY:
                            # Find all player IDs that use this device
                            player_ids = [
                                pid
                                for pid, kb in self.player_keyboard_map.items()
                                if kb and kb.path == device.path
                            ]

                            if not player_ids:
                                continue

                            key_code = event.code
                            key_name = ecodes.KEY[key_code]

                            # Update key state for all players using this device
                            for player_id in player_ids:
                                if event.value == 1:  # Key press
                                    self.key_states[player_id][key_name] = True
                                    # print(f"[DEBUG] ID {player_id} pressed: {key_name}")
                                elif event.value == 0:  # Key release
                                    self.key_states[player_id].pop(key_name, None)
                except Exception as e:
                    print(f"⚠️ Error reading from device: {e}")

    def doExit(self):
        """Check if ESC key is pressed on any keyboard"""
        # Check all keyboards for ESC key
        for player in range(len(self.key_states)):
            if (
                player in self.player_keyboard_map
                and "KEY_ESC" in self.key_states[player]
            ):
                return True
        return False

    def getInputOfPlayer(
        self, pID: int
    ) -> tuple[Direction, int, str] | tuple[None, None, None]:
        """Get input for the specified player ID (0 or 1)"""
        if pID not in [0, 1] or pID not in self.player_keyboard_map:
            return None, None, None

        # Create a local copy of the state to prevent modification while iterating
        state = self.key_states[pID].copy()

        # Check for special keys
        if "KEY_SPACE" in state:
            # Clear the key state to prevent repeated triggering
            self.key_states[pID].pop("KEY_SPACE", None)
            return None, 0, "PLACE_BLOCK"

        # For player 0 (default controls)
        if pID == 0:
            # Check for direction keys (and clear them after reading)
            if "KEY_UP" in state:
                self.key_states[pID].pop("KEY_UP", None)
                return Direction.TOP, 1, None
            if "KEY_DOWN" in state:
                self.key_states[pID].pop("KEY_DOWN", None)
                return Direction.BOTTOM, 1, None
            if "KEY_LEFT" in state:
                self.key_states[pID].pop("KEY_LEFT", None)
                return Direction.LEFT, 1, None
            if "KEY_RIGHT" in state:
                self.key_states[pID].pop("KEY_RIGHT", None)
                return Direction.RIGHT, 1, None

        # For player 1 (inverted left/right controls)
        elif pID == 1:
            # Check for direction keys (and clear them after reading)
            if "KEY_UP" in state:
                self.key_states[pID].pop("KEY_UP", None)
                return Direction.TOP, 1, None
            if "KEY_DOWN" in state:
                self.key_states[pID].pop("KEY_DOWN", None)
                return Direction.BOTTOM, 1, None
            if "KEY_LEFT" in state:
                self.key_states[pID].pop("KEY_LEFT", None)
                # LEFT key now moves RIGHT for player 2
                return Direction.RIGHT, 1, None
            if "KEY_RIGHT" in state:
                self.key_states[pID].pop("KEY_RIGHT", None)
                # RIGHT key now moves LEFT for player 2
                return Direction.LEFT, 1, None

        return None, None, None

    def cleanup(self):
        """Clean up resources when done"""
        self.running = False
        if self.input_thread:
            self.input_thread.join(timeout=1.0)
        for kb in self.keyboards:
            kb.close()

    def checkForKey(self, key_name: str) -> bool:
        """Check if a specific key is pressed on any keyboard"""
        # Mapping for common keys
        key_map = {
            "return": "KEY_ENTER",
            "enter": "KEY_ENTER",
            "escape": "KEY_ESC",
            "esc": "KEY_ESC",
            "space": "KEY_SPACE",
        }

        # Get the evdev key name
        evdev_key = key_map.get(key_name.lower(), f"KEY_{key_name.upper()}")

        # Debug the state of our key_states array

        # Create a local copy to avoid issues if the dictionary changes
        key_states_copy = self.key_states.copy()

        # First check control keyboard (index 2)
        if 2 in key_states_copy and evdev_key in key_states_copy[2]:
            print(f"Found {evdev_key} on control keyboard!")
            return True

        # Then check player keyboards
        for player_id in [0, 1]:
            if player_id in key_states_copy and evdev_key in key_states_copy[player_id]:
                print(f"Found {evdev_key} on player {player_id} keyboard!")
                return True

        # If we get here, key wasn't found
        return False


#
# # Example of how to use the class:
#
# # Create input handler
# input_handler = EnhancedMultiKeyboardInput()
#
# # Initialize and get available keyboard IDs
# keyboard_ids = input_handler.initInput()
#
# # Show available keyboards to user (in your UI or console)
# # Let user select which keyboard should be assigned to each player
#
# # Assign keyboards to players and control based on user selection
# # For example:
# player1_keyboard_id = keyboard_ids[0]  # First keyboard
# player2_keyboard_id = keyboard_ids[1]  # Second keyboard
# control_keyboard_id = keyboard_ids[2]  # Third keyboard
#
# input_handler.assignKeyboards(
#     player1_keyboard_id,
#     player2_keyboard_id,
#     control_keyboard_id
# )
#
# # Now you can use the input handler normally in your game
