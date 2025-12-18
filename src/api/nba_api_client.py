"""NBA API Client using nba_api library with SQLite caching.

This client fetches data from NBA.com via the nba_api library and stores
it in a local SQLite database to minimize API calls and avoid rate limiting.
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import yaml

from src.utils.logger import get_logger
from src.utils.database import NBADatabase

logger = get_logger(__name__)

# Delay between API calls to avoid rate limiting (in seconds)
API_DELAY = 0.6  # 600ms between calls

# Fallback data when API is unavailable
FALLBACK_TOP_TEAMS = {"CLE", "BOS", "OKC", "HOU", "MEM"}
FALLBACK_STAR_PLAYERS = {
    "LeBron James",
    "Stephen Curry",
    "Kevin Durant",
    "Giannis Antetokounmpo",
    "Luka Doncic",
    "Nikola Jokic",
    "Joel Embiid",
    "Jayson Tatum",
    "Damian Lillard",
    "Anthony Davis",
    "Devin Booker",
    "Kawhi Leonard",
    "Jimmy Butler",
    "Donovan Mitchell",
    "Trae Young",
    "Kyrie Irving",
    "Shai Gilgeous-Alexander",
    "Anthony Edwards",
    "Tyrese Haliburton",
    "Ja Morant",
    "Jaylen Brown",
    "De'Aaron Fox",
    "Domantas Sabonis",
    "Bam Adebayo",
    "Pascal Siakam",
    "Paolo Banchero",
    "Chet Holmgren",
    "Victor Wembanyama",
    "Lauri Markkanen",
    "Jalen Brunson",
}


class NBAAPIError(Exception):
    """Custom exception for NBA API errors."""

    pass


class NBAClient:
    """Client for fetching NBA data using nba_api with SQLite caching."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the NBA client.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                self.db_config = config.get("database", {})
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            self.db_config = {}

        # Initialize database
        db_path = self.db_config.get("path", "data/nba_games.db")
        self.db = NBADatabase(db_path=db_path)

        # Cache for runtime data
        self._top_teams_cache: Optional[Set[str]] = None
        self._star_players_cache: Optional[Set[str]] = None

        # Load cached data from DB on startup
        self._load_cached_metadata()

    def _load_cached_metadata(self):
        """Load top teams and star players from database."""
        # Load top teams from standings
        top_teams = self.db.get_top_teams(5)
        if top_teams:
            self._top_teams_cache = set(top_teams)
            logger.info(f"Loaded top teams from DB: {self._top_teams_cache}")
        else:
            self._top_teams_cache = FALLBACK_TOP_TEAMS
            logger.info(f"Using fallback top teams: {self._top_teams_cache}")

        # Load star players from database
        star_players = self.db.get_star_players()
        if star_players:
            self._star_players_cache = set(star_players)
            logger.info(f"Loaded {len(self._star_players_cache)} star players from DB")
        else:
            self._star_players_cache = FALLBACK_STAR_PLAYERS
            logger.info(
                f"Using fallback star players: {len(self._star_players_cache)} players"
            )

    def get_games_last_n_days(self, days: int = 7) -> List[Dict]:
        """
        Fetch all completed games from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of game dictionaries with detailed information
        """
        # Start from yesterday to avoid checking today's incomplete games
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # Try to get from database first
        db_games = self.db.get_games_in_range(start_str, end_str)

        if db_games:
            logger.info(
                f"Found {len(db_games)} games in database for {start_str} to {end_str}"
            )
            return self._format_games_from_db(db_games)

        # If no games in DB, we need to sync first
        logger.warning(f"No games found in database for {start_str} to {end_str}")
        logger.warning("Run 'sync' command to populate the database first")
        return []

    def _format_games_from_db(self, db_games: List[Dict]) -> List[Dict]:
        """Format database game records to match expected output format."""
        games = []
        for game in db_games:
            game_id = game["game_id"]

            # Get star player count for this game
            star_count = self.db.get_star_players_in_game(game_id)

            home_score = game["home_score"] or 0
            away_score = game["away_score"] or 0

            game_info = {
                "game_id": game_id,
                "game_date": game["game_date"],
                "home_team": {
                    "name": game["home_name"],
                    "abbr": game["home_abbr"],
                    "score": home_score,
                },
                "away_team": {
                    "name": game["away_name"],
                    "abbr": game["away_abbr"],
                    "score": away_score,
                },
                "total_points": home_score + away_score,
                "final_margin": abs(home_score - away_score),
                "star_players_count": star_count,
            }
            games.append(game_info)

        return games

    @property
    def TOP_5_TEAMS(self) -> Set[str]:
        """Get top 5 teams."""
        if self._top_teams_cache is None:
            self._load_cached_metadata()
        return self._top_teams_cache or FALLBACK_TOP_TEAMS

    @property
    def STAR_PLAYERS(self) -> Set[str]:
        """Get star players."""
        if self._star_players_cache is None:
            self._load_cached_metadata()
        return self._star_players_cache or FALLBACK_STAR_PLAYERS

    def is_top5_team(self, team_abbr: str) -> bool:
        """Check if a team is in the top 5."""
        return team_abbr in self.TOP_5_TEAMS


