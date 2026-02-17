"""SQLite database for persistent NBA data storage."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from src.utils.logger import get_logger

logger = get_logger(__name__)


class NBADatabase:
    """SQLite database for NBA game data with intelligent caching."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str = "data/nba_games.db"):
        """
        Initialize the database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # Teams table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY,
                    abbreviation TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    city TEXT,
                    conference TEXT,
                    division TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Players table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    team_id INTEGER,
                    is_star_player INTEGER DEFAULT 0,
                    ppg REAL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams(id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_players_full_name ON players(full_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_players_star ON players(is_star_player)
            """)

            # Games table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    game_date TEXT NOT NULL,
                    home_team_id INTEGER NOT NULL,
                    away_team_id INTEGER NOT NULL,
                    home_score INTEGER,
                    away_score INTEGER,
                    status TEXT,
                    season INTEGER,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (home_team_id) REFERENCES teams(id),
                    FOREIGN KEY (away_team_id) REFERENCES teams(id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_games_season ON games(season)
            """)

            # Game player stats (for star player counting)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_players (
                    game_id TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    player_name TEXT NOT NULL,
                    team_id INTEGER,
                    points INTEGER,
                    rebounds INTEGER,
                    assists INTEGER,
                    PRIMARY KEY (game_id, player_id),
                    FOREIGN KEY (game_id) REFERENCES games(id),
                    FOREIGN KEY (player_id) REFERENCES players(id)
                )
            """)

            # Standings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS standings (
                    team_id INTEGER PRIMARY KEY,
                    team_abbr TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    wins INTEGER,
                    losses INTEGER,
                    win_pct REAL,
                    conference_rank INTEGER,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams(id)
                )
            """)

            # Game buzz scores (AI-generated engagement scores)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_buzz (
                    game_id TEXT PRIMARY KEY,
                    score REAL NOT NULL,
                    reasoning TEXT,
                    scored_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                )
            """)

            # Sync metadata (track when data was last synced)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    sync_type TEXT PRIMARY KEY,
                    last_sync TEXT,
                    sync_details TEXT
                )
            """)

            logger.info(f"Database initialized at {self.db_path}")

    def get_last_sync(self, sync_type: str) -> Optional[datetime]:
        """Get the last sync time for a specific sync type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_sync FROM sync_metadata WHERE sync_type = ?", (sync_type,)
            )
            row = cursor.fetchone()
            if row and row["last_sync"]:
                return datetime.fromisoformat(row["last_sync"])
            return None

    def set_last_sync(self, sync_type: str, details: Optional[str] = None):
        """Update the last sync time for a specific sync type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO sync_metadata (sync_type, last_sync, sync_details)
                VALUES (?, ?, ?)
            """,
                (sync_type, datetime.now().isoformat(), details),
            )

    # Team operations
    def upsert_team(
        self,
        team_id: int,
        abbreviation: str,
        full_name: str,
        city: str = None,
        conference: str = None,
        division: str = None,
    ):
        """Insert or update a team."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO teams
                (id, abbreviation, full_name, city, conference, division, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    team_id,
                    abbreviation,
                    full_name,
                    city,
                    conference,
                    division,
                    datetime.now().isoformat(),
                ),
            )

    def get_team_by_abbr(self, abbreviation: str) -> Optional[Dict]:
        """Get team by abbreviation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM teams WHERE abbreviation = ?", (abbreviation,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_teams(self) -> List[Dict]:
        """Get all teams."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM teams")
            return [dict(row) for row in cursor.fetchall()]

    # Player operations
    def upsert_player(
        self,
        player_id: int,
        first_name: str,
        last_name: str,
        team_id: int = None,
        is_star: bool = False,
        ppg: float = None,
    ):
        """Insert or update a player."""
        full_name = f"{first_name} {last_name}".strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO players
                (id, first_name, last_name, full_name, team_id, is_star_player, ppg, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    player_id,
                    first_name,
                    last_name,
                    full_name,
                    team_id,
                    1 if is_star else 0,
                    ppg,
                    datetime.now().isoformat(),
                ),
            )

    def get_star_players(self) -> List[str]:
        """Get list of star player names."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT full_name FROM players WHERE is_star_player = 1")
            return [row["full_name"] for row in cursor.fetchall()]

    def set_star_players(self, player_names: List[str]):
        """Mark players as stars by name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Reset all star status
            cursor.execute("UPDATE players SET is_star_player = 0")
            # Set new stars
            for name in player_names:
                cursor.execute(
                    "UPDATE players SET is_star_player = 1 WHERE full_name = ?", (name,)
                )

    # Game operations
    def upsert_game(
        self,
        game_id: str,
        game_date: str,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        status: str,
        season: int,
    ):
        """Insert or update a game."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO games
                (id, game_date, home_team_id, away_team_id, home_score, away_score,
                 status, season, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    game_id,
                    game_date,
                    home_team_id,
                    away_team_id,
                    home_score,
                    away_score,
                    status,
                    season,
                    datetime.now().isoformat(),
                ),
            )

    def get_games_for_date(self, game_date: str) -> List[Dict]:
        """Get all games for a specific date with team info."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    g.id as game_id,
                    g.game_date,
                    g.home_score,
                    g.away_score,
                    g.status,
                    g.season,
                    ht.abbreviation as home_abbr,
                    ht.full_name as home_name,
                    at.abbreviation as away_abbr,
                    at.full_name as away_name
                FROM games g
                JOIN teams ht ON g.home_team_id = ht.id
                JOIN teams at ON g.away_team_id = at.id
                WHERE g.game_date = ? AND g.status = 'Final'
            """,
                (game_date,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_games_in_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get all completed games in a date range."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    g.id as game_id,
                    g.game_date,
                    g.home_score,
                    g.away_score,
                    g.status,
                    g.season,
                    ht.abbreviation as home_abbr,
                    ht.full_name as home_name,
                    at.abbreviation as away_abbr,
                    at.full_name as away_name
                FROM games g
                JOIN teams ht ON g.home_team_id = ht.id
                JOIN teams at ON g.away_team_id = at.id
                WHERE g.game_date BETWEEN ? AND ? AND g.status = 'Final'
                ORDER BY g.game_date DESC
            """,
                (start_date, end_date),
            )
            return [dict(row) for row in cursor.fetchall()]

    def has_games_for_date(self, game_date: str) -> bool:
        """Check if we have games cached for a date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM games WHERE game_date = ?", (game_date,)
            )
            row = cursor.fetchone()
            return row["cnt"] > 0

    # Game player stats operations
    def upsert_game_player(
        self,
        game_id: str,
        player_id: int,
        player_name: str,
        team_id: int = None,
        points: int = 0,
        rebounds: int = 0,
        assists: int = 0,
    ):
        """Insert or update a player's stats for a game."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO game_players
                (game_id, player_id, player_name, team_id, points, rebounds, assists)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (game_id, player_id, player_name, team_id, points, rebounds, assists),
            )

    def get_star_players_in_game(self, game_id: str) -> int:
        """Count star players who played in a game."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(DISTINCT gp.player_id) as star_count
                FROM game_players gp
                JOIN players p ON gp.player_id = p.id
                WHERE gp.game_id = ? AND p.is_star_player = 1
            """,
                (game_id,),
            )
            row = cursor.fetchone()
            return row["star_count"] if row else 0

    def has_game_players(self, game_id: str) -> bool:
        """Check if we have player stats for a game."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM game_players WHERE game_id = ?", (game_id,)
            )
            row = cursor.fetchone()
            return row["cnt"] > 0

    # Standings operations
    def upsert_standings(
        self,
        team_id: int,
        team_abbr: str,
        season: int,
        wins: int,
        losses: int,
        win_pct: float,
        conf_rank: int,
    ):
        """Insert or update team standings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO standings
                (team_id, team_abbr, season, wins, losses, win_pct, conference_rank, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    team_id,
                    team_abbr,
                    season,
                    wins,
                    losses,
                    win_pct,
                    conf_rank,
                    datetime.now().isoformat(),
                ),
            )

    def get_top_teams(self, top_n: int = 5) -> List[str]:
        """Get top N teams by win percentage."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT team_abbr FROM standings
                ORDER BY win_pct DESC
                LIMIT ?
            """,
                (top_n,),
            )
            return [row["team_abbr"] for row in cursor.fetchall()]

    def get_standings_age_hours(self) -> Optional[float]:
        """Get how old the standings data is in hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(updated_at) as latest FROM standings")
            row = cursor.fetchone()
            if row and row["latest"]:
                updated = datetime.fromisoformat(row["latest"])
                age = datetime.now() - updated
                return age.total_seconds() / 3600
            return None

    # Utility operations
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}
            for table in ["teams", "players", "games", "game_players", "standings"]:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()["cnt"]

            # Get date range of games
            cursor.execute("""
                SELECT MIN(game_date) as min_date, MAX(game_date) as max_date
                FROM games
            """)
            row = cursor.fetchone()
            stats["games_date_range"] = {"min": row["min_date"], "max": row["max_date"]}

            # Get star player count
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM players WHERE is_star_player = 1"
            )
            stats["star_players_count"] = cursor.fetchone()["cnt"]

            # Get database file size
            stats["db_size_mb"] = round(self.db_path.stat().st_size / (1024 * 1024), 2)
            stats["db_path"] = str(self.db_path)

            return stats

    # Buzz score operations
    def upsert_buzz_score(self, game_id: str, score: float, reasoning: str = None):
        """Insert or update a buzz score for a game."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO game_buzz (game_id, score, reasoning, scored_at)
                VALUES (?, ?, ?, ?)
            """,
                (game_id, score, reasoning, datetime.now().isoformat()),
            )

    def get_buzz_score(self, game_id: str) -> Optional[Dict]:
        """Get buzz score for a game."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT score, reasoning FROM game_buzz WHERE game_id = ?",
                (game_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_buzz_scores(self, game_ids: list) -> Dict[str, Dict]:
        """Get buzz scores for multiple games."""
        if not game_ids:
            return {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in game_ids)
            cursor.execute(
                f"SELECT game_id, score, reasoning FROM game_buzz WHERE game_id IN ({placeholders})",
                game_ids,
            )
            return {
                row["game_id"]: {"score": row["score"], "reasoning": row["reasoning"]}
                for row in cursor.fetchall()
            }

    def clear_all(self):
        """Clear all data from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for table in [
                "game_buzz",
                "game_players",
                "games",
                "standings",
                "players",
                "teams",
                "sync_metadata",
            ]:
                cursor.execute(f"DELETE FROM {table}")
            logger.info("Database cleared")
