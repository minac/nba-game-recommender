#!/usr/bin/env python3
"""
Example usage of the NBA Game Recommender with mock data.
This demonstrates the scoring algorithm without making API calls.
"""

from src.core.game_scorer import GameScorer

# Mock game data
mock_games = [
    {
        'game_id': '1',
        'game_date': '2024-01-15',
        'home_team': {'name': 'Celtics', 'abbr': 'BOS', 'score': 115},
        'away_team': {'name': 'Lakers', 'abbr': 'LAL', 'score': 118},
        'total_points': 233,
        'final_margin': 3,
        'lead_changes': 12,
        'star_players_count': 4
    },
    {
        'game_id': '2',
        'game_date': '2024-01-15',
        'home_team': {'name': 'Warriors', 'abbr': 'GSW', 'score': 95},
        'away_team': {'name': 'Kings', 'abbr': 'SAC', 'score': 120},
        'total_points': 215,
        'final_margin': 25,
        'lead_changes': 3,
        'star_players_count': 2
    },
    {
        'game_id': '3',
        'game_date': '2024-01-15',
        'home_team': {'name': 'Bucks', 'abbr': 'MIL', 'score': 108},
        'away_team': {'name': 'Nuggets', 'abbr': 'DEN', 'score': 106},
        'total_points': 214,
        'final_margin': 2,
        'lead_changes': 15,
        'star_players_count': 3
    }
]

# Configuration
config = {
    'lead_changes_weight': 10,
    'top5_team_bonus': 50,
    'close_game_bonus': 100,
    'min_total_points': 200,
    'star_power_weight': 20,
    'favorite_team_bonus': 75
}

# Top 5 teams
top5_teams = {'BOS', 'DEN', 'MIL', 'PHX', 'LAL'}

# Create scorer
scorer = GameScorer(config)

print("=" * 60)
print("NBA GAME RECOMMENDER - EXAMPLE USAGE")
print("=" * 60)
print()

# Score all games
scored_games = []
for game in mock_games:
    result = scorer.score_game(game, favorite_team='LAL', top5_teams=top5_teams)
    scored_games.append({
        'game': game,
        'score': result['score'],
        'breakdown': result['breakdown']
    })

# Sort by score
scored_games.sort(key=lambda x: x['score'], reverse=True)

# Display results
for i, result in enumerate(scored_games, 1):
    game = result['game']
    breakdown = result['breakdown']

    print(f"{i}. {game['away_team']['abbr']} {game['away_team']['score']} @ "
          f"{game['home_team']['score']} {game['home_team']['abbr']}")
    print(f"   Engagement Score: {result['score']:.2f}")
    print(f"   Lead Changes: {breakdown['lead_changes']['count']} "
          f"({breakdown['lead_changes']['points']:.1f} pts)")
    print(f"   Final Margin: {breakdown['close_game']['margin']} pts "
          f"({breakdown['close_game']['points']:.1f} pts)")
    print(f"   Total Points: {breakdown['total_points']['total']}")
    print(f"   Star Players: {breakdown['star_power']['count']}")
    print(f"   Top 5 Teams: {breakdown['top5_teams']['count']}")
    print(f"   Favorite Team: {'Yes' if breakdown['favorite_team']['has_favorite'] else 'No'}")
    print()

print("=" * 60)
print(f"BEST GAME: {scored_games[0]['game']['away_team']['abbr']} @ "
      f"{scored_games[0]['game']['home_team']['abbr']}")
print(f"Score: {scored_games[0]['score']:.2f}")
print("=" * 60)
