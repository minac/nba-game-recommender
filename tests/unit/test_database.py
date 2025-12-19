"""Unit tests for NBADatabase class."""

import pytest
import tempfile
import os
from datetime import datetime
from src.utils.database import NBADatabase


class TestNBADatabase:
    """Test cases for NBADatabase class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_file.close()
        db_path = temp_file.name

        db = NBADatabase(db_path=db_path)
        yield db

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_initialization_creates_database(self, temp_db):
        """Test that database file is created."""
        assert temp_db.db_path.exists()

    def test_initialization_creates_tables(self, temp_db):
        """Test that all required tables are created."""
        stats = temp_db.get_stats()
        assert "teams_count" in stats
        assert "players_count" in stats
        assert "games_count" in stats
        assert "standings_count" in stats

    # Team operations
    def test_upsert_team(self, temp_db):
        """Test inserting and updating a team."""
        temp_db.upsert_team(
            team_id=1610612747,
            abbreviation="LAL",
            full_name="Los Angeles Lakers",
            city="Los Angeles",
            conference="West",
            division="Pacific",
        )

        team = temp_db.get_team_by_abbr("LAL")
        assert team is not None
        assert team["full_name"] == "Los Angeles Lakers"
        assert team["city"] == "Los Angeles"

    def test_get_all_teams(self, temp_db):
        """Test getting all teams."""
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")
        temp_db.upsert_team(2, "BOS", "Boston Celtics")

        teams = temp_db.get_all_teams()
        assert len(teams) == 2
        abbrs = {t["abbreviation"] for t in teams}
        assert "LAL" in abbrs
        assert "BOS" in abbrs

    # Player operations
    def test_upsert_player(self, temp_db):
        """Test inserting and updating a player."""
        temp_db.upsert_player(
            player_id=2544,
            first_name="LeBron",
            last_name="James",
            team_id=1610612747,
            is_star=True,
            ppg=25.5,
        )

        stars = temp_db.get_star_players()
        assert "LeBron James" in stars

    def test_get_star_players(self, temp_db):
        """Test getting star players."""
        temp_db.upsert_player(1, "LeBron", "James", is_star=True)
        temp_db.upsert_player(2, "Stephen", "Curry", is_star=True)
        temp_db.upsert_player(3, "Joe", "Smith", is_star=False)

        stars = temp_db.get_star_players()
        assert len(stars) == 2
        assert "LeBron James" in stars
        assert "Stephen Curry" in stars
        assert "Joe Smith" not in stars

    def test_set_star_players(self, temp_db):
        """Test marking players as stars."""
        temp_db.upsert_player(1, "LeBron", "James")
        temp_db.upsert_player(2, "Stephen", "Curry")
        temp_db.upsert_player(3, "Joe", "Smith")

        # Mark only LeBron as star
        temp_db.set_star_players(["LeBron James"])

        stars = temp_db.get_star_players()
        assert len(stars) == 1
        assert "LeBron James" in stars

    # Game operations
    def test_upsert_game(self, temp_db):
        """Test inserting and updating a game."""
        # First add teams
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")
        temp_db.upsert_team(2, "BOS", "Boston Celtics")

        temp_db.upsert_game(
            game_id="0022400123",
            game_date="2024-12-15",
            home_team_id=1,
            away_team_id=2,
            home_score=118,
            away_score=115,
            status="Final",
            season=2024,
        )

        games = temp_db.get_games_for_date("2024-12-15")
        assert len(games) == 1
        assert games[0]["home_score"] == 118
        assert games[0]["away_score"] == 115

    def test_get_games_in_range(self, temp_db):
        """Test getting games in a date range."""
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")
        temp_db.upsert_team(2, "BOS", "Boston Celtics")

        temp_db.upsert_game("1", "2024-12-10", 1, 2, 100, 98, "Final", 2024)
        temp_db.upsert_game("2", "2024-12-12", 2, 1, 105, 102, "Final", 2024)
        temp_db.upsert_game("3", "2024-12-15", 1, 2, 110, 108, "Final", 2024)

        games = temp_db.get_games_in_range("2024-12-11", "2024-12-14")
        assert len(games) == 1
        assert games[0]["game_id"] == "2"

    def test_has_games_for_date(self, temp_db):
        """Test checking if games exist for a date."""
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")
        temp_db.upsert_team(2, "BOS", "Boston Celtics")
        temp_db.upsert_game("1", "2024-12-15", 1, 2, 100, 98, "Final", 2024)

        assert temp_db.has_games_for_date("2024-12-15") is True
        assert temp_db.has_games_for_date("2024-12-16") is False

    # Game player operations
    def test_upsert_game_player(self, temp_db):
        """Test inserting game player stats."""
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")
        temp_db.upsert_team(2, "BOS", "Boston Celtics")
        temp_db.upsert_game("123", "2024-12-15", 1, 2, 100, 98, "Final", 2024)
        temp_db.upsert_player(1, "LeBron", "James", team_id=1, is_star=True)

        temp_db.upsert_game_player(
            game_id="123",
            player_id=1,
            player_name="LeBron James",
            team_id=1,
            points=30,
            rebounds=10,
            assists=8,
        )

        assert temp_db.has_game_players("123") is True

    def test_get_star_players_in_game(self, temp_db):
        """Test counting star players in a game."""
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")
        temp_db.upsert_team(2, "BOS", "Boston Celtics")
        temp_db.upsert_game("123", "2024-12-15", 1, 2, 100, 98, "Final", 2024)

        temp_db.upsert_player(1, "LeBron", "James", is_star=True)
        temp_db.upsert_player(2, "Joe", "Smith", is_star=False)
        temp_db.upsert_player(3, "Stephen", "Curry", is_star=True)

        temp_db.upsert_game_player("123", 1, "LeBron James")
        temp_db.upsert_game_player("123", 2, "Joe Smith")
        temp_db.upsert_game_player("123", 3, "Stephen Curry")

        star_count = temp_db.get_star_players_in_game("123")
        assert star_count == 2

    # Standings operations
    def test_upsert_standings(self, temp_db):
        """Test inserting standings."""
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")

        temp_db.upsert_standings(
            team_id=1,
            team_abbr="LAL",
            season=2024,
            wins=20,
            losses=10,
            win_pct=0.667,
            conf_rank=3,
        )

        top_teams = temp_db.get_top_teams(5)
        assert "LAL" in top_teams

    def test_get_top_teams(self, temp_db):
        """Test getting top teams by win percentage."""
        temp_db.upsert_team(1, "BOS", "Boston Celtics")
        temp_db.upsert_team(2, "LAL", "Los Angeles Lakers")
        temp_db.upsert_team(3, "GSW", "Golden State Warriors")

        temp_db.upsert_standings(1, "BOS", 2024, 25, 5, 0.833, 1)
        temp_db.upsert_standings(2, "LAL", 2024, 20, 10, 0.667, 3)
        temp_db.upsert_standings(3, "GSW", 2024, 15, 15, 0.500, 5)

        top_2 = temp_db.get_top_teams(2)
        assert len(top_2) == 2
        assert top_2[0] == "BOS"  # Highest win pct
        assert top_2[1] == "LAL"

    # Sync metadata operations
    def test_sync_metadata(self, temp_db):
        """Test sync metadata tracking."""
        temp_db.set_last_sync("teams", "Synced 30 teams")

        last_sync = temp_db.get_last_sync("teams")
        assert last_sync is not None
        assert isinstance(last_sync, datetime)

    def test_get_last_sync_not_found(self, temp_db):
        """Test getting sync time for non-existent type."""
        result = temp_db.get_last_sync("nonexistent")
        assert result is None

    # Utility operations
    def test_get_stats(self, temp_db):
        """Test getting database statistics."""
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")
        temp_db.upsert_player(1, "LeBron", "James", is_star=True)

        stats = temp_db.get_stats()
        assert stats["teams_count"] == 1
        assert stats["players_count"] == 1
        assert stats["star_players_count"] == 1
        assert "db_size_mb" in stats
        assert "db_path" in stats

    def test_clear_all(self, temp_db):
        """Test clearing all data."""
        temp_db.upsert_team(1, "LAL", "Los Angeles Lakers")
        temp_db.upsert_player(1, "LeBron", "James")

        temp_db.clear_all()

        stats = temp_db.get_stats()
        assert stats["teams_count"] == 0
        assert stats["players_count"] == 0
