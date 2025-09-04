from psychopy.iohub import launchHubServer
from psychopy.iohub.client.keyboard import Keyboard
from backend.util import Direction
import keyboard as kb  # Standard keyboard library for more device info
import time

class MultiKeyboardPlayerInput:
    """
    Handles input from two separate keyboards for a two-player game.
    Each player is assigned to a specific keyboard identified by its device ID.
    """
    
    def __init__(self):
        self.io = None
        self.keyboards = []
        self.keyboard_devices = []
        self.player_keyboard_map = {}
        self.key_states = [{}, {}]  # Track key states for each player
        
        # Initialize key press history
        self.key_history = [set(), set()]
        
        # Direction mappings for both players
        self.p0_direction_keys = {
            'up': Direction.TOP,
            'down': Direction.BOTTOM,
            'left': Direction.LEFT,
            'right': Direction.RIGHT
        }
        
        self.p1_direction_keys = {
            'w': Direction.TOP,
            's': Direction.BOTTOM,
            'a': Direction.LEFT,
            'd': Direction.RIGHT
        }
        
        # Special action keys
        self.p0_special_keys = {
            'space': 'PLACE_BLOCK'
        }
        
        self.p1_special_keys = {
            'lshift': 'PLACE_BLOCK'  # Left shift for player 2
        }
        
        # Default speeds
        self.p0_speed = 1
        self.p1_speed = 1
    
    def initInput(self):
        """
        Initialize the IO Hub for keyboard monitoring and detect connected keyboards
        """
        # Launch the hub server
        self.io = launchHubServer()
        
        # Get all keyboard devices from IOHub
        print(type(self.io.devices.keyboard))
        
        # Store keyboard device
        self.keyboards = [self.io.devices.keyboard]
        
        # Set up keyboard device mapping based on available devices
        connected_keyboards = kb.get_keyboard_names()
        print(f"Connected keyboards: {connected_keyboards}")
        
        # Map keyboards to players (ideally you'd have a config UI for this)
        # For now, just use the first two keyboards or handle the case of one keyboard
        if len(connected_keyboards) >= 2:
            self.player_keyboard_map = {
                0: connected_keyboards[0],  # Player 0 uses first keyboard
                1: connected_keyboards[1]   # Player 1 uses second keyboard
            }
            print(f"Using separate keyboards for players: {self.player_keyboard_map}")
        else:
            # Fallback to single keyboard
            print("Not enough keyboards detected. Both players will use the same keyboard.")
            if len(connected_keyboards) > 0:
                self.player_keyboard_map = {
                    0: connected_keyboards[0],  # Both players use the same keyboard
                    1: connected_keyboards[0]
                }
        
        print(f"Keyboard mapping: {self.player_keyboard_map}")
    
    def getInputOfPlayer(self, playerID):
        """
        Get the current input for the specified player
        
        Returns:
        - direction: Direction or None
        - speed: Integer
        - special: String or None (for special actions)
        """
        # Clear old key states
        self.key_states[playerID] = {}
        
        # Get keyboard events from IOHub
        keyboard_events = self.keyboards[0].getEvents()
        
        # Process events to detect key presses and releases
        for evt in keyboard_events:
            # Basic filtering (you might want to add device-specific filtering)
            self._process_key_event(evt, playerID)
        
        # Get direction based on pressed keys
        direction = self._get_direction(playerID)
        
        # Get speed based on player
        speed = self.p0_speed if playerID == 0 else self.p1_speed
        
        # Check for special actions
        special = self._check_special_actions(playerID)
        
        return direction, speed, special
    
    def _process_key_event(self, event, playerID):
        """Process a key event and update key states"""
        key = event.key.lower()
        
        if event.type == 'KEYBOARD_PRESS':
            self.key_states[playerID][key] = True
            self.key_history[playerID].add(key)
        elif event.type == 'KEYBOARD_RELEASE':
            if key in self.key_states[playerID]:
                del self.key_states[playerID][key]
    
    def _get_direction(self, playerID):
        """Determine direction based on pressed keys"""
        direction_keys = self.p0_direction_keys if playerID == 0 else self.p1_direction_keys
        
        # Check each direction key to see if it's pressed
        for key, direction in direction_keys.items():
            if key in self.key_states[playerID]:
                return direction
        
        return None  # No direction key pressed
    
    def _check_special_actions(self, playerID):
        """Check for special action keys"""
        special_keys = self.p0_special_keys if playerID == 0 else self.p1_special_keys
        
        # Check each special key to see if it's pressed
        for key, action in special_keys.items():
            if key in self.key_states[playerID]:
                return action
        
        return None  # No special key pressed
    
    def doExit(self):
        """Check if exit key combination is pressed"""
        # Example: exit on Escape key for either player
        for playerID in range(2):
            if 'escape' in self.key_states[playerID]:
                return True
        return False
    
    def checkForKey(self, key_name):
        """Check if a specific key is pressed by either player"""
        # This is used for interface controls like Enter to continue
        for playerID in range(2):
            if key_name in self.key_states[playerID]:
                return True
        
        # Also check current key events
        keyboard_events = self.keyboards[0].getEvents()
        for evt in keyboard_events:
            if evt.type == 'KEYBOARD_PRESS' and evt.key.lower() == key_name.lower():
                return True
        
        return False
    
    def shutdown(self):
        """Clean up resources"""
        if self.io:
            self.io.quit()