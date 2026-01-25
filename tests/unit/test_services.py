"""
Unit tests for services (room_service and game_service)
"""
import pytest
import json
from unittest.mock import patch, MagicMock, call
from models.game_room import GameRoom
import services.room_service as room_service
import services.game_service as game_service


class TestRoomServiceRoomCodeGeneration:
    """Test room code generation"""
    
    def test_generate_room_code_default_length(self, mock_redis):
        """Test generating room code with default length"""
        code = room_service.generate_room_code()
        
        assert len(code) == 6
        assert code.isalnum()
        assert code.isupper() or code.isdigit()
    
    def test_generate_room_code_custom_length(self, mock_redis):
        """Test generating room code with custom length"""
        code = room_service.generate_room_code(length=8)
        
        assert len(code) == 8
    
    def test_generate_room_code_uniqueness(self, mock_redis):
        """Test that generated codes are unique"""
        mock_redis.exists.side_effect = [True, True, False]  # First 2 exist, 3rd doesn't
        
        code = room_service.generate_room_code()
        
        # Should have checked 3 times before finding unique code
        assert mock_redis.exists.call_count == 3
        assert code is not None


class TestRoomServiceCreateRoom:
    """Test room creation"""
    
    def test_create_room_success(self, mock_redis):
        """Test successfully creating a room"""
        room_code, moderator_id, room = room_service.create_room("TestModerator", max_players=2)
        
        assert room_code is not None
        assert len(room_code) == 6
        assert moderator_id is not None
        assert isinstance(room, GameRoom)
        assert room.moderator_id == moderator_id
        assert moderator_id in room.players
        assert room.players[moderator_id]['moderator'] is True
    
    def test_create_room_saves_to_redis(self, mock_redis):
        """Test that room is saved to Redis"""
        room_code, moderator_id, room = room_service.create_room("TestModerator")
        
        # Check that Redis set was called
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        
        # Verify the key format
        assert call_args[0][0].startswith("room:")
        assert room_code in call_args[0][0]
        
        # Verify the data is JSON
        saved_data = json.loads(call_args[0][1])
        assert saved_data['room_code'] == room_code
    
    def test_create_room_with_custom_max_players(self, mock_redis):
        """Test creating room with custom max_players"""
        room_code, moderator_id, room = room_service.create_room("TestModerator", max_players=4)
        
        assert room.max_players == 4


class TestRoomServiceGetRoom:
    """Test retrieving rooms"""
    
    def test_get_room_success(self, mock_redis, sample_room_code):
        """Test getting an existing room"""
        # Create a room and save it
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        meta = room.to_meta()
        
        mock_redis.get.return_value = json.dumps(meta)
        
        retrieved_room = room_service.get_room(sample_room_code)
        
        assert retrieved_room is not None
        assert retrieved_room.room_code == sample_room_code
        assert "mod-001" in retrieved_room.players
    
    def test_get_room_not_found(self, mock_redis):
        """Test getting a non-existent room"""
        mock_redis.get.return_value = None
        
        result = room_service.get_room("NOTFOUND")
        
        assert result is None
    
    def test_get_room_uppercase_conversion(self, mock_redis, sample_room_code):
        """Test that room code is converted to uppercase"""
        room = GameRoom(sample_room_code)
        meta = room.to_meta()
        mock_redis.get.return_value = json.dumps(meta)
        
        # Request with lowercase
        retrieved_room = room_service.get_room(sample_room_code.lower())
        
        assert retrieved_room is not None
        assert retrieved_room.room_code == sample_room_code


class TestRoomServiceSaveRoom:
    """Test saving rooms"""
    
    def test_save_room(self, mock_redis, room_with_moderator):
        """Test saving a room to Redis"""
        room_service.save_room(room_with_moderator)
        
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        
        # Verify key format
        assert f"room:{room_with_moderator.room_code}" == call_args[0][0]
        
        # Verify data is valid JSON
        saved_data = json.loads(call_args[0][1])
        assert saved_data['room_code'] == room_with_moderator.room_code


