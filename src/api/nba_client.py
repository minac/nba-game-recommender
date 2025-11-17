"""NBA API Client for fetching game data."""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import time
import yaml

from src.utils.logger import get_logger
from src.utils.cache import DateBasedCache

logger = get_logger(__name__)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                except Exception as e:
                    # Don't retry on other exceptions
                    raise
            return None
        return wrapper
    return decorator


class NBAClient:
    """Client for interacting with NBA stats API."""

    BASE_URL = "https://stats.nba.com/stats"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://stats.nba.com/',
        'Origin': 'https://stats.nba.com'
    }

    # Cache duration in seconds (24 hours)
    CACHE_DURATION = 86400

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize the NBA client.

        Args:
            config_path: Path to configuration file
        """
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        # Load configuration
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                cache_config = config.get('cache', {})
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            cache_config = {}

        # Initialize date-based cache
        cache_enabled = cache_config.get('enabled', True)
        cache_dir = cache_config.get('directory', '/tmp/nba_cache')
        self.scoreboard_ttl_days = cache_config.get('scoreboard_ttl_days', 30)
        self.game_details_ttl_days = cache_config.get('game_details_ttl_days', 30)

        if cache_enabled:
            self.cache = DateBasedCache(cache_dir=cache_dir)
            logger.info(f"Date-based cache enabled: {cache_dir}")

            # Auto cleanup expired cache if configured
            if cache_config.get('auto_cleanup', True):
                self.cache.clear_expired()
        else:
            self.cache = None
            logger.info("Cache disabled")

        # Cache for dynamic data (top teams and star players)
        self._top_teams_cache: Optional[Set[str]] = None
        self._star_players_cache: Optional[Set[str]] = None
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
        # Check cache first
        if self.cache:
            cached_games = self.cache.get_scoreboard(game_date, ttl_days=self.scoreboard_ttl_days)
            if cached_games is not None:
                return cached_games

        # Cache miss - fetch from API
        try:
            url = f"{self.BASE_URL}/scoreboardv3"
            params = {
                'GameDate': game_date,
                'LeagueID': '00'
            }

            logger.info(f"Fetching scoreboard for {game_date} from API...")
            response = self._make_request(url, params=params)
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

            # Store in cache
            if self.cache and games:
                self.cache.set_scoreboard(game_date, games)

            return games

        except Exception as e:
            logger.error(f"Error fetching scoreboard for {game_date}: {e}")
            return []

    def _get_game_details(self, game_id: str) -> Optional[Dict]:
        """
        Get detailed game information including lead changes.

        Args:
            game_id: NBA game ID

        Returns:
            Dictionary with game details
        """
        # Check cache first
        if self.cache:
            cached_details = self.cache.get_game_details(game_id, ttl_days=self.game_details_ttl_days)
            if cached_details is not None:
                return cached_details

        # Cache miss - fetch from API
        try:
            # Get play-by-play data for lead changes
            url = f"{self.BASE_URL}/playbyplayv3"
            params = {
                'GameID': game_id,
                'EndPeriod': 10,
                'StartPeriod': 1
            }

            logger.debug(f"Fetching game details for {game_id} from API...")
            response = self._make_request(url, params=params)
            response.raise_for_status()
            data = response.json()

            lead_changes = self._calculate_lead_changes(data.get('game', {}).get('actions', []))

            # Get box score for star players
            star_count = self._get_star_players_count(game_id)

            details = {
                'lead_changes': lead_changes,
                'star_players_count': star_count
            }

            # Store in cache
            if self.cache:
                self.cache.set_game_details(game_id, details)

            return details

        except Exception as e:
            logger.error(f"Error fetching game details for {game_id}: {e}")
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
            # NBA API v3 uses 'scoreHome' and 'scoreAway', not 'homeScore'/'awayScore'
            # Try the correct field names first, then fallback to test data format
            home_score = action.get('scoreHome', action.get('homeScore', 0))
            away_score = action.get('scoreAway', action.get('awayScore', 0))

            # Handle case where scores might be strings
            if isinstance(home_score, str):
                home_score = int(home_score) if home_score else 0
            if isinstance(away_score, str):
                away_score = int(away_score) if away_score else 0

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

            response = self._make_request(url, params=params)
            response.raise_for_status()
            data = response.json()

            star_count = 0
            box_score = data.get('boxScoreTraditional', {})

            # Players are nested under homeTeam and awayTeam in v3 API
            home_players = box_score.get('homeTeam', {}).get('players', [])
            away_players = box_score.get('awayTeam', {}).get('players', [])
            all_players = home_players + away_players

            logger.debug(f"Found {len(home_players)} home players and {len(away_players)} away players")

            for player in all_players:
                # NBA Stats API v3 uses firstName and familyName fields, not a single 'name' field
                first_name = player.get('firstName', '')
                family_name = player.get('familyName', '')
                player_name = f"{first_name} {family_name}".strip()

                if player_name in self.STAR_PLAYERS:
                    star_count += 1
                    logger.debug(f"Found star player: {player_name}")

            logger.debug(f"Total star players found in game {game_id}: {star_count}")
            return star_count

        except Exception as e:
            logger.error(f"Error fetching box score for {game_id}: {e}")
            return 0

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _make_request(self, url: str, params: Dict) -> requests.Response:
        """
        Make an HTTP request with retry logic and increased timeout.

        Args:
            url: The URL to request
            params: Query parameters

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: If request fails after retries
        """
        return self.session.get(url, params=params, timeout=30)

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self._cache_timestamp is None:
            return False
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self.CACHE_DURATION

    def _fetch_top_teams(self) -> Set[str]:
        """
        Fetch current top 5 teams by win percentage from standings.

        Returns:
            Set of team abbreviations for top 5 teams
        """
        try:
            # Get current season (e.g., "2024-25")
            now = datetime.now()
            if now.month >= 10:  # Season starts in October
                season = f"{now.year}-{str(now.year + 1)[-2:]}"
            else:
                season = f"{now.year - 1}-{str(now.year)[-2:]}"

            url = f"{self.BASE_URL}/leaguestandingsv3"
            params = {
                'LeagueID': '00',
                'Season': season,
                'SeasonType': 'Regular Season'
            }

            response = self._make_request(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract standings data
            standings = data.get('resultSets', [{}])[0].get('rowSet', [])
            headers = data.get('resultSets', [{}])[0].get('headers', [])

            # Find indices for team abbreviation and win percentage
            team_abbr_idx = headers.index('TeamSlug') if 'TeamSlug' in headers else None
            win_pct_idx = headers.index('WinPCT') if 'WinPCT' in headers else None

            if team_abbr_idx is None or win_pct_idx is None:
                raise ValueError("Required fields not found in standings data")

            # Sort by win percentage and get top 5
            sorted_teams = sorted(standings, key=lambda x: float(x[win_pct_idx]), reverse=True)
            top_5 = {team[team_abbr_idx].upper() for team in sorted_teams[:5]}

            logger.info(f"Dynamically fetched top 5 teams: {top_5}")
            return top_5

        except Exception as e:
            logger.error(f"Error fetching top teams: {e}")
            logger.warning("Using fallback default top teams")
            # Fallback to a reasonable default
            return {'BOS', 'DEN', 'MIL', 'PHX', 'LAL'}

    def _fetch_star_players(self) -> Set[str]:
        """
        Fetch current star players based on league leaders in points per game.

        Returns:
            Set of star player names (top 30 scorers)
        """
        try:
            # Get current season
            now = datetime.now()
            if now.month >= 10:
                season = f"{now.year}-{str(now.year + 1)[-2:]}"
            else:
                season = f"{now.year - 1}-{str(now.year)[-2:]}"

            url = f"{self.BASE_URL}/leagueleaders"
            params = {
                'LeagueID': '00',
                'PerMode': 'PerGame',
                'Scope': 'S',
                'Season': season,
                'SeasonType': 'Regular Season',
                'StatCategory': 'PTS'
            }

            response = self._make_request(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract player data
            players = data.get('resultSet', {}).get('rowSet', [])
            headers = data.get('resultSet', {}).get('headers', [])

            # Find player name index
            player_idx = headers.index('PLAYER') if 'PLAYER' in headers else None

            if player_idx is None:
                raise ValueError("Player field not found in leaders data")

            # Get top 30 scorers
            star_players = {player[player_idx] for player in players[:30]}

            logger.info(f"Dynamically fetched {len(star_players)} star players")
            return star_players

        except Exception as e:
            logger.error(f"Error fetching star players: {e}")
            logger.warning("Using fallback default star players")
            # Fallback to a reasonable default
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
