"""NBA API Client for fetching game data using Ball Don't Lie API."""
import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import time
import yaml

from src.utils.logger import get_logger
from src.utils.cache import DateBasedCache

logger = get_logger(__name__)


class NBAAPIError(Exception):
    """Custom exception for NBA API errors."""
    pass


class NBAClient:
    """Client for interacting with Ball Don't Lie API."""

    BASE_URL = "https://api.balldontlie.io/v1"

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize the NBA client.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                cache_config = config.get('cache', {})
                nba_config = config.get('nba_api', {})
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            cache_config = {}
            nba_config = {}

        # Get API key from environment variable first, then config file
        self.api_key = os.getenv('BALLDONTLIE_API_KEY') or nba_config.get('api_key')
        if not self.api_key:
            raise NBAAPIError(
                "Ball Don't Lie API key not found. "
                "Set BALLDONTLIE_API_KEY environment variable or configure in config.yaml"
            )

        # Initialize session with API key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.api_key,
            'Accept': 'application/json'
        })

        # Initialize date-based cache
        cache_enabled = cache_config.get('enabled', True)
        cache_dir = cache_config.get('directory', '/tmp/nba_cache')
        self.scoreboard_ttl_days = cache_config.get('scoreboard_ttl_days', 30)
        self.game_details_ttl_days = cache_config.get('game_details_ttl_days', 30)
        self.star_players_ttl_days = cache_config.get('star_players_ttl_days', 7)  # Refresh weekly
        self.game_stats_ttl_days = cache_config.get('game_stats_ttl_days', 30)  # Cache stats for 30 days

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
        self.CACHE_DURATION = 86400  # 24 hours

        # Rate limiting: Track API call timestamps per endpoint (sliding window)
        self._api_call_timestamps: Dict[str, List[datetime]] = {}
        self.API_RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes
        self.API_RATE_LIMIT_MAX_CALLS = 120  # Max calls per 10-minute window

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
            # Increased delay to avoid rate limiting (Ball Don't Lie has 100 requests/min limit)
            # 1 second ensures we stay well under the limit
            time.sleep(1.0)

        return games

    def _get_game_star_players_count(self, game_id: str) -> int:
        """
        Get count of star players who played in a specific game.

        Args:
            game_id: The game ID

        Returns:
            Count of star players in the game
        """
        # Check file-based cache first (persistent across restarts)
        if self.cache:
            cached_stats = self.cache.get_game_stats(game_id, self.game_stats_ttl_days)
            if cached_stats is not None:
                star_count = cached_stats.get('star_players_count', 0)
                logger.debug(f"Using cached star player count for game {game_id}: {star_count}")
                return star_count

        # Check rate limiting before making API call
        if self._is_rate_limited('stats'):
            stats = self._get_rate_limit_stats('stats')
            logger.info(f"Rate limited for stats endpoint ({stats['calls_made']}/{stats['max_calls']} calls used). Skipping star player count for game {game_id}.")
            return 0

        try:
            url = f"{self.BASE_URL}/stats"
            params = {
                'game_ids[]': game_id,
                'per_page': 100  # Max allowed
            }

            logger.debug(f"Fetching player stats for game {game_id}...")
            response = self.session.get(url, params=params, timeout=10)

            # Handle rate limiting gracefully
            if response.status_code == 429:
                logger.warning(f"Rate limited while fetching stats for game {game_id}, returning 0")
                return 0

            response.raise_for_status()
            data = response.json()

            # Update rate limit timestamp after successful API call
            self._update_rate_limit_timestamp('stats')

            # Get unique player names from the stats
            players_in_game = set()
            for stat in data.get('data', []):
                player = stat.get('player', {})
                first_name = player.get('first_name', '')
                last_name = player.get('last_name', '')
                full_name = f"{first_name} {last_name}".strip()
                if full_name:
                    players_in_game.add(full_name)

            # Count how many are star players
            star_players = self.STAR_PLAYERS
            star_count = len(players_in_game & star_players)

            if star_count > 0:
                logger.info(f"Game {game_id} has {star_count} star player(s): {players_in_game & star_players}")

            # Cache the game stats for future use
            if self.cache:
                self.cache.set_game_stats(game_id, {
                    'star_players_count': star_count,
                    'players_in_game': list(players_in_game),
                    'star_players_in_game': list(players_in_game & star_players)
                })

            return star_count

        except Exception as e:
            logger.warning(f"Error fetching star players count for game {game_id}: {e}")
            # Return 0 on error to not break the flow
            return 0

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
                # If we have cached data and we're rate limited, return cached data
                if self._is_rate_limited('scoreboard'):
                    stats = self._get_rate_limit_stats('scoreboard')
                    logger.info(f"Rate limited ({stats['calls_made']}/{stats['max_calls']} calls used). Returning cached scoreboard data for {game_date}.")
                return cached_games

        # Check rate limiting before making API call
        if self._is_rate_limited('scoreboard'):
            stats = self._get_rate_limit_stats('scoreboard')
            logger.warning(f"Rate limited ({stats['calls_made']}/{stats['max_calls']} calls used, window resets at {stats['window_resets_at']}) and no cached data available for {game_date}.")
            # Return empty list if no cache and rate limited
            return []

        # Not rate limited - fetch from API with retry logic
        max_retries = 3
        retry_delay = 2  # Initial retry delay in seconds

        for attempt in range(max_retries):
            try:
                url = f"{self.BASE_URL}/games"
                params = {
                    'start_date': game_date,
                    'end_date': game_date
                }

                logger.info(f"Fetching games for {game_date} from Ball Don't Lie API (attempt {attempt + 1}/{max_retries})...")
                response = self.session.get(url, params=params, timeout=10)

                # Handle rate limiting and temporary server errors with exponential backoff
                if response.status_code in [429, 503, 504]:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        status_msg = {429: "Rate limited", 503: "Service unavailable", 504: "Gateway timeout"}
                        logger.warning(f"{status_msg.get(response.status_code, 'Error')} ({response.status_code}). Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Failed after {max_retries} attempts (status {response.status_code})")
                        response.raise_for_status()

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
                    game_id = str(game.get('id'))

                    # Fetch star players count for this game
                    star_players_count = self._get_game_star_players_count(game_id)

                    game_info = {
                        'game_id': game_id,
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
                        # Note: Ball Don't Lie doesn't provide play-by-play data
                        # so we can't calculate actual lead changes
                        'star_players_count': star_players_count
                    }

                    games.append(game_info)

                    # Small delay between stats requests to avoid rate limiting
                    if star_players_count > 0:
                        time.sleep(0.5)

                # Store in cache
                if self.cache and games:
                    self.cache.set_scoreboard(game_date, games)

                # Update rate limit timestamp after successful API call
                self._update_rate_limit_timestamp('scoreboard')

                return games

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Already handled above, but if we get here on last attempt, re-raise
                    logger.error(f"Error fetching games for {game_date} from Ball Don't Lie: {e}")
                    raise NBAAPIError(f"Failed to fetch games for {game_date}: Rate limited") from e
                else:
                    logger.error(f"Error fetching games for {game_date} from Ball Don't Lie: {e}")
                    raise NBAAPIError(f"Failed to fetch games for {game_date}: {e}") from e
            except Exception as e:
                logger.error(f"Error fetching games for {game_date} from Ball Don't Lie: {e}")
                raise NBAAPIError(f"Failed to fetch games for {game_date}: {e}") from e

        # This should not be reached, but just in case
        raise NBAAPIError(f"Failed to fetch games for {game_date} after {max_retries} attempts")

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self._cache_timestamp is None:
            return False
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self.CACHE_DURATION

    def _clean_old_timestamps(self, endpoint_key: str) -> None:
        """
        Remove timestamps older than the rate limit window.

        Args:
            endpoint_key: Identifier for the endpoint
        """
        if endpoint_key not in self._api_call_timestamps:
            return

        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.API_RATE_LIMIT_WINDOW_SECONDS)

        # Keep only timestamps within the window
        self._api_call_timestamps[endpoint_key] = [
            ts for ts in self._api_call_timestamps[endpoint_key]
            if ts > cutoff_time
        ]

    def _is_rate_limited(self, endpoint_key: str) -> bool:
        """
        Check if we're rate limited for a specific endpoint using sliding window.

        Args:
            endpoint_key: Identifier for the endpoint (e.g., 'scoreboard', 'standings', 'leaders')

        Returns:
            True if rate limited (120 calls in last 10 minutes), False otherwise
        """
        # Clean up old timestamps first
        self._clean_old_timestamps(endpoint_key)

        # Check if we've hit the limit
        if endpoint_key not in self._api_call_timestamps:
            return False

        call_count = len(self._api_call_timestamps[endpoint_key])
        return call_count >= self.API_RATE_LIMIT_MAX_CALLS

    def _update_rate_limit_timestamp(self, endpoint_key: str) -> None:
        """Add current timestamp to the rate limit tracker."""
        if endpoint_key not in self._api_call_timestamps:
            self._api_call_timestamps[endpoint_key] = []

        self._api_call_timestamps[endpoint_key].append(datetime.now())

    def _get_rate_limit_stats(self, endpoint_key: str) -> Dict[str, any]:
        """
        Get rate limit statistics for an endpoint.

        Args:
            endpoint_key: Identifier for the endpoint

        Returns:
            Dictionary with rate limit stats (calls_made, calls_remaining, window_resets_at)
        """
        self._clean_old_timestamps(endpoint_key)

        calls_made = 0
        oldest_timestamp = None

        if endpoint_key in self._api_call_timestamps:
            calls_made = len(self._api_call_timestamps[endpoint_key])
            if calls_made > 0:
                oldest_timestamp = min(self._api_call_timestamps[endpoint_key])

        calls_remaining = max(0, self.API_RATE_LIMIT_MAX_CALLS - calls_made)

        # Calculate when the window resets (when oldest call expires)
        window_resets_at = None
        if oldest_timestamp:
            window_resets_at = oldest_timestamp + timedelta(seconds=self.API_RATE_LIMIT_WINDOW_SECONDS)

        return {
            'calls_made': calls_made,
            'calls_remaining': calls_remaining,
            'max_calls': self.API_RATE_LIMIT_MAX_CALLS,
            'window_seconds': self.API_RATE_LIMIT_WINDOW_SECONDS,
            'window_resets_at': window_resets_at.isoformat() if window_resets_at else None
        }

    def _fetch_top_teams(self) -> Set[str]:
        """
        Get top 5 teams based on current standings from NBA official API.
        Try once, fallback to static list if it fails (API is unreliable).

        Returns:
            Set of team abbreviations for top 5 teams
        """
        # Fallback static list (current top teams as of 2024-25 season)
        fallback_teams = {'BOS', 'CLE', 'OKC', 'NYK', 'DEN'}

        try:
            # Get current season string (e.g., "2024-25")
            now = datetime.now()
            if now.month >= 10:  # Season starts in October
                season_year = now.year
            else:
                season_year = now.year - 1
            season_str = f"{season_year}-{str(season_year + 1)[-2:]}"

            # NBA official stats API endpoint
            url = "https://stats.nba.com/stats/leaguestandingsv3"
            params = {
                'LeagueID': '00',
                'Season': season_str,
                'SeasonType': 'Regular Season'
            }

            # NBA API requires specific headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.nba.com/',
                'Origin': 'https://www.nba.com',
                'Accept': 'application/json'
            }

            logger.info(f"Attempting to fetch standings for {season_str} season from NBA official API...")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse standings data
            result_sets = data.get('resultSets', [])
            if not result_sets:
                logger.warning("No result sets in NBA API response, using fallback")
                return fallback_teams

            standings_data = result_sets[0]
            headers_list = standings_data.get('headers', [])
            rows = standings_data.get('rowSet', [])

            if not rows:
                logger.warning("No standings rows in NBA API response, using fallback")
                return fallback_teams

            # Find indices for team abbreviation and win percentage
            try:
                team_abbr_idx = headers_list.index('TeamSlug')
                win_pct_idx = headers_list.index('WinPCT')
            except ValueError:
                logger.warning("Could not find required columns in NBA API response, using fallback")
                return fallback_teams

            # Sort by win percentage and get top 5
            sorted_teams = sorted(rows, key=lambda x: x[win_pct_idx], reverse=True)
            top_5 = {row[team_abbr_idx] for row in sorted_teams[:5]}

            logger.info(f"Successfully fetched top 5 teams from NBA API: {top_5}")
            return top_5

        except Exception as e:
            logger.warning(f"Error fetching standings from NBA official API: {e}")
            logger.info(f"Using fallback top teams: {fallback_teams}")
            return fallback_teams

    def _fetch_star_players(self) -> Set[str]:
        """
        Get star players based on season leaders from Ball Don't Lie API.

        Returns:
            Set of star player names (top 30 scorers)
        """
        # Get current season
        now = datetime.now()
        if now.month >= 10:  # Season starts in October
            season = now.year
        else:
            season = now.year - 1

        # Check file-based cache first (persistent across restarts)
        if self.cache:
            cached_players = self.cache.get_star_players(season, self.star_players_ttl_days)
            if cached_players is not None:
                logger.info(f"Using cached star players for season {season}")
                return set(cached_players)

        # Check rate limiting before making API call
        if self._is_rate_limited('leaders'):
            stats = self._get_rate_limit_stats('leaders')
            logger.info(f"Rate limited ({stats['calls_made']}/{stats['max_calls']} calls used). Returning cached star players.")
            # Return cached data if available, otherwise use fallback
            if self._star_players_cache is not None:
                return self._star_players_cache
            logger.warning(f"No cached data available, using fallback defaults. Window resets at {stats['window_resets_at']}")
            return {
                'LeBron James', 'Stephen Curry', 'Kevin Durant', 'Giannis Antetokounmpo',
                'Luka Doncic', 'Nikola Jokic', 'Joel Embiid', 'Jayson Tatum',
                'Damian Lillard', 'Anthony Davis', 'Devin Booker', 'Kawhi Leonard',
                'Jimmy Butler', 'Donovan Mitchell', 'Trae Young', 'Kyrie Irving',
                'Shai Gilgeous-Alexander', 'Anthony Edwards', 'Tyrese Haliburton'
            }

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                url = f"{self.BASE_URL}/leaders"
                params = {
                    'season': season,
                    'stat_type': 'pts'  # Points per game leaders
                }

                logger.info(f"Fetching season leaders for {season} (attempt {attempt + 1}/{max_retries})...")
                response = self.session.get(url, params=params, timeout=10)

                # Handle rate limiting and temporary server errors
                if response.status_code in [429, 503, 504]:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        status_msg = {429: "Rate limited", 503: "Service unavailable", 504: "Gateway timeout"}
                        logger.warning(f"{status_msg.get(response.status_code, 'Error')} ({response.status_code}). Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue

                response.raise_for_status()
                data = response.json()

                # Get top 30 scorers
                leaders = data.get('data', [])
                star_players = set()
                for leader in leaders[:30]:
                    player = leader.get('player', {})
                    first_name = player.get('first_name', '')
                    last_name = player.get('last_name', '')
                    full_name = f"{first_name} {last_name}".strip()
                    if full_name:
                        star_players.add(full_name)

                logger.info(f"Fetched {len(star_players)} star players from season leaders")

                # Update rate limit timestamp after successful API call
                self._update_rate_limit_timestamp('leaders')

                # Cache the star players for future use
                if self.cache:
                    self.cache.set_star_players(season, list(star_players))

                return star_players

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Error fetching star players (attempt {attempt + 1}): {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Error fetching star players after {max_retries} attempts: {e}")
                    logger.warning("Using fallback default star players")
                    # Fallback to well-known players
                    return {
                        'LeBron James', 'Stephen Curry', 'Kevin Durant', 'Giannis Antetokounmpo',
                        'Luka Doncic', 'Nikola Jokic', 'Joel Embiid', 'Jayson Tatum',
                        'Damian Lillard', 'Anthony Davis', 'Devin Booker', 'Kawhi Leonard',
                        'Jimmy Butler', 'Donovan Mitchell', 'Trae Young', 'Kyrie Irving',
                        'Shai Gilgeous-Alexander', 'Anthony Edwards', 'Tyrese Haliburton'
                    }

        # Fallback if all retries failed
        return {
            'LeBron James', 'Stephen Curry', 'Kevin Durant', 'Giannis Antetokounmpo',
            'Luka Doncic', 'Nikola Jokic', 'Joel Embiid', 'Jayson Tatum',
            'Damian Lillard', 'Anthony Davis', 'Devin Booker', 'Kawhi Leonard',
            'Jimmy Butler', 'Donovan Mitchell', 'Trae Young', 'Kyrie Irving',
            'Shai Gilgeous-Alexander', 'Anthony Edwards', 'Tyrese Haliburton'
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
