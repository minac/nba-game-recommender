"""BalldontlieAPI Client for fetching NBA game data."""
import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import time
from dotenv import load_dotenv


class BalldontlieClient:
    """Client for interacting with Balldontlie API."""

    BASE_URL = "https://api.balldontlie.io"
    # Note: Modern API uses /nba/v1, legacy uses /api/v1

    # Cache duration in seconds (24 hours)
    CACHE_DURATION = 86400

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Balldontlie client.

        Args:
            api_key: Optional API key. If not provided, will load from .env file
        """
        # Load environment variables from .env file
        load_dotenv()

        # Use provided API key or load from environment
        self.api_key = api_key or os.getenv('BALLDONTLIE_API_KEY')

        if not self.api_key:
            raise ValueError(
                "Balldontlie API key not found. "
                "Please set BALLDONTLIE_API_KEY environment variable or pass api_key parameter."
            )

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'{self.api_key}',
            'Accept': 'application/json'
        })

        # Cache for dynamic data
        self._top_teams_cache: Optional[Set[str]] = None
        self._star_players_cache: Optional[Set[str]] = None
        self._teams_cache: Optional[Dict[int, Dict]] = None
        self._cache_timestamp: Optional[datetime] = None

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

        try:
            # Fetch games within date range
            url = f"{self.BASE_URL}/nba/v1/games"
            params = {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'per_page': 100
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []
            for game_data in data.get('data', []):
                # Only include completed games (status == 'Final')
                if game_data.get('status') != 'Final':
                    continue

                game = self._parse_game_data(game_data)
                if game:
                    games.append(game)
                    time.sleep(0.1)  # Rate limiting

            # Handle pagination if needed
            meta = data.get('meta', {})
            next_cursor = meta.get('next_cursor')

            while next_cursor:
                params['cursor'] = next_cursor
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                for game_data in data.get('data', []):
                    if game_data.get('status') != 'Final':
                        continue
                    game = self._parse_game_data(game_data)
                    if game:
                        games.append(game)
                        time.sleep(0.1)

                meta = data.get('meta', {})
                next_cursor = meta.get('next_cursor')

            return games

        except Exception as e:
            print(f"Error fetching games from Balldontlie API: {e}")
            return []

    def _parse_game_data(self, game_data: Dict) -> Optional[Dict]:
        """
        Parse game data from Balldontlie API format to internal format.

        Args:
            game_data: Raw game data from Balldontlie API

        Returns:
            Parsed game dictionary
        """
        try:
            home_team = game_data.get('home_team', {})
            visitor_team = game_data.get('visitor_team', {})
            home_score = game_data.get('home_team_score', 0)
            visitor_score = game_data.get('visitor_team_score', 0)

            game_info = {
                'game_id': str(game_data.get('id')),
                'game_date': game_data.get('date', '').split('T')[0],  # Extract date from ISO format
                'home_team': {
                    'name': home_team.get('full_name', ''),
                    'abbr': home_team.get('abbreviation', ''),
                    'score': home_score
                },
                'away_team': {
                    'name': visitor_team.get('full_name', ''),
                    'abbr': visitor_team.get('abbreviation', ''),
                    'score': visitor_score
                },
                'total_points': home_score + visitor_score,
                'final_margin': abs(home_score - visitor_score)
            }

            # Try to get detailed game statistics
            game_details = self._get_game_details(game_info['game_id'])
            if game_details:
                game_info.update(game_details)
            else:
                # Use defaults if detailed stats not available
                game_info['lead_changes'] = 0
                game_info['star_players_count'] = 0

            return game_info

        except Exception as e:
            print(f"Error parsing game data: {e}")
            return None

    def _get_game_details(self, game_id: str) -> Optional[Dict]:
        """
        Get detailed game information including stats.

        Args:
            game_id: Game ID

        Returns:
            Dictionary with game details
        """
        try:
            # Get stats for the game
            url = f"{self.BASE_URL}/nba/v1/stats"
            params = {
                'game_ids[]': game_id,
                'per_page': 100
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            stats = data.get('data', [])

            # Calculate star players count
            star_count = self._count_star_players(stats)

            # Note: Balldontlie API doesn't provide play-by-play data for lead changes
            # We'll set this to 0 as a limitation of this API
            return {
                'lead_changes': 0,  # Not available in Balldontlie API
                'star_players_count': star_count
            }

        except Exception as e:
            print(f"Error fetching game details for {game_id}: {e}")
            return {
                'lead_changes': 0,
                'star_players_count': 0
            }

    def _count_star_players(self, stats: List[Dict]) -> int:
        """
        Count star players who played in the game.

        Args:
            stats: List of player stats from the game

        Returns:
            Count of star players
        """
        star_count = 0
        star_players = self.STAR_PLAYERS

        for stat in stats:
            player = stat.get('player', {})
            player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()

            if player_name in star_players:
                star_count += 1

        return star_count

    def _get_teams(self) -> Dict[int, Dict]:
        """
        Fetch all NBA teams.

        Returns:
            Dictionary mapping team IDs to team info
        """
        if self._teams_cache:
            return self._teams_cache

        try:
            url = f"{self.BASE_URL}/nba/v1/teams"
            params = {'per_page': 100}

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            teams = {}
            for team in data.get('data', []):
                teams[team['id']] = team

            self._teams_cache = teams
            return teams

        except Exception as e:
            print(f"Error fetching teams: {e}")
            return {}

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self._cache_timestamp is None:
            return False
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self.CACHE_DURATION

    def _fetch_top_teams(self) -> Set[str]:
        """
        Fetch current top 5 teams.

        Note: Balldontlie free tier might not have standings data,
        so we fallback to a reasonable default.

        Returns:
            Set of team abbreviations for top 5 teams
        """
        try:
            # TODO: Implement standings fetching when available in API tier
            # For now, return a reasonable default based on current season
            print("Using default top 5 teams (standings not available in current API tier)")
            return {'BOS', 'DEN', 'OKC', 'MIN', 'LAC'}

        except Exception as e:
            print(f"Error fetching top teams: {e}")
            return {'BOS', 'DEN', 'OKC', 'MIN', 'LAC'}

    def _fetch_star_players(self) -> Set[str]:
        """
        Fetch current star players.

        Note: Using a default list of star players.
        This could be enhanced with the leaders endpoint if available in API tier.

        Returns:
            Set of star player names
        """
        try:
            # Fallback to a reasonable default list of current star players
            return {
                'LeBron James', 'Stephen Curry', 'Kevin Durant', 'Giannis Antetokounmpo',
                'Luka Doncic', 'Nikola Jokic', 'Joel Embiid', 'Jayson Tatum',
                'Damian Lillard', 'Anthony Davis', 'Devin Booker', 'Kawhi Leonard',
                'Jimmy Butler', 'Donovan Mitchell', 'Trae Young', 'Kyrie Irving',
                'Shai Gilgeous-Alexander', 'Anthony Edwards', 'Tyrese Haliburton',
                'Jaylen Brown', 'Karl-Anthony Towns', 'Ja Morant', 'Zion Williamson',
                'Paolo Banchero', 'De\'Aaron Fox', 'Bam Adebayo', 'Jalen Brunson',
                'Tyrese Maxey', 'Scottie Barnes', 'Franz Wagner'
            }

        except Exception as e:
            print(f"Error fetching star players: {e}")
            return {
                'LeBron James', 'Stephen Curry', 'Kevin Durant', 'Giannis Antetokounmpo',
                'Luka Doncic', 'Nikola Jokic', 'Joel Embiid', 'Jayson Tatum',
                'Damian Lillard', 'Anthony Davis', 'Devin Booker', 'Kawhi Leonard',
                'Jimmy Butler', 'Donovan Mitchell', 'Trae Young', 'Kyrie Irving'
            }

    @property
    def TOP_5_TEAMS(self) -> Set[str]:
        """Get top 5 teams (cached)."""
        if not self._is_cache_valid() or self._top_teams_cache is None:
            self._top_teams_cache = self._fetch_top_teams()
            self._cache_timestamp = datetime.now()
        return self._top_teams_cache

    @property
    def STAR_PLAYERS(self) -> Set[str]:
        """Get star players (cached)."""
        if not self._is_cache_valid() or self._star_players_cache is None:
            self._star_players_cache = self._fetch_star_players()
            if self._cache_timestamp is None:
                self._cache_timestamp = datetime.now()
        return self._star_players_cache

    def is_top5_team(self, team_abbr: str) -> bool:
        """Check if a team is in the top 5."""
        return team_abbr in self.TOP_5_TEAMS
