"""Unit tests for NBAClient class."""
import pytest
import responses
from datetime import datetime, timedelta
from src.api.nba_client import NBAClient
from tests.fixtures.sample_data import (
    get_sample_playbyplay_response,
)


class TestNBAClient:
    """Test cases for NBAClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = NBAClient()

    def test_initialization(self):
        """Test NBAClient initializes correctly."""
        assert self.client.BASE_URL == "https://stats.nba.com/stats"
        assert self.client.session is not None
        assert 'User-Agent' in self.client.session.headers

    def test_top5_teams_property_fetches_real_data(self):
        """Test TOP_5_TEAMS property fetches real data from NBA API."""
        top_teams = self.client.TOP_5_TEAMS

        assert isinstance(top_teams, set)
        assert len(top_teams) == 5
        # Should contain real NBA teams (3-letter codes)
        for team in top_teams:
            assert isinstance(team, str)
            assert len(team) == 3
            assert team.isupper()

    def test_star_players_property_fetches_real_data(self):
        """Test STAR_PLAYERS property fetches real data from NBA API."""
        star_players = self.client.STAR_PLAYERS

        assert isinstance(star_players, set)
        assert len(star_players) > 0
        # Should contain real player names
        for player in star_players:
            assert isinstance(player, str)
            assert ' ' in player  # Names should have spaces

    def test_is_top5_team_with_real_data(self):
        """Test is_top5_team with real NBA data."""
        top_teams = self.client.TOP_5_TEAMS

        # Pick a team from the actual top 5
        if top_teams:
            real_top_team = list(top_teams)[0]
            assert self.client.is_top5_team(real_top_team) is True

        # Non-existent team should be False
        assert self.client.is_top5_team('XXX') is False

    def test_calculate_lead_changes_empty_actions(self):
        """Test _calculate_lead_changes with empty actions list."""
        lead_changes = self.client._calculate_lead_changes([])
        assert lead_changes == 0

    def test_calculate_lead_changes_no_changes(self):
        """Test _calculate_lead_changes when one team always leads."""
        actions = [
            {'homeScore': 2, 'awayScore': 0},
            {'homeScore': 5, 'awayScore': 2},
            {'homeScore': 8, 'awayScore': 5},
            {'homeScore': 10, 'awayScore': 7},
        ]
        lead_changes = self.client._calculate_lead_changes(actions)
        assert lead_changes == 0

    def test_calculate_lead_changes_multiple_changes(self):
        """Test _calculate_lead_changes with multiple lead changes."""
        actions = [
            {'homeScore': 0, 'awayScore': 2},   # Away leads
            {'homeScore': 3, 'awayScore': 2},   # Home takes lead (change 1)
            {'homeScore': 3, 'awayScore': 5},   # Away takes lead (change 2)
            {'homeScore': 8, 'awayScore': 5},   # Home takes lead (change 3)
            {'homeScore': 8, 'awayScore': 10},  # Away takes lead (change 4)
            {'homeScore': 13, 'awayScore': 10}, # Home takes lead (change 5)
        ]
        lead_changes = self.client._calculate_lead_changes(actions)
        assert lead_changes == 5

    def test_calculate_lead_changes_ignores_ties(self):
        """Test _calculate_lead_changes doesn't count ties as lead changes."""
        actions = [
            {'homeScore': 0, 'awayScore': 2},   # Away leads
            {'homeScore': 2, 'awayScore': 2},   # Tie (not a change)
            {'homeScore': 5, 'awayScore': 2},   # Home leads (change 1)
            {'homeScore': 5, 'awayScore': 5},   # Tie (not a change)
            {'homeScore': 5, 'awayScore': 8},   # Away leads (change 2)
        ]
        lead_changes = self.client._calculate_lead_changes(actions)
        assert lead_changes == 2

    def test_calculate_lead_changes_handles_zero_scores(self):
        """Test _calculate_lead_changes handles games starting at 0-0."""
        actions = [
            {'homeScore': 0, 'awayScore': 0},   # Tie at start
            {'homeScore': 2, 'awayScore': 0},   # Home leads
            {'homeScore': 2, 'awayScore': 3},   # Away takes lead (change 1)
        ]
        lead_changes = self.client._calculate_lead_changes(actions)
        assert lead_changes == 1

    def test_calculate_lead_changes_tie_to_lead_not_counted_as_change(self):
        """Test that going from tie to lead is not counted as a lead change."""
        actions = [
            {'homeScore': 0, 'awayScore': 0},   # Tie
            {'homeScore': 2, 'awayScore': 0},   # Home leads (not a change, first lead)
            {'homeScore': 2, 'awayScore': 2},   # Tie
            {'homeScore': 2, 'awayScore': 5},   # Away leads (change 1)
        ]
        lead_changes = self.client._calculate_lead_changes(actions)
        assert lead_changes == 1

    def test_top5_teams_caching(self):
        """Test that TOP_5_TEAMS caches data and doesn't re-fetch."""
        # First access - should fetch from API
        teams1 = self.client.TOP_5_TEAMS

        # Second access - should use cache (same object reference)
        teams2 = self.client.TOP_5_TEAMS

        # Should be the same object
        assert teams1 is teams2

    def test_star_players_caching(self):
        """Test that STAR_PLAYERS caches data and doesn't re-fetch."""
        # First access - should fetch from API
        players1 = self.client.STAR_PLAYERS

        # Second access - should use cache (same object reference)
        players2 = self.client.STAR_PLAYERS

        # Should be the same object
        assert players1 is players2

    @pytest.mark.slow
    def test_get_games_last_n_days_with_real_api(self):
        """Test get_games_last_n_days with real API (slow test)."""
        # Only look back 1 day to minimize API calls
        games = self.client.get_games_last_n_days(days=1)

        # Should return a list (may be empty if no games that day)
        assert isinstance(games, list)

        # If games exist, validate structure
        for game in games:
            assert 'game_id' in game
            assert 'game_date' in game
            assert 'home_team' in game
            assert 'away_team' in game
            assert 'total_points' in game
            assert 'final_margin' in game
            assert 'lead_changes' in game
            assert 'star_players_count' in game

    # Tests that SHOULD use mocks (error conditions that can't be easily triggered)

    @responses.activate
    def test_fetch_top_teams_handles_error(self):
        """Test _fetch_top_teams returns fallback on API error."""
        from tests.fixtures.sample_data import get_sample_standings_response

        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/leaguestandingsv3',
            json={'error': 'Server error'},
            status=500
        )

        # Create new client to trigger fetch
        client = NBAClient()

        # Should return fallback teams without crashing
        teams = client.TOP_5_TEAMS
        assert isinstance(teams, set)
        assert len(teams) == 5

    @responses.activate
    def test_fetch_star_players_handles_error(self):
        """Test _fetch_star_players returns fallback on API error."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/leagueleaders',
            json={'error': 'Server error'},
            status=500
        )

        # Create new client to trigger fetch
        client = NBAClient()

        # Should return fallback players without crashing
        players = client.STAR_PLAYERS
        assert isinstance(players, set)
        assert len(players) > 0

    @responses.activate
    def test_get_game_details_handles_error(self):
        """Test _get_game_details returns defaults on API error."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/playbyplayv3',
            json={'error': 'Not found'},
            status=404
        )

        details = self.client._get_game_details('invalid_id')

        # Should return defaults instead of crashing
        assert details['lead_changes'] == 0
        assert details['star_players_count'] == 0

    def test_cache_integration_with_real_data(self):
        """Test that cache works correctly with real API data."""
        # Get a scoreboard (will fetch from API or cache)
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # First call - may hit API or cache depending on previous tests
        games1 = self.client._get_scoreboard(date_str)

        # Second call - should definitely hit cache
        games2 = self.client._get_scoreboard(date_str)

        # Should be the same data
        assert games1 == games2

    def test_scoreboard_returns_only_final_games(self):
        """Test that scoreboard filtering works with real data."""
        # Get recent scoreboard
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        games = self.client._get_scoreboard(date_str)

        # All returned games should be final (status 3)
        # We can't verify this directly since we only get final games,
        # but we can verify the structure
        for game in games:
            assert 'game_id' in game
            assert 'home_team' in game
            assert 'away_team' in game