class TestRoomServiceJoinRoom:
    """Test joining rooms"""
    
    def test_join_room_success(self, mock_redis, sample_room_code):
        """Test successfully joining a room"""
        # Setup: create a room with moderator
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        meta = room.to_meta()
        
        mock_redis.get.return_value = json.dumps(meta)
        
        success, player_id, error_message = room_service.join_room(sample_room_code, "NewPlayer")
        
        assert success is True
        assert player_id is not None
        assert error_message == ""
        
        # Verify room was saved with new player
        assert mock_redis.set.call_count >= 1
    
    def test_join_room_not_found(self, mock_redis):
        """Test joining a non-existent room"""
        mock_redis.get.return_value = None
        
        success, player_id, error_message = room_service.join_room("NOTFOUND", "Player")
        
        assert success is False
        assert player_id == ""
        assert "not found" in error_message.lower()
    
    def test_join_room_when_full(self, mock_redis, sample_room_code):
        """Test joining a room that is full"""
        # Setup: create a full room
        room = GameRoom(sample_room_code, max_players=2)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        room.add_player("player-001", "Player1", is_moderator=False)
        room.add_player("player-002", "Player2", is_moderator=False)
        meta = room.to_meta()
        
        mock_redis.get.return_value = json.dumps(meta)
        
        success, player_id, error_message = room_service.join_room(sample_room_code, "Player3")
        
        assert success is False
        assert "full" in error_message.lower()


class TestRoomServiceRemovePlayer:
    """Test removing players"""
    
    def test_remove_player_success(self, mock_redis, sample_room_code):
        """Test successfully removing a player"""
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        room.add_player("player-001", "Player1", is_moderator=False)
        meta = room.to_meta()
        
        mock_redis.get.return_value = json.dumps(meta)
        
        result = room_service.remove_player(sample_room_code, "player-001")
        
        assert result is True
        # Room should be saved after player removal
        assert mock_redis.set.call_count >= 1
    
    def test_remove_player_removes_empty_room(self, mock_redis, sample_room_code):
        """Test that empty room is removed"""
        room = GameRoom(sample_room_code)
        room.add_player("player-001", "Player1", is_moderator=False)
        meta = room.to_meta()
        
        mock_redis.get.return_value = json.dumps(meta)
        
        room_service.remove_player(sample_room_code, "player-001")
        
        # Should have called delete to remove the room
        assert mock_redis.delete.call_count >= 1


class TestRoomServiceRemoveRoom:
    """Test removing entire rooms"""
    
    def test_remove_room(self, mock_redis, sample_room_code):
        """Test removing a room"""
        mock_redis.delete.return_value = 1
        
        result = room_service.remove_room(sample_room_code)
        
        assert result is True
        mock_redis.delete.assert_called_once_with(f"room:{sample_room_code}")


class TestRoomServiceGetActiveRooms:
    """Test listing active rooms"""
    
    def test_get_active_rooms(self, mock_redis):
        """Test getting list of active rooms"""
        mock_redis.keys.return_value = ["room:ABC123", "room:DEF456"]
        
        rooms = room_service.get_active_rooms()
        
        assert len(rooms) == 2
        assert "ABC123" in rooms
        assert "DEF456" in rooms


class TestRoomServiceCleanupInactiveRooms:
    """Test cleanup of inactive rooms"""
    
    def test_cleanup_inactive_rooms(self, mock_redis):
        """Test cleaning up inactive rooms"""
        # Setup: create some rooms, mark one as inactive
        room1 = GameRoom("ROOM001")
        room1.active = True
        
        room2 = GameRoom("ROOM002")
        room2.active = False
        
        mock_redis.keys.return_value = ["room:ROOM001", "room:ROOM002"]
        
        def mock_get(key):
            if "ROOM001" in key:
                return json.dumps(room1.to_meta())
            elif "ROOM002" in key:
                return json.dumps(room2.to_meta())
            return None
        
        mock_redis.get.side_effect = mock_get
        mock_redis.delete.return_value = 1
        
        removed_count = room_service.cleanup_inactive_rooms()
        
        assert removed_count >= 1


