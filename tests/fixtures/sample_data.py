"""Sample test data for NBA games."""

# Team name mappings for common abbreviations
TEAM_NAMES = {
    "LAL": "Lakers",
    "BOS": "Celtics",
    "DEN": "Nuggets",
    "MIL": "Bucks",
    "PHX": "Suns",
    "GSW": "Warriors",
    "MIA": "Heat",
    "SAC": "Kings",
    "POR": "Trail Blazers",
    "DAL": "Mavericks",
}


def get_sample_game(
    home_abbr="LAL",
    away_abbr="BOS",
    home_score=110,
    away_score=108,
    star_players=4,
    game_date="2024-01-15",
    game_id="0022300123",
):
    """
    Create a sample game dictionary.

    Args:
        home_abbr: Home team abbreviation
        away_abbr: Away team abbreviation
        home_score: Home team score
        away_score: Away team score
        star_players: Number of star players
        game_date: Game date string
        game_id: Game ID

    Returns:
        Game dictionary
    """
    return {
        "game_id": game_id,
        "game_date": game_date,
        "home_team": {
            "name": TEAM_NAMES.get(home_abbr, "Home Team"),
            "abbr": home_abbr,
            "score": home_score,
        },
        "away_team": {
            "name": TEAM_NAMES.get(away_abbr, "Away Team"),
            "abbr": away_abbr,
            "score": away_score,
        },
        "total_points": home_score + away_score,
        "final_margin": abs(home_score - away_score),
        "star_players_count": star_players,
    }


def get_sample_config():
    """Get sample scoring configuration."""
    return {
        "top5_team_bonus": 50,
        "close_game_bonus": 100,
        "min_total_points": 200,
        "high_score_bonus": 10,
        "star_power_weight": 20,
        "favorite_team_bonus": 75,
    }


def get_sample_scoreboard_response():
    """Get sample NBA API scoreboard response."""
    return {
        "scoreboard": {
            "games": [
                {
                    "gameId": "0022300123",
                    "gameStatus": 3,
                    "homeTeam": {
                        "teamName": "Lakers",
                        "teamTricode": "LAL",
                        "score": 110,
                    },
                    "awayTeam": {
                        "teamName": "Celtics",
                        "teamTricode": "BOS",
                        "score": 108,
                    },
                },
                {
                    "gameId": "0022300124",
                    "gameStatus": 3,
                    "homeTeam": {
                        "teamName": "Warriors",
                        "teamTricode": "GSW",
                        "score": 95,
                    },
                    "awayTeam": {
                        "teamName": "Heat",
                        "teamTricode": "MIA",
                        "score": 100,
                    },
                },
            ]
        }
    }


def get_sample_playbyplay_response():
    """Get sample play-by-play response."""
    return {
        "game": {
            "actions": [
                {"homeScore": 0, "awayScore": 2},
                {"homeScore": 3, "awayScore": 2},
                {"homeScore": 3, "awayScore": 5},
                {"homeScore": 8, "awayScore": 5},
                {"homeScore": 8, "awayScore": 10},
                {"homeScore": 13, "awayScore": 10},
            ]
        }
    }


def get_sample_boxscore_response(star_players=None):
    """
    Get sample box score response with star players.

    Args:
        star_players: List of star player names to include. If None, uses default.

    Returns:
        Box score response dictionary
    """
    if star_players is None:
        star_players = ["LeBron James", "Jayson Tatum", "Anthony Davis"]

    # Parse star players into first/last names
    home_players = []
    away_players = []

    for i, player in enumerate(star_players[:3]):  # Max 3 per team
        parts = player.split(" ", 1)
        first = parts[0] if len(parts) > 0 else "Player"
        last = parts[1] if len(parts) > 1 else str(i)

        player_dict = {"firstName": first, "familyName": last, "points": 20 + i * 5}
        if i % 2 == 0:
            home_players.append(player_dict)
        else:
            away_players.append(player_dict)

    # Add regular players
    home_players.append({"firstName": "Regular", "familyName": "Player1", "points": 10})
    away_players.append({"firstName": "Regular", "familyName": "Player2", "points": 12})

    return {
        "boxScoreTraditional": {
            "homeTeam": {"players": home_players},
            "awayTeam": {"players": away_players},
        }
    }


def get_sample_standings_response():
    """Get sample standings response for top teams."""
    return {
        "resultSets": [
            {
                "headers": ["TeamSlug", "WinPCT", "WINS", "LOSSES"],
                "rowSet": [
                    ["BOS", 0.750, 30, 10],
                    ["DEN", 0.725, 29, 11],
                    ["MIL", 0.700, 28, 12],
                    ["PHX", 0.675, 27, 13],
                    ["LAL", 0.650, 26, 14],
                    ["GSW", 0.600, 24, 16],
                    ["MIA", 0.550, 22, 18],
                ],
            }
        ]
    }


def get_sample_league_leaders_response():
    """Get sample league leaders response for star players."""
    return {
        "resultSet": {
            "headers": ["PLAYER", "PTS", "GP"],
            "rowSet": [
                ["LeBron James", 28.5, 40],
                ["Stephen Curry", 27.8, 42],
                ["Kevin Durant", 27.2, 38],
                ["Giannis Antetokounmpo", 26.9, 41],
                ["Jayson Tatum", 26.5, 43],
                ["Anthony Davis", 25.8, 39],
                ["Damian Lillard", 25.2, 40],
                ["Nikola Jokic", 24.9, 42],
            ],
        }
    }
