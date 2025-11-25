"""Unit tests for NBAClient class (Ball Don't Lie API)."""
import pytest
import responses
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.api.nba_client import NBAClient, NBAAPIError


class TestNBAClient:
    """Test cases for NBAClient class using Ball Don't Lie API."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock the API key for testing
        with patch.dict('os.environ', {'BALLDONTLIE_API_KEY': 'test_key'}):
            self.client = NBAClient()

        # Clear cache to avoid interference between tests
        if self.client.cache:
            self.client.cache.clear_all()

    def test_initialization(self):
        """Test NBAClient initializes correctly."""
        with patch.dict('os.environ', {'BALLDONTLIE_API_KEY': 'test_key'}):
            client = NBAClient()
            assert client.BASE_URL == "https://api.balldontlie.io/v1"
            assert client.session is not None
            assert 'Authorization' in client.session.headers

    def test_initialization_without_api_key_raises_error(self):
        """Test that NBAClient raises error when API key is missing."""
        with patch.dict('os.environ', {}, clear=True):
            # Mock config to not have api_key either
            with patch('builtins.open', side_effect=FileNotFoundError):
                with pytest.raises(NBAAPIError, match="Ball Don't Lie API key not found"):
                    NBAClient()

    def test_top5_teams_returns_default(self):
        """Test TOP_5_TEAMS property returns default teams."""
        top_teams = self.client.TOP_5_TEAMS

        assert isinstance(top_teams, set)
        assert len(top_teams) == 5
        # Should contain NBA team identifiers (either abbreviations or full names)
        # The API may return either format, so check both
        top_teams_normalized = {team.upper() for team in top_teams}
        expected_teams = ['BOS', 'CELTICS', 'DEN', 'NUGGETS', 'OKC', 'THUNDER',
                          'CLE', 'CAVALIERS', 'LAL', 'LAKERS', 'NYK', 'KNICKS']
        assert any(expected in top_teams_normalized for expected in expected_teams)

    def test_star_players_returns_default(self):
        """Test STAR_PLAYERS property returns default players."""
        star_players = self.client.STAR_PLAYERS

        assert isinstance(star_players, set)
        assert len(star_players) > 0
        # Should contain some well-known players
        assert 'LeBron James' in star_players or 'Stephen Curry' in star_players

    def test_is_top5_team(self):
        """Test is_top5_team method."""
        top_teams = self.client.TOP_5_TEAMS

        # Pick a team from the top 5
        if top_teams:
            real_top_team = list(top_teams)[0]
            assert self.client.is_top5_team(real_top_team) is True

        # Non-existent team should be False
        assert self.client.is_top5_team('XXX') is False

    def test_top5_teams_caching(self):
        """Test that TOP_5_TEAMS caches data."""
        teams1 = self.client.TOP_5_TEAMS
        teams2 = self.client.TOP_5_TEAMS

        # Should be the same object (cached)
        assert teams1 is teams2

    def test_star_players_caching(self):
        """Test that STAR_PLAYERS caches data."""
        players1 = self.client.STAR_PLAYERS
        players2 = self.client.STAR_PLAYERS

        # Should be the same object (cached)
        assert players1 is players2

    @responses.activate
    def test_get_scoreboard_success(self):
        """Test _get_scoreboard successfully fetches games."""
        game_date = '2024-01-15'

        # Mock Ball Don't Lie API response
        responses.add(
            responses.GET,
            'https://api.balldontlie.io/v1/games',
            json={
                'data': [
                    {
                        'id': 12345,
                        'status': 'Final',
                        'home_team': {
                            'full_name': 'Los Angeles Lakers',
                            'abbreviation': 'LAL'
                        },
                        'visitor_team': {
                            'full_name': 'Boston Celtics',
                            'abbreviation': 'BOS'
                        },
                        'home_team_score': 118,
                        'visitor_team_score': 115
                    }
                ]
            },
            status=200
        )

        games, from_cache = self.client._get_scoreboard(game_date)

        assert len(games) == 1
        assert games[0]['game_id'] == '12345'
        assert games[0]['home_team']['abbr'] == 'LAL'
        assert games[0]['away_team']['abbr'] == 'BOS'
        assert games[0]['home_team']['score'] == 118
        assert games[0]['away_team']['score'] == 115
        assert games[0]['total_points'] == 233
        assert games[0]['final_margin'] == 3
        assert from_cache is False

    @responses.activate
    def test_get_scoreboard_filters_non_final_games(self):
        """Test _get_scoreboard filters out non-final games."""
        game_date = '2024-01-15'

        responses.add(
            responses.GET,
            'https://api.balldontlie.io/v1/games',
            json={
                'data': [
                    {
                        'id': 1,
                        'status': 'Final',
                        'home_team': {'abbreviation': 'LAL'},
                        'visitor_team': {'abbreviation': 'BOS'},
                        'home_team_score': 100,
                        'visitor_team_score': 98
                    },
                    {
                        'id': 2,
                        'status': 'In Progress',
                        'home_team': {'abbreviation': 'GSW'},
                        'visitor_team': {'abbreviation': 'MIA'},
                        'home_team_score': 50,
                        'visitor_team_score': 45
                    }
                ]
            },
            status=200
        )

        games, from_cache = self.client._get_scoreboard(game_date)

        # Should only return the final game
        assert len(games) == 1
        assert games[0]['game_id'] == '1'
        assert from_cache is False

    @responses.activate
    def test_get_scoreboard_handles_api_error(self):
        """Test _get_scoreboard handles API errors."""
        game_date = '2024-01-15'

        responses.add(
            responses.GET,
            'https://api.balldontlie.io/v1/games',
            json={'error': 'Server error'},
            status=500
        )

        with pytest.raises(NBAAPIError, match="Failed to fetch games"):
            self.client._get_scoreboard(game_date)

    @responses.activate
    def test_get_games_last_n_days(self):
        """Test get_games_last_n_days fetches games for multiple days."""
        # Mock multiple days of games
        for i in range(3):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            responses.add(
                responses.GET,
                'https://api.balldontlie.io/v1/games',
                json={
                    'data': [
                        {
                            'id': 100 + i,
                            'status': 'Final',
                            'home_team': {'full_name': 'Team A', 'abbreviation': 'TMA'},
                            'visitor_team': {'full_name': 'Team B', 'abbreviation': 'TMB'},
                            'home_team_score': 100,
                            'visitor_team_score': 95
                        }
                    ]
                },
                status=200
            )

        games = self.client.get_games_last_n_days(days=2)

        # Should have games from 3 days (start_date to end_date inclusive)
        assert len(games) == 3

    def test_cache_integration(self):
        """Test that cache works correctly."""
        if not self.client.cache:
            pytest.skip("Cache not enabled")

        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Mock first call
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                'https://api.balldontlie.io/v1/games',
                json={'data': [
                    {
                        'id': 999,
                        'status': 'Final',
                        'home_team': {'abbreviation': 'LAL'},
                        'visitor_team': {'abbreviation': 'BOS'},
                        'home_team_score': 100,
                        'visitor_team_score': 98
                    }
                ]},
                status=200
            )

            games1, from_cache1 = self.client._get_scoreboard(date_str)

        # Second call should hit cache (no API call needed)
        games2, from_cache2 = self.client._get_scoreboard(date_str)

        # Should be the same data
        assert games1 == games2
        assert from_cache1 is False  # First call fetches from API
        assert from_cache2 is True   # Second call comes from cache
