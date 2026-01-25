"""
Unit tests for GameRoom model
"""
import pytest
from unittest.mock import patch, MagicMock
from models.game_room import GameRoom


class TestGameRoomCreation:
    """Test GameRoom initialization"""
    
    def test_create_empty_room(self, sample_room_code):
        """Test creating an empty room with default parameters"""
        room = GameRoom(sample_room_code)
        
        assert room.room_code == sample_room_code
        assert room.max_players == 2
        assert room.players == {}
        assert room.started is False
        assert room.active is True
        assert room.moderator_id is None
        assert room.engine is None
        assert room.ui is None
    
    def test_create_room_custom_max_players(self, sample_room_code):
        """Test creating a room with custom max_players"""
        room = GameRoom(sample_room_code, max_players=4)
        
        assert room.max_players == 4
    
    def test_room_loads_trials_on_creation(self, sample_room_code, mock_game_config):
        """Test that room loads trial configuration on creation"""
        room = GameRoom(sample_room_code)
        
        assert len(room.trials) == 2
        assert room.current_trial_index == 0
        assert room.trials[0]['target'] == [2, 1]
        assert room.trials[0]['capturer'] == 'R'
    
    def test_room_handles_missing_game_config(self, sample_room_code):
        """Test room creation when game config is missing"""
        with patch('conf.game_config.GAME_CONFIG', {}):
            room = GameRoom(sample_room_code)
            
            assert room.trials == []
            assert room.current_trial_index == 0


class TestPlayerManagement:
    """Test player addition and removal"""
    
    def test_add_moderator(self, empty_room, sample_moderator_id, sample_username):
        """Test adding a moderator to the room"""
        result = empty_room.add_player(sample_moderator_id, sample_username, is_moderator=True)
        
        assert result is True
        assert sample_moderator_id in empty_room.players
        assert empty_room.players[sample_moderator_id]['username'] == sample_username
        assert empty_room.players[sample_moderator_id]['moderator'] is True
        assert empty_room.moderator_id == sample_moderator_id
        assert empty_room.players[sample_moderator_id]['role'] is None
    
    def test_add_regular_player(self, room_with_moderator, sample_player_id):
        """Test adding a regular player to the room"""
        result = room_with_moderator.add_player(sample_player_id, "Player1", is_moderator=False)
        
        assert result is True
        assert sample_player_id in room_with_moderator.players
        assert room_with_moderator.players[sample_player_id]['player_number'] == 0
        assert room_with_moderator.players[sample_player_id]['moderator'] is False
        assert room_with_moderator.players[sample_player_id]['ready'] is False
        assert room_with_moderator.players[sample_player_id]['role'] == 'R'
    
    def test_add_second_player_gets_role_B(self, room_with_moderator):
        """Test that second player gets role 'B'"""
        room_with_moderator.add_player("player-001", "Player1", is_moderator=False)
        result = room_with_moderator.add_player("player-002", "Player2", is_moderator=False)
        
        assert result is True
        assert room_with_moderator.players["player-002"]['player_number'] == 1
        assert room_with_moderator.players["player-002"]['role'] == 'B'
    
    def test_cannot_add_player_when_full(self, room_with_players, sample_player_id):
        """Test that players cannot join when room is full"""
        result = room_with_players.add_player(sample_player_id, "Player3", is_moderator=False)
        
        assert result is False
        assert sample_player_id not in room_with_players.players
    
    def test_is_full_returns_true_when_full(self, room_with_players):
        """Test is_full() returns True when room has max players"""
        assert room_with_players.is_full() is True
    
    def test_is_full_returns_false_when_not_full(self, room_with_moderator):
        """Test is_full() returns False when room has space"""
        assert room_with_moderator.is_full() is False
    
    def test_is_empty_returns_true_for_empty_room(self, empty_room):
        """Test is_empty() returns True for empty room"""
        assert empty_room.is_empty() is True
    
    def test_is_empty_returns_false_with_players(self, room_with_moderator):
        """Test is_empty() returns False when players exist"""
        assert room_with_moderator.is_empty() is False
    
    def test_remove_player(self, room_with_players):
        """Test removing a player from the room"""
        result = room_with_players.remove_player("player-001")
        
        assert result is True
        assert "player-001" not in room_with_players.players
    
    def test_remove_nonexistent_player(self, room_with_players):
        """Test removing a player that doesn't exist"""
        result = room_with_players.remove_player("nonexistent")
        
        assert result is False
    
    def test_remove_player_reassigns_numbers(self, room_with_players):
        """Test that player numbers are reassigned after removal"""
        room_with_players.remove_player("player-001")
        
        # Player 2 should now be player 0
        assert room_with_players.players["player-002"]['player_number'] == 0
    
    def test_remove_moderator_promotes_another_player(self, room_with_players, sample_moderator_id):
        """Test that removing moderator promotes another player"""
        room_with_players.remove_player(sample_moderator_id)
        
        # One of the remaining players should be moderator now
        moderators = [pid for pid, pdata in room_with_players.players.items() 
                     if pdata.get('moderator', False)]
        assert len(moderators) == 1
        assert room_with_players.moderator_id is not None


