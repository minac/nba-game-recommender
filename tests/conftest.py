"""Shared pytest fixtures and configuration."""
import pytest
import sys
import shutil
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test API key for Ball Don't Lie
os.environ['BALLDONTLIE_API_KEY'] = 'test_key_for_tests'


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before any tests run."""
    # Allow cache to persist across tests for better performance with real API calls
    # This helps avoid rate limiting and speeds up test execution
    yield
    # Optionally clean up after all tests (commented out to preserve cache)
    # test_cache_dir = Path('/tmp/nba_cache')
    # if test_cache_dir.exists():
    #     shutil.rmtree(test_cache_dir)


@pytest.fixture
def temp_cache_dir():
    """Provide a temporary cache directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix='nba_test_cache_')
    yield temp_dir
    # Cleanup
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config():
    """Provide a sample configuration dictionary."""
    return {
        'lead_changes_weight': 10,
        'top5_team_bonus': 50,
        'close_game_bonus': 100,
        'min_total_points': 200,
        'high_score_bonus': 10,
        'star_power_weight': 20,
        'favorite_team_bonus': 75
    }


@pytest.fixture
def top5_teams():
    """Provide a set of top 5 teams."""
    return {'LAL', 'BOS', 'DEN', 'MIL', 'PHX'}


@pytest.fixture
def star_players():
    """Provide a set of star players."""
    return {
        'LeBron James',
        'Stephen Curry',
        'Kevin Durant',
        'Giannis Antetokounmpo',
        'Jayson Tatum',
        'Anthony Davis',
        'Damian Lillard',
        'Nikola Jokic'
    }


@pytest.fixture
def mock_nba_api_responses():
    """Provide mocked NBA API responses for common endpoints."""
    from tests.fixtures.sample_data import (
        get_sample_scoreboard_response,
        get_sample_playbyplay_response,
        get_sample_boxscore_response,
        get_sample_standings_response,
        get_sample_league_leaders_response
    )

    return {
        'scoreboard': get_sample_scoreboard_response(),
        'playbyplay': get_sample_playbyplay_response(),
        'boxscore': get_sample_boxscore_response(),
        'standings': get_sample_standings_response(),
        'league_leaders': get_sample_league_leaders_response()
    }


@pytest.fixture
def mock_nba_client_with_cache_disabled(star_players, top5_teams):
    """Create a mock NBA client with cache disabled and fixed data."""
    with patch('src.api.nba_client.NBAClient') as MockClient:
        mock_client = Mock()

        # Set up properties to return fixed sets
        mock_client.TOP_5_TEAMS = top5_teams
        mock_client.STAR_PLAYERS = star_players
        mock_client.is_top5_team = lambda team: team in top5_teams

        # Return the mock instance when instantiated
        MockClient.return_value = mock_client

        yield mock_client
