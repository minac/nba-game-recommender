"""NBA API Client for fetching game data."""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time


class NBAClient:
    """Client for interacting with NBA stats API."""

    BASE_URL = "https://stats.nba.com/stats"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://stats.nba.com/',
        'Origin': 'https://stats.nba.com'
    }

    # Top 5 teams (as of 2024-2025 season - can be updated)
    TOP_5_TEAMS = {'BOS', 'DEN', 'MIL', 'PHX', 'LAL'}

    # Star players (simplified - can be expanded)
    STAR_PLAYERS = {
        'LeBron James', 'Stephen Curry', 'Kevin Durant', 'Giannis Antetokounmpo',
        'Luka Doncic', 'Nikola Jokic', 'Joel Embiid', 'Jayson Tatum',
        'Damian Lillard', 'Anthony Davis', 'Devin Booker', 'Kawhi Leonard',
        'Jimmy Butler', 'Donovan Mitchell', 'Trae Young', 'Kyrie Irving'
    }

    def __init__(self):
        """Initialize the NBA client."""
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_games_last_n_days(self, days: int = 7) -> List[Dict]:
        """
        Fetch all completed games from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of game dictionaries with detailed information
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        games = []
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            daily_games = self._get_scoreboard(date_str)
            games.extend(daily_games)
            current_date += timedelta(days=1)
            time.sleep(0.5)  # Rate limiting

        return games

    def _get_scoreboard(self, game_date: str) -> List[Dict]:
        """
        Get scoreboard for a specific date.

        Args:
            game_date: Date in YYYY-MM-DD format

        Returns:
            List of games for that date
        """
        try:
            url = f"{self.BASE_URL}/scoreboardv3"
            params = {
                'GameDate': game_date,
                'LeagueID': '00'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []
            scoreboard = data.get('scoreboard', {})

            for game in scoreboard.get('games', []):
                # Only include completed games
                if game.get('gameStatus') != 3:  # 3 = Final
                    continue

                home_team = game.get('homeTeam', {})
                away_team = game.get('awayTeam', {})

                game_info = {
                    'game_id': game.get('gameId'),
                    'game_date': game_date,
                    'home_team': {
                        'name': home_team.get('teamName'),
                        'abbr': home_team.get('teamTricode'),
                        'score': home_team.get('score', 0)
                    },
                    'away_team': {
                        'name': away_team.get('teamName'),
                        'abbr': away_team.get('teamTricode'),
                        'score': away_team.get('score', 0)
                    },
                    'total_points': home_team.get('score', 0) + away_team.get('score', 0),
                    'final_margin': abs(home_team.get('score', 0) - away_team.get('score', 0))
                }

                # Fetch additional game details (play-by-play for lead changes)
                game_details = self._get_game_details(game_info['game_id'])
                if game_details:
                    game_info.update(game_details)

                games.append(game_info)
                time.sleep(0.5)  # Rate limiting

            return games

        except Exception as e:
            print(f"Error fetching scoreboard for {game_date}: {e}")
            return []

    def _get_game_details(self, game_id: str) -> Optional[Dict]:
        """
        Get detailed game information including lead changes.

        Args:
            game_id: NBA game ID

        Returns:
            Dictionary with game details
        """
        try:
            # Get play-by-play data for lead changes
            url = f"{self.BASE_URL}/playbyplayv3"
            params = {
                'GameID': game_id,
                'EndPeriod': 10,
                'StartPeriod': 1
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            lead_changes = self._calculate_lead_changes(data.get('game', {}).get('actions', []))

            # Get box score for star players
            star_count = self._get_star_players_count(game_id)

            return {
                'lead_changes': lead_changes,
                'star_players_count': star_count
            }

        except Exception as e:
            print(f"Error fetching game details for {game_id}: {e}")
            # Return defaults if API fails
            return {
                'lead_changes': 0,
                'star_players_count': 0
            }

    def _calculate_lead_changes(self, actions: List[Dict]) -> int:
        """
        Calculate number of lead changes from play-by-play data.

        Args:
            actions: List of play-by-play actions

        Returns:
            Number of lead changes
        """
        if not actions:
            return 0

        lead_changes = 0
        previous_leader = None

        for action in actions:
            home_score = action.get('homeScore', 0)
            away_score = action.get('awayScore', 0)

            if home_score > away_score:
                current_leader = 'home'
            elif away_score > home_score:
                current_leader = 'away'
            else:
                current_leader = 'tie'

            if previous_leader and previous_leader != 'tie' and current_leader != 'tie':
                if previous_leader != current_leader:
                    lead_changes += 1

            if current_leader != 'tie':
                previous_leader = current_leader

        return lead_changes

    def _get_star_players_count(self, game_id: str) -> int:
        """
        Get count of star players who played in the game.

        Args:
            game_id: NBA game ID

        Returns:
            Count of star players
        """
        try:
            url = f"{self.BASE_URL}/boxscoretraditionalv3"
            params = {
                'GameID': game_id,
                'EndPeriod': 10,
                'StartPeriod': 1
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            star_count = 0
            players = data.get('boxScoreTraditional', {}).get('players', [])

            for player in players:
                player_name = player.get('name', '')
                if player_name in self.STAR_PLAYERS:
                    star_count += 1

            return star_count

        except Exception as e:
            print(f"Error fetching box score for {game_id}: {e}")
            return 0

    def is_top5_team(self, team_abbr: str) -> bool:
        """Check if a team is in the top 5."""
        return team_abbr in self.TOP_5_TEAMS
