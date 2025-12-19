"""Unit tests for NBAClient class (nba_api + SQLite)."""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import patch
from src.api.nba_api_client import (
    NBAClient,
    NBASyncService,
    FALLBACK_TOP_TEAMS,
    FALLBACK_STAR_PLAYERS,
)


class TestNBAClient:
    """Test cases for NBAClient class using nba_api with SQLite caching."""

    @pytest.fixture
    def config_file(self):
        """Create a temporary config file for testing."""
        config_content = """
database:
  path: "{db_path}"
"""
        # Create temp db file
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        # Create config with the temp db path
        temp_config = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml"
        )
        temp_config.write(config_content.format(db_path=temp_db.name))
        temp_config.close()

        yield temp_config.name, temp_db.name

        # Cleanup
        os.unlink(temp_config.name)
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

    def test_initialization(self, config_file):
        """Test NBAClient initializes correctly."""
        config_path, db_path = config_file
        client = NBAClient(config_path=config_path)

        assert client.db is not None
        assert client._top_teams_cache is not None
        assert client._star_players_cache is not None

    def test_initialization_uses_fallback_when_db_empty(self, config_file):
        """Test that fallback data is used when database is empty."""
        config_path, db_path = config_file
        client = NBAClient(config_path=config_path)

        # Should use fallback top teams when DB is empty
        assert client.TOP_5_TEAMS == FALLBACK_TOP_TEAMS
        assert client.STAR_PLAYERS == FALLBACK_STAR_PLAYERS

    def test_top5_teams_loads_from_db(self, config_file):
        """Test TOP_5_TEAMS loads from database when available."""
        config_path, db_path = config_file

        # Pre-populate database
        from src.utils.database import NBADatabase

        db = NBADatabase(db_path=db_path)
        db.upsert_team(1, "CLE", "Cleveland Cavaliers")
        db.upsert_team(2, "BOS", "Boston Celtics")
        db.upsert_standings(1, "CLE", 2024, 25, 5, 0.833, 1)
        db.upsert_standings(2, "BOS", 2024, 20, 10, 0.667, 2)

        client = NBAClient(config_path=config_path)

        # Should load from DB
        top_teams = client.TOP_5_TEAMS
        assert "CLE" in top_teams
        assert "BOS" in top_teams

    def test_star_players_loads_from_db(self, config_file):
        """Test STAR_PLAYERS loads from database when available."""
        config_path, db_path = config_file

        # Pre-populate database
        from src.utils.database import NBADatabase

        db = NBADatabase(db_path=db_path)
        db.upsert_player(1, "LeBron", "James", is_star=True)
        db.upsert_player(2, "Stephen", "Curry", is_star=True)

        client = NBAClient(config_path=config_path)

        stars = client.STAR_PLAYERS
        assert "LeBron James" in stars
        assert "Stephen Curry" in stars

    def test_is_top5_team(self, config_file):
        """Test is_top5_team method."""
        config_path, db_path = config_file
        client = NBAClient(config_path=config_path)

        # Uses fallback data
        assert client.is_top5_team("CLE") is True  # In fallback
        assert client.is_top5_team("XXX") is False

    def test_get_games_last_n_days_returns_empty_when_no_data(self, config_file):
        """Test get_games_last_n_days returns empty list when no data."""
        config_path, db_path = config_file
        client = NBAClient(config_path=config_path)

        games = client.get_games_last_n_days(days=7)
        assert games == []

    def test_get_games_last_n_days_returns_games_from_db(self, config_file):
        """Test get_games_last_n_days returns games from database."""
        config_path, db_path = config_file

        # Pre-populate database
        from src.utils.database import NBADatabase
        from datetime import timedelta

        db = NBADatabase(db_path=db_path)

        db.upsert_team(1, "LAL", "Los Angeles Lakers")
        db.upsert_team(2, "BOS", "Boston Celtics")

        # Add a game from 2 days ago
        game_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        db.upsert_game("12345", game_date, 1, 2, 118, 115, "Final", 2024)

        client = NBAClient(config_path=config_path)
        games = client.get_games_last_n_days(days=7)

        assert len(games) == 1
        assert games[0]["game_id"] == "12345"
        assert games[0]["home_team"]["abbr"] == "LAL"
        assert games[0]["away_team"]["abbr"] == "BOS"
        assert games[0]["total_points"] == 233
        assert games[0]["final_margin"] == 3


class TestNBASyncService:
    """Test cases for NBASyncService class."""

    @pytest.fixture
    def config_file(self):
        """Create a temporary config file for testing."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        config_content = f"""
database:
  path: "{temp_db.name}"
"""
        temp_config = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml"
        )
        temp_config.write(config_content)
        temp_config.close()

        yield temp_config.name, temp_db.name

        os.unlink(temp_config.name)
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

    def test_initialization(self, config_file):
        """Test NBASyncService initializes correctly."""
        config_path, db_path = config_file
        sync_service = NBASyncService(config_path=config_path)

        assert sync_service.db is not None

    def test_get_current_season(self, config_file):
        """Test _get_current_season returns correct format."""
        config_path, db_path = config_file
        sync_service = NBASyncService(config_path=config_path)

        season = sync_service._get_current_season()

        # Should be in format like "2024-25"
        assert "-" in season
        parts = season.split("-")
        assert len(parts) == 2
        assert len(parts[1]) == 2  # Last two digits of year

    @patch("nba_api.stats.static.teams.get_teams")
    def test_sync_teams(self, mock_get_teams, config_file):
        """Test sync_teams syncs team data."""
        config_path, db_path = config_file

        # Mock nba_api response
        mock_get_teams.return_value = [
            {
                "id": 1610612747,
                "abbreviation": "LAL",
                "full_name": "Los Angeles Lakers",
                "city": "Los Angeles",
            },
            {
                "id": 1610612738,
                "abbreviation": "BOS",
                "full_name": "Boston Celtics",
                "city": "Boston",
            },
        ]

        sync_service = NBASyncService(config_path=config_path)
        count = sync_service.sync_teams()

        assert count == 2

        # Verify teams in database
        teams = sync_service.db.get_all_teams()
        assert len(teams) == 2
        abbrs = {t["abbreviation"] for t in teams}
        assert "LAL" in abbrs
        assert "BOS" in abbrs

    def test_get_sync_status(self, config_file):
        """Test get_sync_status returns database stats."""
        config_path, db_path = config_file
        sync_service = NBASyncService(config_path=config_path)

        status = sync_service.get_sync_status()

        assert "teams_count" in status
        assert "players_count" in status
        assert "games_count" in status
        assert "last_teams_sync" in status
        assert "db_path" in status