class TestGameServiceStartGame:
    """Test game start functionality"""
    
    def test_start_game_success(self, mock_redis, sample_room_code):
        """Test successfully starting a game"""
        # Setup: create a ready room
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        room.add_player("player-001", "Player1", is_moderator=False)
        room.add_player("player-002", "Player2", is_moderator=False)
        room.players["player-001"]["ready"] = True
        room.players["player-002"]["ready"] = True
        
        meta = room.to_meta()
        mock_redis.get.return_value = json.dumps(meta)
        
        result = game_service.start_game(sample_room_code, "mod-001")
        
        assert result['success'] is True
    
    def test_start_game_room_not_found(self, mock_redis):
        """Test starting game for non-existent room"""
        mock_redis.get.return_value = None
        
        result = game_service.start_game("NOTFOUND", "player-001")
        
        assert result['success'] is False
        assert "not found" in result['message'].lower()
    
    def test_start_game_not_moderator(self, mock_redis, sample_room_code):
        """Test that only moderator can start game"""
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        room.add_player("player-001", "Player1", is_moderator=False)
        
        meta = room.to_meta()
        mock_redis.get.return_value = json.dumps(meta)
        
        result = game_service.start_game(sample_room_code, "player-001")
        
        assert result['success'] is False
        assert "moderator" in result['message'].lower()
    
    def test_start_game_not_enough_players(self, mock_redis, sample_room_code):
        """Test that game requires enough players"""
        room = GameRoom(sample_room_code, max_players=2)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        room.add_player("player-001", "Player1", is_moderator=False)
        
        meta = room.to_meta()
        mock_redis.get.return_value = json.dumps(meta)
        
        result = game_service.start_game(sample_room_code, "mod-001")
        
        assert result['success'] is False
        assert "players" in result['message'].lower()


class TestGameServiceMarkPlayerReady:
    """Test marking players as ready"""
    
    def test_mark_player_ready_success(self, mock_redis, sample_room_code):
        """Test successfully marking a player as ready"""
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        room.add_player("player-001", "Player1", is_moderator=False)
        
        meta = room.to_meta()
        mock_redis.get.return_value = json.dumps(meta)
        
        result = game_service.mark_player_ready(sample_room_code, "player-001")
        
        assert result is True
        # Should save the room with updated ready status
        assert mock_redis.set.call_count >= 1
    
    def test_mark_player_ready_room_not_found(self, mock_redis):
        """Test marking ready for non-existent room"""
        mock_redis.get.return_value = None
        
        result = game_service.mark_player_ready("NOTFOUND", "player-001")
        
        assert result is False
    
    def test_mark_player_ready_player_not_in_room(self, mock_redis, sample_room_code):
        """Test marking ready for player not in room"""
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        
        meta = room.to_meta()
        mock_redis.get.return_value = json.dumps(meta)
        
        result = game_service.mark_player_ready(sample_room_code, "nonexistent")
        
        assert result is False


class TestGameServiceUpdatePosition:
    """Test position update functionality"""
    
    def test_update_position_success(self, mock_redis, sample_room_code, mock_game_config):
        """Test successfully updating player position"""
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        room.add_player("player-001", "Player1", is_moderator=False)
        
        meta = room.to_meta()
        mock_redis.get.return_value = json.dumps(meta)
        
        result = game_service.update_position(sample_room_code, "player-001", 1, 0)
        
        assert result is True
        # Room should be saved after update
        assert mock_redis.set.call_count >= 1
    
    def test_update_position_room_not_found(self, mock_redis):
        """Test updating position for non-existent room"""
        mock_redis.get.return_value = None
        
        result = game_service.update_position("NOTFOUND", "player-001", 1, 0)
        
        assert result is None
    
    def test_update_position_invalid_player(self, mock_redis, sample_room_code):
        """Test updating position for invalid player"""
        room = GameRoom(sample_room_code)
        room.add_player("mod-001", "Moderator", is_moderator=True)
        
        meta = room.to_meta()
        mock_redis.get.return_value = json.dumps(meta)
        
        result = game_service.update_position(sample_room_code, "nonexistent", 1, 0)
        
        assert result is None


class TestGameServiceSocketIO:
    """Test Socket.IO integration"""
    
    def test_set_socketio(self):
        """Test setting Socket.IO instance"""
        mock_socketio = MagicMock()
        
        game_service.set_socketio(mock_socketio)
        
        assert game_service._socketio is mock_socketio
    
    def test_emit_with_socketio_set(self, mock_redis, sample_room_code):
        """Test that events are emitted when Socket.IO is set"""
        mock_socketio = MagicMock()
        game_service.set_socketio(mock_socketio)
        
        # This would be tested in integration tests
        # Here we just verify the setup works
        assert game_service._socketio is not None