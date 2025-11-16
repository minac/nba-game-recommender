"""Shared pytest fixtures and configuration."""
import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_config():
    """Provide a sample configuration dictionary."""
    return {
        'lead_changes_weight': 10,
        'top5_team_bonus': 50,
        'close_game_bonus': 100,
        'min_total_points': 200,
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
        'Jayson Tatum'
    }
