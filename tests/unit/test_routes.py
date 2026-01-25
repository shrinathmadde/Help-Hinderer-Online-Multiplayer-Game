"""
Unit tests for routes (API routes and game routes)
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from models.game_room import GameRoom


class TestAPIRoutesCreateRoom:
    """Test /api/create-room endpoint"""
    
    def test_create_room_success(self, client, mock_redis):
        """Test successfully creating a room via API"""
        response = client.post('/api/create-room',
                              json={'username': 'TestUser'},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert 'room_code' in data
        assert 'player_id' in data
        assert len(data['room_code']) == 6
    
    def test_create_room_default_username(self, client, mock_redis):
        """Test creating room with default username"""
        response = client.post('/api/create-room',
                              json={},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
    
    def test_create_room_saves_to_redis(self, client, mock_redis):
        """Test that creating room saves to Redis"""
        response = client.post('/api/create-room',
                              json={'username': 'TestUser'},
                              content_type='application/json')
        
        # Verify Redis set was called
        assert mock_redis.set.called


class TestAPIRoutesJoinRoom:
    """Test /api/join-room endpoint"""
    
    def test_join_room_success(self, client, mock_redis):
        """Test successfully joining a room"""
        # First create a room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        # Now join the room
        response = client.post('/api/join-room',
                              json={'room_code': room_code, 'username': 'Player1'},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert 'room_code' in data
        assert 'player_id' in data
    
    def test_join_room_not_found(self, client, mock_redis):
        """Test joining a non-existent room"""
        response = client.post('/api/join-room',
                              json={'room_code': 'NOTFOUND', 'username': 'Player1'},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert 'message' in data
    
    def test_join_room_uppercase_conversion(self, client, mock_redis):
        """Test that room code is converted to uppercase"""
        # Create room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        # Join with lowercase
        response = client.post('/api/join-room',
                              json={'room_code': room_code.lower(), 'username': 'Player1'},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_join_room_default_username(self, client, mock_redis):
        """Test joining with default username"""
        # Create room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        # Join without username
        response = client.post('/api/join-room',
                              json={'room_code': room_code},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestAPIRoutesListRooms:
    """Test /api/rooms endpoint"""
    
    def test_list_rooms_empty(self, client, mock_redis):
        """Test listing rooms when none exist"""
        mock_redis.keys.return_value = []
        
        response = client.get('/api/rooms')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['rooms'] == []
    
    def test_list_rooms_with_rooms(self, client, mock_redis):
        """Test listing rooms when some exist"""
        # Create a couple of rooms
        client.post('/api/create-room',
                   json={'username': 'User1'},
                   content_type='application/json')
        client.post('/api/create-room',
                   json={'username': 'User2'},
                   content_type='application/json')
        
        response = client.get('/api/rooms')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert len(data['rooms']) >= 2


class TestAPIRoutesGetRoomInfo:
    """Test /api/room/<room_code> endpoint"""
    
    def test_get_room_info_success(self, client, mock_redis):
        """Test getting room info for existing room"""
        # Create a room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        # Get room info
        response = client.get(f'/api/room/{room_code}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert 'room' in data
        assert data['room']['room_code'] == room_code
        assert 'players' in data['room']
    
    def test_get_room_info_not_found(self, client, mock_redis):
        """Test getting info for non-existent room"""
        response = client.get('/api/room/NOTFOUND')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        
        assert data['success'] is False
    
    def test_get_room_info_includes_players(self, client, mock_redis):
        """Test that room info includes player details"""
        # Create room and join
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        client.post('/api/join-room',
                   json={'room_code': room_code, 'username': 'Player1'},
                   content_type='application/json')
        
        # Get room info
        response = client.get(f'/api/room/{room_code}')
        data = json.loads(response.data)
        
        assert len(data['room']['players']) >= 1


class TestGameRoutesIndex:
    """Test / (index) route"""
    
    def test_index_page_loads(self, client):
        """Test that index page loads successfully"""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'Multiplayer Game' in response.data or b'Helper Hinderer' in response.data


class TestGameRoutesGame:
    """Test /game/<room_code> route"""
    
    def test_game_page_room_not_found(self, client, mock_redis):
        """Test game page for non-existent room"""
        mock_redis.get.return_value = None
        
        response = client.get('/game/NOTFOUND')
        
        assert response.status_code == 404
        assert b'not found' in response.data.lower() or b'Not Found' in response.data
    
    def test_game_page_redirects_if_not_started(self, client, mock_redis):
        """Test that game page redirects to waiting if game not started"""
        # Create a room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        response = client.get(f'/game/{room_code}', follow_redirects=False)
        
        # Should redirect to waiting page
        assert response.status_code == 302
        assert b'/waiting/' in response.data or response.headers.get('Location', '').startswith('/waiting/')
    
    def test_game_page_uppercase_conversion(self, client, mock_redis):
        """Test that room code is converted to uppercase"""
        # Create a room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        # Access with lowercase
        response = client.get(f'/game/{room_code.lower()}', follow_redirects=False)
        
        # Should handle lowercase properly
        assert response.status_code in [200, 302]


class TestGameRoutesWaiting:
    """Test /waiting/<room_code> route"""
    
    def test_waiting_page_loads(self, client, mock_redis):
        """Test that waiting page loads for valid room"""
        # Create a room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        response = client.get(f'/waiting/{room_code}')
        
        assert response.status_code == 200
        assert bytes(room_code, 'utf-8') in response.data
    
    def test_waiting_page_room_not_found(self, client, mock_redis):
        """Test waiting page for non-existent room"""
        mock_redis.get.return_value = None
        
        response = client.get('/waiting/NOTFOUND')
        
        assert response.status_code == 404


class TestGameRoutesDebug:
    """Test /debug/<room_code> route"""
    
    def test_debug_page_loads(self, client, mock_redis):
        """Test that debug page loads for valid room"""
        # Create a room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        response = client.get(f'/debug/{room_code}')
        
        assert response.status_code == 200
    
    def test_debug_page_room_not_found(self, client, mock_redis):
        """Test debug page for non-existent room"""
        mock_redis.get.return_value = None
        
        response = client.get('/debug/NOTFOUND')
        
        assert response.status_code == 404
    
    def test_debug_page_shows_room_info(self, client, mock_redis):
        """Test that debug page shows room information"""
        # Create a room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        response = client.get(f'/debug/{room_code}')
        
        assert response.status_code == 200
        assert bytes(room_code, 'utf-8') in response.data


class TestErrorHandlers:
    """Test error handlers"""
    
    def test_404_handler(self, client):
        """Test 404 error handler"""
        response = client.get('/nonexistent-page')
        
        assert response.status_code == 404
        assert b'not found' in response.data.lower() or b'Not Found' in response.data
    
    def test_404_has_home_link(self, client):
        """Test that 404 page has link to home"""
        response = client.get('/nonexistent-page')
        
        # Should have a link to home page
        assert b'/' in response.data or b'home' in response.data.lower()


class TestRouteIntegration:
    """Test route integration scenarios"""
    
    def test_full_room_creation_flow(self, client, mock_redis):
        """Test complete room creation and joining flow"""
        # 1. Create room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        assert create_response.status_code == 200
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        # 2. Join room
        join_response = client.post('/api/join-room',
                                   json={'room_code': room_code, 'username': 'Player1'},
                                   content_type='application/json')
        assert join_response.status_code == 200
        join_data = json.loads(join_response.data)
        assert join_data['success'] is True
        
        # 3. Check room info
        info_response = client.get(f'/api/room/{room_code}')
        assert info_response.status_code == 200
        info_data = json.loads(info_response.data)
        assert len(info_data['room']['players']) >= 1
        
        # 4. Access waiting page
        waiting_response = client.get(f'/waiting/{room_code}')
        assert waiting_response.status_code == 200
    
    def test_multiple_players_join_same_room(self, client, mock_redis):
        """Test multiple players joining the same room"""
        # Create room
        create_response = client.post('/api/create-room',
                                     json={'username': 'Moderator'},
                                     content_type='application/json')
        create_data = json.loads(create_response.data)
        room_code = create_data['room_code']
        
        # Join as player 1
        join1_response = client.post('/api/join-room',
                                    json={'room_code': room_code, 'username': 'Player1'},
                                    content_type='application/json')
        assert json.loads(join1_response.data)['success'] is True
        
        # Join as player 2
        join2_response = client.post('/api/join-room',
                                    json={'room_code': room_code, 'username': 'Player2'},
                                    content_type='application/json')
        assert json.loads(join2_response.data)['success'] is True
        
        # Check room now has 2 players
        info_response = client.get(f'/api/room/{room_code}')
        info_data = json.loads(info_response.data)
        assert info_data['room']['player_count'] >= 2