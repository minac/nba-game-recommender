"""BallDontLie API Client for fetching game data (backup data source)."""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

from src.utils.logger import get_logger

logger = get_logger(__name__)


class BallDontLieClient:
    """Client for interacting with BallDontLie API as a backup data source."""

    BASE_URL = "https://api.balldontlie.io/v1"

    def __init__(self, api_key: str):
        """
        Initialize the BallDontLie client.

        Args:
            api_key: BallDontLie API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': api_key,
            'Accept': 'application/json'
        })

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
            daily_games = self._get_games_by_date(date_str)
            games.extend(daily_games)
            current_date += timedelta(days=1)
            time.sleep(0.6)  # Rate limiting (BallDontLie has 100 requests/min limit)

        return games

    def _get_games_by_date(self, game_date: str) -> List[Dict]:
        """
        Get games for a specific date.

        Args:
            game_date: Date in YYYY-MM-DD format

        Returns:
            List of games for that date
        """
        try:
            url = f"{self.BASE_URL}/games"
            params = {
                'start_date': game_date,
                'end_date': game_date
            }

            logger.info(f"Fetching games for {game_date} from BallDontLie API...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []
            for game in data.get('data', []):
                # Only include completed games
                if game.get('status') != 'Final':
                    continue

                home_team = game.get('home_team', {})
                visitor_team = game.get('visitor_team', {})
                home_score = game.get('home_team_score', 0)
                visitor_score = game.get('visitor_team_score', 0)

                game_info = {
                    'game_id': str(game.get('id')),
                    'game_date': game_date,
                    'home_team': {
                        'name': home_team.get('full_name'),
                        'abbr': home_team.get('abbreviation'),
                        'score': home_score
                    },
                    'away_team': {
                        'name': visitor_team.get('full_name'),
                        'abbr': visitor_team.get('abbreviation'),
                        'score': visitor_score
                    },
                    'total_points': home_score + visitor_score,
                    'final_margin': abs(home_score - visitor_score),
                    # BallDontLie doesn't provide detailed play-by-play data
                    # So we estimate based on final score
                    'lead_changes': self._estimate_lead_changes(home_score, visitor_score),
                    # BallDontLie doesn't provide player data in basic endpoint
                    'star_players_count': 0
                }

                games.append(game_info)

            return games

        except Exception as e:
            logger.error(f"Error fetching games for {game_date} from BallDontLie: {e}")
            return []

    def _estimate_lead_changes(self, home_score: int, visitor_score: int) -> int:
        """
        Estimate lead changes based on final score closeness.
        This is a heuristic since BallDontLie doesn't provide play-by-play data.

        Args:
            home_score: Home team final score
            visitor_score: Visitor team final score

        Returns:
            Estimated number of lead changes
        """
        margin = abs(home_score - visitor_score)

        # Heuristic: closer games likely had more lead changes
        if margin <= 3:
            return 15  # Very close game
        elif margin <= 5:
            return 10  # Close game
        elif margin <= 10:
            return 5   # Competitive game
        elif margin <= 15:
            return 2   # Moderately competitive
        else:
            return 0   # Blowout

    def get_team_abbreviation(self, team_name: str) -> Optional[str]:
        """
        Map team name to abbreviation.

        Args:
            team_name: Full team name

        Returns:
            Team abbreviation or None
        """
        # Map of BallDontLie team names to NBA abbreviations
        team_map = {
            'Atlanta Hawks': 'ATL',
            'Boston Celtics': 'BOS',
            'Brooklyn Nets': 'BKN',
            'Charlotte Hornets': 'CHA',
            'Chicago Bulls': 'CHI',
            'Cleveland Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL',
            'Denver Nuggets': 'DEN',
            'Detroit Pistons': 'DET',
            'Golden State Warriors': 'GSW',
            'Houston Rockets': 'HOU',
            'Indiana Pacers': 'IND',
            'LA Clippers': 'LAC',
            'Los Angeles Lakers': 'LAL',
            'Memphis Grizzlies': 'MEM',
            'Miami Heat': 'MIA',
            'Milwaukee Bucks': 'MIL',
            'Minnesota Timberwolves': 'MIN',
            'New Orleans Pelicans': 'NOP',
            'New York Knicks': 'NYK',
            'Oklahoma City Thunder': 'OKC',
            'Orlando Magic': 'ORL',
            'Philadelphia 76ers': 'PHI',
            'Phoenix Suns': 'PHX',
            'Portland Trail Blazers': 'POR',
            'Sacramento Kings': 'SAC',
            'San Antonio Spurs': 'SAS',
            'Toronto Raptors': 'TOR',
            'Utah Jazz': 'UTA',
            'Washington Wizards': 'WAS'
        }
        return team_map.get(team_name)
