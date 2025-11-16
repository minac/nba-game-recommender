"""Unit tests for NBAClient class."""
import pytest
import responses
from datetime import datetime, timedelta
from src.api.nba_client import NBAClient
from tests.fixtures.sample_data import (
    get_sample_scoreboard_response,
    get_sample_playbyplay_response,
    get_sample_boxscore_response
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

    def test_top5_teams_constant(self):
        """Test TOP_5_TEAMS constant is defined."""
        assert isinstance(NBAClient.TOP_5_TEAMS, set)
        assert len(NBAClient.TOP_5_TEAMS) == 5
        assert 'BOS' in NBAClient.TOP_5_TEAMS

    def test_star_players_constant(self):
        """Test STAR_PLAYERS constant is defined."""
        assert isinstance(NBAClient.STAR_PLAYERS, set)
        assert 'LeBron James' in NBAClient.STAR_PLAYERS
        assert 'Stephen Curry' in NBAClient.STAR_PLAYERS

    def test_is_top5_team_true(self):
        """Test is_top5_team returns True for top 5 teams."""
        assert self.client.is_top5_team('BOS') is True
        assert self.client.is_top5_team('LAL') is True

    def test_is_top5_team_false(self):
        """Test is_top5_team returns False for non-top 5 teams."""
        assert self.client.is_top5_team('SAC') is False
        assert self.client.is_top5_team('POR') is False

    @responses.activate
    def test_get_scoreboard_success(self):
        """Test _get_scoreboard successfully fetches games."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/scoreboardv3',
            json=get_sample_scoreboard_response(),
            status=200
        )

        # Mock the game details calls
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/playbyplayv3',
            json=get_sample_playbyplay_response(),
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json=get_sample_boxscore_response(),
            status=200
        )

        games = self.client._get_scoreboard('2024-01-15')

        assert len(games) == 2
        assert games[0]['game_id'] == '0022300123'
        assert games[0]['home_team']['abbr'] == 'LAL'
        assert games[0]['away_team']['abbr'] == 'BOS'

    @responses.activate
    def test_get_scoreboard_only_final_games(self):
        """Test _get_scoreboard only returns completed games."""
        scoreboard_data = {
            'scoreboard': {
                'games': [
                    {
                        'gameId': '001',
                        'gameStatus': 3,  # Final
                        'homeTeam': {'teamName': 'Lakers', 'teamTricode': 'LAL', 'score': 110},
                        'awayTeam': {'teamName': 'Celtics', 'teamTricode': 'BOS', 'score': 108}
                    },
                    {
                        'gameId': '002',
                        'gameStatus': 2,  # In Progress - should be excluded
                        'homeTeam': {'teamName': 'Warriors', 'teamTricode': 'GSW', 'score': 50},
                        'awayTeam': {'teamName': 'Heat', 'teamTricode': 'MIA', 'score': 48}
                    },
                    {
                        'gameId': '003',
                        'gameStatus': 1,  # Not Started - should be excluded
                        'homeTeam': {'teamName': 'Suns', 'teamTricode': 'PHX', 'score': 0},
                        'awayTeam': {'teamName': 'Nuggets', 'teamTricode': 'DEN', 'score': 0}
                    }
                ]
            }
        }

        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/scoreboardv3',
            json=scoreboard_data,
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/playbyplayv3',
            json=get_sample_playbyplay_response(),
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json=get_sample_boxscore_response(),
            status=200
        )

        games = self.client._get_scoreboard('2024-01-15')

        # Should only return the game with status 3 (Final)
        assert len(games) == 1
        assert games[0]['game_id'] == '001'

    @responses.activate
    def test_get_scoreboard_handles_error(self):
        """Test _get_scoreboard handles API errors gracefully."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/scoreboardv3',
            json={'error': 'Server error'},
            status=500
        )

        games = self.client._get_scoreboard('2024-01-15')

        # Should return empty list on error
        assert games == []

    @responses.activate
    def test_get_scoreboard_calculates_total_and_margin(self):
        """Test _get_scoreboard correctly calculates total points and margin."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/scoreboardv3',
            json=get_sample_scoreboard_response(),
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/playbyplayv3',
            json=get_sample_playbyplay_response(),
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json=get_sample_boxscore_response(),
            status=200
        )

        games = self.client._get_scoreboard('2024-01-15')

        # First game: LAL 110 vs BOS 108
        assert games[0]['total_points'] == 218
        assert games[0]['final_margin'] == 2

        # Second game: GSW 95 vs MIA 100
        assert games[1]['total_points'] == 195
        assert games[1]['final_margin'] == 5

    @responses.activate
    def test_get_game_details_success(self):
        """Test _get_game_details successfully fetches lead changes and stars."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/playbyplayv3',
            json=get_sample_playbyplay_response(),
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json=get_sample_boxscore_response(),
            status=200
        )

        details = self.client._get_game_details('0022300123')

        assert 'lead_changes' in details
        assert 'star_players_count' in details
        assert isinstance(details['lead_changes'], int)
        assert isinstance(details['star_players_count'], int)

    @responses.activate
    def test_get_game_details_handles_error(self):
        """Test _get_game_details returns defaults on error."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/playbyplayv3',
            json={'error': 'Not found'},
            status=404
        )

        details = self.client._get_game_details('invalid_id')

        # Should return defaults
        assert details['lead_changes'] == 0
        assert details['star_players_count'] == 0

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

    @responses.activate
    def test_get_star_players_count_success(self):
        """Test _get_star_players_count correctly counts star players."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json=get_sample_boxscore_response(),
            status=200
        )

        star_count = self.client._get_star_players_count('0022300123')

        # Sample data has LeBron James, Jayson Tatum, and Anthony Davis
        assert star_count == 3

    @responses.activate
    def test_get_star_players_count_no_stars(self):
        """Test _get_star_players_count when no star players played."""
        boxscore_data = {
            'boxScoreTraditional': {
                'players': [
                    {'name': 'Regular Player 1', 'points': 10},
                    {'name': 'Regular Player 2', 'points': 12},
                ]
            }
        }
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json=boxscore_data,
            status=200
        )

        star_count = self.client._get_star_players_count('0022300123')
        assert star_count == 0

    @responses.activate
    def test_get_star_players_count_handles_error(self):
        """Test _get_star_players_count returns 0 on error."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json={'error': 'Server error'},
            status=500
        )

        star_count = self.client._get_star_players_count('invalid_id')
        assert star_count == 0

    @responses.activate
    def test_get_games_last_n_days(self):
        """Test get_games_last_n_days fetches games across multiple days."""
        # Mock responses for scoreboard calls
        for _ in range(3):  # Will be called for each day
            responses.add(
                responses.GET,
                'https://stats.nba.com/stats/scoreboardv3',
                json=get_sample_scoreboard_response(),
                status=200
            )

        # Mock game details calls (2 games per day * 3 days = 6 calls each)
        for _ in range(6):
            responses.add(
                responses.GET,
                'https://stats.nba.com/stats/playbyplayv3',
                json=get_sample_playbyplay_response(),
                status=200
            )
            responses.add(
                responses.GET,
                'https://stats.nba.com/stats/boxscoretraditionalv3',
                json=get_sample_boxscore_response(),
                status=200
            )

        games = self.client.get_games_last_n_days(days=2)

        # Should aggregate games from multiple days
        assert len(games) > 0
        assert all('game_id' in game for game in games)
        assert all('lead_changes' in game for game in games)
        assert all('star_players_count' in game for game in games)

    @responses.activate
    def test_get_games_last_n_days_empty(self):
        """Test get_games_last_n_days when no games found."""
        # Mock empty scoreboard responses
        empty_response = {'scoreboard': {'games': []}}

        for _ in range(2):
            responses.add(
                responses.GET,
                'https://stats.nba.com/stats/scoreboardv3',
                json=empty_response,
                status=200
            )

        games = self.client.get_games_last_n_days(days=1)
        assert games == []

    @responses.activate
    def test_get_scoreboard_missing_optional_data(self):
        """Test _get_scoreboard handles missing optional data gracefully."""
        scoreboard_data = {
            'scoreboard': {
                'games': [
                    {
                        'gameId': '001',
                        'gameStatus': 3,
                        'homeTeam': {
                            'teamName': 'Lakers',
                            'teamTricode': 'LAL',
                            # Missing score - should default to 0
                        },
                        'awayTeam': {
                            'teamName': 'Celtics',
                            'teamTricode': 'BOS',
                            'score': 100
                        }
                    }
                ]
            }
        }

        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/scoreboardv3',
            json=scoreboard_data,
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/playbyplayv3',
            json=get_sample_playbyplay_response(),
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json=get_sample_boxscore_response(),
            status=200
        )

        games = self.client._get_scoreboard('2024-01-15')

        assert len(games) == 1
        assert games[0]['home_team']['score'] == 0
        assert games[0]['total_points'] == 100

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

    @responses.activate
    def test_headers_are_set_correctly(self):
        """Test that proper headers are sent with API requests."""
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/scoreboardv3',
            json=get_sample_scoreboard_response(),
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/playbyplayv3',
            json=get_sample_playbyplay_response(),
            status=200
        )
        responses.add(
            responses.GET,
            'https://stats.nba.com/stats/boxscoretraditionalv3',
            json=get_sample_boxscore_response(),
            status=200
        )

        self.client._get_scoreboard('2024-01-15')

        # Check that the request was made with proper headers
        assert len(responses.calls) > 0
        request_headers = responses.calls[0].request.headers
        assert 'User-Agent' in request_headers
        assert 'Referer' in request_headers
