"""Unit tests for BallDontLieClient."""
import pytest
import responses
from datetime import datetime

from src.api.balldontlie_client import BallDontLieClient


@pytest.fixture
def client():
    """Create a BallDontLieClient instance for testing."""
    return BallDontLieClient(api_key="test_api_key_12345")


@pytest.fixture
def sample_balldontlie_response():
    """Sample BallDontLie API response."""
    return {
        "data": [
            {
                "id": 123456,
                "status": "Final",
                "home_team": {
                    "id": 1,
                    "abbreviation": "LAL",
                    "full_name": "Los Angeles Lakers"
                },
                "visitor_team": {
                    "id": 2,
                    "abbreviation": "BOS",
                    "full_name": "Boston Celtics"
                },
                "home_team_score": 118,
                "visitor_team_score": 115
            },
            {
                "id": 123457,
                "status": "Final",
                "home_team": {
                    "id": 3,
                    "abbreviation": "GSW",
                    "full_name": "Golden State Warriors"
                },
                "visitor_team": {
                    "id": 4,
                    "abbreviation": "MIL",
                    "full_name": "Milwaukee Bucks"
                },
                "home_team_score": 110,
                "visitor_team_score": 120
            }
        ]
    }


class TestBallDontLieClient:
    """Test suite for BallDontLieClient."""

    @responses.activate
    def test_get_games_by_date(self, client, sample_balldontlie_response):
        """Test fetching games for a specific date."""
        responses.add(
            responses.GET,
            "https://api.balldontlie.io/v1/games",
            json=sample_balldontlie_response,
            status=200
        )

        games = client._get_games_by_date('2024-01-15')

        assert len(games) == 2
        assert games[0]['game_id'] == '123456'
        assert games[0]['home_team']['abbr'] == 'LAL'
        assert games[0]['away_team']['abbr'] == 'BOS'
        assert games[0]['home_team']['score'] == 118
        assert games[0]['away_team']['score'] == 115
        assert games[0]['total_points'] == 233
        assert games[0]['final_margin'] == 3

    @responses.activate
    def test_get_games_with_no_games(self, client):
        """Test fetching games when no games are available."""
        responses.add(
            responses.GET,
            "https://api.balldontlie.io/v1/games",
            json={"data": []},
            status=200
        )

        games = client._get_games_by_date('2024-01-15')

        assert len(games) == 0

    @responses.activate
    def test_get_games_filters_non_final_games(self, client):
        """Test that non-final games are filtered out."""
        response_data = {
            "data": [
                {
                    "id": 123456,
                    "status": "Final",
                    "home_team": {
                        "id": 1,
                        "abbreviation": "LAL",
                        "full_name": "Los Angeles Lakers"
                    },
                    "visitor_team": {
                        "id": 2,
                        "abbreviation": "BOS",
                        "full_name": "Boston Celtics"
                    },
                    "home_team_score": 118,
                    "visitor_team_score": 115
                },
                {
                    "id": 123457,
                    "status": "In Progress",
                    "home_team": {
                        "id": 3,
                        "abbreviation": "GSW",
                        "full_name": "Golden State Warriors"
                    },
                    "visitor_team": {
                        "id": 4,
                        "abbreviation": "MIL",
                        "full_name": "Milwaukee Bucks"
                    },
                    "home_team_score": 80,
                    "visitor_team_score": 75
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://api.balldontlie.io/v1/games",
            json=response_data,
            status=200
        )

        games = client._get_games_by_date('2024-01-15')

        assert len(games) == 1
        assert games[0]['game_id'] == '123456'

    @responses.activate
    def test_api_error_handling(self, client):
        """Test that API errors are handled gracefully."""
        responses.add(
            responses.GET,
            "https://api.balldontlie.io/v1/games",
            json={"error": "API error"},
            status=500
        )

        games = client._get_games_by_date('2024-01-15')

        assert len(games) == 0

    def test_estimate_lead_changes_close_game(self, client):
        """Test lead change estimation for close games."""
        # Very close game (margin <= 3)
        lead_changes = client._estimate_lead_changes(100, 98)
        assert lead_changes == 15

        # Close game (margin <= 5)
        lead_changes = client._estimate_lead_changes(100, 95)
        assert lead_changes == 10

        # Competitive game (margin <= 10)
        lead_changes = client._estimate_lead_changes(100, 92)
        assert lead_changes == 5

        # Moderately competitive (margin <= 15)
        lead_changes = client._estimate_lead_changes(100, 87)
        assert lead_changes == 2

        # Blowout (margin > 15)
        lead_changes = client._estimate_lead_changes(120, 90)
        assert lead_changes == 0

    def test_get_team_abbreviation(self, client):
        """Test team name to abbreviation mapping."""
        assert client.get_team_abbreviation('Los Angeles Lakers') == 'LAL'
        assert client.get_team_abbreviation('Boston Celtics') == 'BOS'
        assert client.get_team_abbreviation('Golden State Warriors') == 'GSW'
        assert client.get_team_abbreviation('Unknown Team') is None

    def test_client_initialization(self):
        """Test that client initializes with correct headers."""
        api_key = "test_key_123"
        client = BallDontLieClient(api_key=api_key)

        assert client.api_key == api_key
        assert client.session.headers['Authorization'] == api_key
        assert client.session.headers['Accept'] == 'application/json'
