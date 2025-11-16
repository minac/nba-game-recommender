"""Sample test data for NBA games."""


def get_sample_game(
    home_abbr='LAL',
    away_abbr='BOS',
    home_score=110,
    away_score=108,
    lead_changes=12,
    star_players=4,
    game_date='2024-01-15'
):
    """
    Create a sample game dictionary.

    Args:
        home_abbr: Home team abbreviation
        away_abbr: Away team abbreviation
        home_score: Home team score
        away_score: Away team score
        lead_changes: Number of lead changes
        star_players: Number of star players
        game_date: Game date string

    Returns:
        Game dictionary
    """
    return {
        'game_id': '0022300123',
        'game_date': game_date,
        'home_team': {
            'name': 'Lakers',
            'abbr': home_abbr,
            'score': home_score
        },
        'away_team': {
            'name': 'Celtics',
            'abbr': away_abbr,
            'score': away_score
        },
        'total_points': home_score + away_score,
        'final_margin': abs(home_score - away_score),
        'lead_changes': lead_changes,
        'star_players_count': star_players
    }


def get_sample_config():
    """Get sample scoring configuration."""
    return {
        'lead_changes_weight': 10,
        'top5_team_bonus': 50,
        'close_game_bonus': 100,
        'min_total_points': 200,
        'star_power_weight': 20,
        'favorite_team_bonus': 75
    }


def get_sample_scoreboard_response():
    """Get sample NBA API scoreboard response."""
    return {
        'scoreboard': {
            'games': [
                {
                    'gameId': '0022300123',
                    'gameStatus': 3,
                    'homeTeam': {
                        'teamName': 'Lakers',
                        'teamTricode': 'LAL',
                        'score': 110
                    },
                    'awayTeam': {
                        'teamName': 'Celtics',
                        'teamTricode': 'BOS',
                        'score': 108
                    }
                },
                {
                    'gameId': '0022300124',
                    'gameStatus': 3,
                    'homeTeam': {
                        'teamName': 'Warriors',
                        'teamTricode': 'GSW',
                        'score': 95
                    },
                    'awayTeam': {
                        'teamName': 'Heat',
                        'teamTricode': 'MIA',
                        'score': 100
                    }
                }
            ]
        }
    }


def get_sample_playbyplay_response():
    """Get sample play-by-play response."""
    return {
        'game': {
            'actions': [
                {'homeScore': 0, 'awayScore': 2},
                {'homeScore': 3, 'awayScore': 2},
                {'homeScore': 3, 'awayScore': 5},
                {'homeScore': 8, 'awayScore': 5},
                {'homeScore': 8, 'awayScore': 10},
                {'homeScore': 13, 'awayScore': 10},
            ]
        }
    }


def get_sample_boxscore_response():
    """Get sample box score response with star players."""
    return {
        'boxScoreTraditional': {
            'players': [
                {'name': 'LeBron James', 'points': 28},
                {'name': 'Jayson Tatum', 'points': 32},
                {'name': 'Anthony Davis', 'points': 18},
                {'name': 'Regular Player', 'points': 10},
            ]
        }
    }