class TestGameStart:
    """Test game start functionality"""
    
    def test_start_game_success(self, ready_room):
        """Test starting game with all conditions met"""
        result = ready_room.start_game()
        
        assert result is True
        assert ready_room.started is True
    
    def test_start_game_fails_without_enough_players(self, room_with_moderator):
        """Test that game cannot start without enough players"""
        result = room_with_moderator.start_game()
        
        assert result is False
        assert room_with_moderator.started is False
    
    def test_start_game_fails_if_players_not_ready(self, room_with_players):
        """Test that game cannot start if players are not ready"""
        # Players are not marked as ready
        result = room_with_players.start_game()
        
        assert result is False
        assert room_with_players.started is False
    
    def test_start_game_ignores_moderator_ready_status(self, room_with_players):
        """Test that moderator ready status doesn't affect game start"""
        # Mark all non-moderator players as ready
        for player_id, player_data in room_with_players.players.items():
            if not player_data.get('moderator', False):
                player_data['ready'] = True
        
        # Moderator is NOT ready
        room_with_players.players[room_with_players.moderator_id]['ready'] = False
        
        result = room_with_players.start_game()
        
        # Should still start because moderator ready status is ignored
        assert result is True


class TestPositionUpdates:
    """Test player position updates"""
    
    def test_update_player_position(self, room_with_trials):
        """Test updating player position"""
        # Add players first
        room_with_trials.add_player("mod-001", "Moderator", is_moderator=True)
        room_with_trials.add_player("player-001", "Player1", is_moderator=False)
        
        result = room_with_trials.update_player_position("player-001", 1, 0)
        
        assert result is True
        # Position should be updated in current trial
        trial = room_with_trials.trials[room_with_trials.current_trial_index]
        assert trial['start_positions']['R'] == [1, 0]
    
    def test_update_position_toggles_turn(self, room_with_trials):
        """Test that updating position toggles the turn"""
        room_with_trials.add_player("mod-001", "Moderator", is_moderator=True)
        room_with_trials.add_player("player-001", "Player1", is_moderator=False)
        
        trial = room_with_trials.trials[0]
        original_turn = trial.get('turn', 'R')
        
        room_with_trials.update_player_position("player-001", 1, 0)
        
        new_turn = trial['turn']
        assert new_turn != original_turn
    
    def test_update_position_fails_for_nonexistent_player(self, room_with_trials):
        """Test that update fails for player not in room"""
        result = room_with_trials.update_player_position("nonexistent", 1, 0)
        
        assert result is False
    
    def test_update_position_fails_without_trials(self, empty_room):
        """Test that update fails when no trials are configured"""
        empty_room.add_player("player-001", "Player1", is_moderator=False)
        empty_room.trials = []
        
        result = empty_room.update_player_position("player-001", 1, 0)
        
        assert result is False


class TestRoomSerialization:
    """Test room serialization and deserialization"""
    
    def test_to_dict(self, room_with_players):
        """Test converting room to dictionary"""
        room_dict = room_with_players.to_dict()
        
        assert room_dict['room_code'] == room_with_players.room_code
        assert room_dict['max_players'] == room_with_players.max_players
        assert room_dict['started'] == room_with_players.started
        assert 'players' in room_dict
        assert 'trials_count' in room_dict
        assert 'current_trial_index' in room_dict
    
    def test_to_meta(self, room_with_players):
        """Test converting room to metadata for persistence"""
        meta = room_with_players.to_meta()
        
        assert meta['room_code'] == room_with_players.room_code
        assert meta['players'] == room_with_players.players
        assert meta['max_players'] == room_with_players.max_players
        assert meta['started'] == room_with_players.started
        assert meta['active'] == room_with_players.active
        assert meta['moderator_id'] == room_with_players.moderator_id
        assert 'trials' in meta
        assert 'current_trial_index' in meta
    
    def test_from_meta(self, room_with_players):
        """Test creating room from metadata"""
        meta = room_with_players.to_meta()
        
        restored_room = GameRoom.from_meta(meta)
        
        assert restored_room.room_code == room_with_players.room_code
        assert restored_room.players == room_with_players.players
        assert restored_room.max_players == room_with_players.max_players
        assert restored_room.started == room_with_players.started
        assert restored_room.moderator_id == room_with_players.moderator_id
        assert restored_room.trials == room_with_players.trials
        assert restored_room.current_trial_index == room_with_players.current_trial_index
    
    def test_serialization_roundtrip(self, room_with_players):
        """Test that room can be serialized and deserialized without data loss"""
        original_meta = room_with_players.to_meta()
        restored_room = GameRoom.from_meta(original_meta)
        restored_meta = restored_room.to_meta()
        
        assert original_meta == restored_meta


class TestTrialManagement:
    """Test trial configuration and management"""
    
    def test_room_starts_at_trial_zero(self, room_with_trials):
        """Test that room starts at trial index 0"""
        assert room_with_trials.current_trial_index == 0
    
    def test_trials_loaded_from_config(self, room_with_trials):
        """Test that trials are loaded from game config"""
        assert len(room_with_trials.trials) > 0
        assert 'start_positions' in room_with_trials.trials[0]
        assert 'target' in room_with_trials.trials[0]
        assert 'capturer' in room_with_trials.trials[0]
    
    def test_room_handles_empty_trials(self, sample_room_code):
        """Test room with no trials configured"""
        with patch('conf.game_config.GAME_CONFIG', {'trials': []}):
            room = GameRoom(sample_room_code)
            
            assert room.trials == []
            assert room.current_trial_index == 0