class NBASyncService:
    """Service to sync NBA data from nba_api to local SQLite database."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the sync service.

        Args:
            config_path: Path to configuration file
        """
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                self.db_config = config.get("database", {})
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            self.db_config = {}

        db_path = self.db_config.get("path", "data/nba_games.db")
        self.db = NBADatabase(db_path=db_path)

    def _get_current_season(self) -> str:
        """Get current NBA season string (e.g., '2024-25')."""
        now = datetime.now()
        if now.month >= 10:  # Season starts in October
            year = now.year
        else:
            year = now.year - 1
        return f"{year}-{str(year + 1)[-2:]}"

    def sync_teams(self) -> int:
        """
        Sync all NBA teams to database.

        Returns:
            Number of teams synced
        """
        from nba_api.stats.static import teams as nba_teams

        logger.info("Syncing NBA teams...")
        all_teams = nba_teams.get_teams()

        for team in all_teams:
            self.db.upsert_team(
                team_id=team["id"],
                abbreviation=team["abbreviation"],
                full_name=team["full_name"],
                city=team["city"],
                conference=team.get("conference"),
                division=team.get("division"),
            )

        self.db.set_last_sync("teams", f"Synced {len(all_teams)} teams")
        logger.info(f"Synced {len(all_teams)} teams")
        return len(all_teams)

    def sync_standings(self) -> int:
        """
        Sync current standings to database.

        Returns:
            Number of standings entries synced
        """
        from nba_api.stats.endpoints import leaguestandingsv3

        logger.info("Syncing standings...")
        season = self._get_current_season()

        try:
            time.sleep(API_DELAY)
            standings = leaguestandingsv3.LeagueStandingsV3(
                season=season, season_type="Regular Season"
            )
            df = standings.get_data_frames()[0]

            count = 0
            for _, row in df.iterrows():
                self.db.upsert_standings(
                    team_id=row["TeamID"],
                    team_abbr=row["TeamSlug"].upper(),
                    season=int(season.split("-")[0]),
                    wins=row["WINS"],
                    losses=row["LOSSES"],
                    win_pct=row["WinPCT"],
                    conf_rank=row["ConferenceRank"] if "ConferenceRank" in row else 0,
                )
                count += 1

            self.db.set_last_sync("standings", f"Synced {count} standings for {season}")
            logger.info(f"Synced {count} standings for {season}")
            return count

        except Exception as e:
            logger.error(f"Error syncing standings: {e}")
            return 0

    def sync_star_players(self, top_n: int = 30) -> int:
        """
        Sync star players (top scorers) to database.

        Args:
            top_n: Number of top scorers to mark as stars

        Returns:
            Number of star players synced
        """
        from nba_api.stats.endpoints import leagueleaders

        logger.info(f"Syncing top {top_n} scorers as star players...")
        season = self._get_current_season()

        try:
            time.sleep(API_DELAY)
            leaders = leagueleaders.LeagueLeaders(
                season=season, stat_category_abbreviation="PTS", per_mode48="PerGame"
            )
            df = leaders.get_data_frames()[0]

            star_names = []
            for _, row in df.head(top_n).iterrows():
                player_name = row["PLAYER"]
                star_names.append(player_name)

                # Upsert player
                self.db.upsert_player(
                    player_id=row["PLAYER_ID"],
                    first_name=player_name.split()[0]
                    if " " in player_name
                    else player_name,
                    last_name=" ".join(player_name.split()[1:])
                    if " " in player_name
                    else "",
                    team_id=row["TEAM_ID"],
                    is_star=True,
                    ppg=row["PTS"],
                )

            # Mark these players as stars
            self.db.set_star_players(star_names)

            self.db.set_last_sync(
                "star_players", f"Synced {len(star_names)} star players for {season}"
            )
            logger.info(f"Synced {len(star_names)} star players")
            return len(star_names)

        except Exception as e:
            logger.error(f"Error syncing star players: {e}")
            return 0

    def sync_games(self, days: int = 14) -> int:
        """
        Sync games from the last N days to database.

        Uses LeagueGameFinder which is more reliable than scoreboardv2.

        Args:
            days: Number of days to sync

        Returns:
            Number of games synced
        """
        from nba_api.stats.endpoints import leaguegamefinder

        logger.info(f"Syncing games for the last {days} days...")

        # Calculate date range
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        try:
            time.sleep(API_DELAY)
            # Get current season
            season = self._get_current_season()

            # Fetch all completed games for the season
            finder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                season_type_nullable="Regular Season",
            )
            games_df = finder.get_data_frames()[0]

            if games_df.empty:
                logger.warning("No games found from LeagueGameFinder")
                return 0

            # Filter to date range
            games_df["GAME_DATE"] = games_df["GAME_DATE"].astype(str)
            games_df = games_df[
                (games_df["GAME_DATE"] >= start_str)
                & (games_df["GAME_DATE"] <= end_str)
            ]

            # LeagueGameFinder returns 2 rows per game (one per team)
            # Group by GAME_ID to get unique games
            unique_games = games_df.drop_duplicates("GAME_ID")
            logger.info(f"Found {len(unique_games)} games in date range")

            # Get season year for database
            now = datetime.now()
            season_year = now.year if now.month >= 10 else now.year - 1

            count = 0
            for _, game in unique_games.iterrows():
                game_id = str(game["GAME_ID"])
                game_date = game["GAME_DATE"]

                # Skip if already in database
                if self.db.has_games_for_date(game_date):
                    existing = self.db.get_games_for_date(game_date)
                    if any(g["game_id"] == game_id for g in existing):
                        continue

                # Parse matchup to get teams (e.g., "LAL vs. BOS" or "LAL @ BOS")
                matchup = game["MATCHUP"]
                team_abbr = game["TEAM_ABBREVIATION"]
                pts = game["PTS"]

                # Get the other team's row for this game
                other_team = games_df[
                    (games_df["GAME_ID"] == game_id)
                    & (games_df["TEAM_ABBREVIATION"] != team_abbr)
                ]

                if other_team.empty:
                    continue

                other_abbr = other_team.iloc[0]["TEAM_ABBREVIATION"]
                other_pts = other_team.iloc[0]["PTS"]

                # Determine home vs away from matchup format
                if " vs. " in matchup:
                    # Team is home
                    home_abbr, away_abbr = team_abbr, other_abbr
                    home_score, away_score = pts, other_pts
                else:
                    # Team is away (@ format)
                    home_abbr, away_abbr = other_abbr, team_abbr
                    home_score, away_score = other_pts, pts

                # Get team IDs
                home_team = self.db.get_team_by_abbr(home_abbr)
                away_team = self.db.get_team_by_abbr(away_abbr)

                if not home_team or not away_team:
                    logger.debug(f"Team not found: {home_abbr} or {away_abbr}")
                    continue

                self.db.upsert_game(
                    game_id=game_id,
                    game_date=game_date,
                    home_team_id=home_team["id"],
                    away_team_id=away_team["id"],
                    home_score=int(home_score),
                    away_score=int(away_score),
                    status="Final",
                    season=season_year,
                )
                count += 1

            self.db.set_last_sync("games", f"Synced {count} games for last {days} days")
            logger.info(f"Total games synced: {count}")
            return count

        except Exception as e:
            logger.error(f"Error syncing games: {e}")
            return 0

    def _sync_games_for_date(self, game_date: str) -> int:
        """
        Sync games for a specific date.

        Args:
            game_date: Date in YYYY-MM-DD format

        Returns:
            Number of games synced
        """
        from nba_api.stats.endpoints import scoreboardv2

        # Check if we already have games for this date
        if self.db.has_games_for_date(game_date):
            logger.debug(f"Games for {game_date} already in database, skipping")
            return 0

        try:
            time.sleep(API_DELAY)
            # Convert date format for NBA API (MM/DD/YYYY)
            date_parts = game_date.split("-")
            nba_date = f"{date_parts[1]}/{date_parts[2]}/{date_parts[0]}"

            scoreboard = scoreboardv2.ScoreboardV2(game_date=nba_date)
            dfs = scoreboard.get_data_frames()
            games_df = dfs[0]  # GameHeader
            line_score_df = dfs[1]  # LineScore (has actual scores)

            if games_df.empty:
                logger.debug(f"No games found for {game_date}")
                return 0

            # Build score lookup from LineScore
            # LineScore has 2 rows per game (home and away team)
            scores = {}
            for _, row in line_score_df.iterrows():
                gid = str(row["GAME_ID"])
                tid = row["TEAM_ID"]
                pts = row.get("PTS") or 0
                if gid not in scores:
                    scores[gid] = {}
                scores[gid][tid] = pts

            # Get current season year
            now = datetime.now()
            season_year = now.year if now.month >= 10 else now.year - 1

            count = 0
            for _, game in games_df.iterrows():
                # Only sync completed games
                game_status = game.get("GAME_STATUS_TEXT", "")
                if "Final" not in game_status:
                    continue

                game_id = str(game["GAME_ID"])
                home_team_id = game["HOME_TEAM_ID"]
                away_team_id = game["VISITOR_TEAM_ID"]

                # Get scores from LineScore lookup
                game_scores = scores.get(game_id, {})
                home_score = game_scores.get(home_team_id, 0)
                away_score = game_scores.get(away_team_id, 0)

                self.db.upsert_game(
                    game_id=game_id,
                    game_date=game_date,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_score=home_score,
                    away_score=away_score,
                    status="Final",
                    season=season_year,
                )
                count += 1

                # Sync player stats for this game
                self._sync_game_players(game_id)

            logger.info(f"Synced {count} games for {game_date}")
            return count

        except Exception as e:
            logger.warning(f"Error syncing games for {game_date}: {e}")
            return 0

    def _sync_game_players(self, game_id: str):
        """
        Sync player stats for a specific game.

        Args:
            game_id: NBA game ID
        """
        from nba_api.stats.endpoints import boxscoretraditionalv2

        # Skip if we already have player data for this game
        if self.db.has_game_players(game_id):
            return

        try:
            time.sleep(API_DELAY)
            boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
            players_df = boxscore.get_data_frames()[0]  # PlayerStats

            for _, player in players_df.iterrows():
                player_name = player["PLAYER_NAME"]
                self.db.upsert_game_player(
                    game_id=game_id,
                    player_id=player["PLAYER_ID"],
                    player_name=player_name,
                    team_id=player["TEAM_ID"],
                    points=player.get("PTS") or 0,
                    rebounds=player.get("REB") or 0,
                    assists=player.get("AST") or 0,
                )

                # Also upsert the player to players table
                name_parts = player_name.split(" ", 1)
                self.db.upsert_player(
                    player_id=player["PLAYER_ID"],
                    first_name=name_parts[0],
                    last_name=name_parts[1] if len(name_parts) > 1 else "",
                    team_id=player["TEAM_ID"],
                )

        except Exception as e:
            logger.warning(f"Error syncing players for game {game_id}: {e}")

    def sync_all(self, days: int = 14) -> Dict[str, int]:
        """
        Sync all data: teams, standings, star players, and games.

        Args:
            days: Number of days of games to sync

        Returns:
            Dictionary with sync counts
        """
        logger.info("Starting full sync...")

        results = {
            "teams": self.sync_teams(),
            "standings": self.sync_standings(),
            "star_players": self.sync_star_players(),
            "games": self.sync_games(days),
        }

        logger.info(f"Full sync complete: {results}")
        return results

    def get_sync_status(self) -> Dict[str, any]:
        """Get current sync status and database stats."""
        stats = self.db.get_stats()

        # Add last sync times
        for sync_type in ["teams", "standings", "star_players", "games"]:
            last_sync = self.db.get_last_sync(sync_type)
            stats[f"last_{sync_type}_sync"] = (
                last_sync.isoformat() if last_sync else None
            )

        return stats
