"""
Pytest configuration and shared fixtures for all tests
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import after path setup
from app import create_app
from models.game_room import GameRoom
import config


@pytest.fixture
def app():
    """Create and configure a test Flask application instance"""
    app, socketio = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    yield app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application"""
    return app.test_client()


@pytest.fixture
def socketio_client(app):
    """Create a Socket.IO test client"""
    from app import socketio
    return socketio.test_client(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing without actual Redis connection"""
    with patch('services.redis_client.get_redis') as mock:
        # Create a mock Redis instance
        redis_mock = MagicMock()
        
        # In-memory storage for testing
        storage = {}
        
        def mock_set(key, value):
            storage[key] = value
            return True
        
        def mock_get(key):
            return storage.get(key)
        
        def mock_delete(key):
            if key in storage:
                del storage[key]
                return 1
            return 0
        
        def mock_exists(key):
            return key in storage
        
        def mock_keys(pattern):
            # Simple pattern matching for "room:*"
            if pattern == "room:*":
                return [k for k in storage.keys() if k.startswith("room:")]
            return list(storage.keys())
        
        # Configure mock methods
        redis_mock.set = mock_set
        redis_mock.get = mock_get
        redis_mock.delete = mock_delete
        redis_mock.exists = mock_exists
        redis_mock.keys = mock_keys
        redis_mock.hgetall = MagicMock(return_value={})
        
        # Make the mock return itself when accessed as a property
        mock.return_value = redis_mock
        
        # Also patch the direct import used in services
        with patch('services.room_service.get_redis', redis_mock):
            with patch('services.game_service.get_redis', redis_mock):
                yield redis_mock


@pytest.fixture
def sample_room_code():
    """Sample room code for testing"""
    return "ABC123"


@pytest.fixture
def sample_player_id():
    """Sample player ID for testing"""
    return "player-test-001"


@pytest.fixture
def sample_moderator_id():
    """Sample moderator ID for testing"""
    return "moderator-test-001"


@pytest.fixture
def sample_username():
    """Sample username for testing"""
    return "TestPlayer"


@pytest.fixture
def empty_room(sample_room_code):
    """Create an empty GameRoom instance"""
    return GameRoom(sample_room_code, max_players=2)


@pytest.fixture
def room_with_moderator(sample_room_code, sample_moderator_id, sample_username):
    """Create a room with a moderator"""
    room = GameRoom(sample_room_code, max_players=2)
    room.add_player(sample_moderator_id, sample_username, is_moderator=True)
    return room


@pytest.fixture
def room_with_players(sample_room_code, sample_moderator_id):
    """Create a room with a moderator and two players"""
    room = GameRoom(sample_room_code, max_players=2)
    room.add_player(sample_moderator_id, "Moderator", is_moderator=True)
    room.add_player("player-001", "Player1", is_moderator=False)
    room.add_player("player-002", "Player2", is_moderator=False)
    return room


@pytest.fixture
def sample_game_config():
    """Sample game configuration for testing"""
    return {
        "board_size": 4,
        "trials": [
            {
                "start_positions": {
                    "R": [0, 0],
                    "B": [3, 3],
                },
                "target": [2, 1],
                "capturer": "R",
                "time_limit_sec": 20,
                "turn": "R"
            },
            {
                "start_positions": {
                    "R": [3, 0],
                    "B": [0, 3]
                },
                "target": [1, 2],
                "capturer": "B",
                "time_limit_sec": 20,
                "turn": "B"
            }
        ]
    }


@pytest.fixture
def mock_game_config(sample_game_config):
    """Mock the game config module"""
    with patch('conf.game_config.GAME_CONFIG', sample_game_config):
        yield sample_game_config


@pytest.fixture
def room_with_trials(sample_room_code, sample_game_config):
    """Create a room with trial configuration loaded"""
    with patch('conf.game_config.GAME_CONFIG', sample_game_config):
        room = GameRoom(sample_room_code, max_players=2)
        return room


@pytest.fixture
def ready_room(room_with_players):
    """Create a room with all players ready"""
    room = room_with_players
    for player_id, player_data in room.players.items():
        if not player_data.get('moderator', False):
            player_data['ready'] = True
    return room


@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration after each test"""
    yield
    # Reset any config changes if needed


@pytest.fixture
def mock_socketio():
    """Mock Socket.IO instance for testing"""
    mock = MagicMock()
    mock.emit = MagicMock()
    mock.send = MagicMock()
    return mock


@pytest.fixture
def mock_room_service():
    """Mock room service functions"""
    with patch('services.room_service.get_room') as mock_get, \
         patch('services.room_service.save_room') as mock_save, \
         patch('services.room_service.create_room') as mock_create:
        
        yield {
            'get_room': mock_get,
            'save_room': mock_save,
            'create_room': mock_create
        }


@pytest.fixture
def mock_game_service():
    """Mock game service functions"""
    with patch('services.game_service.start_game') as mock_start, \
         patch('services.game_service.mark_player_ready') as mock_ready, \
         patch('services.game_service.update_position') as mock_update:
        
        yield {
            'start_game': mock_start,
            'mark_player_ready': mock_ready,
            'update_position': mock_update
        }