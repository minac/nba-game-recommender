#!/usr/bin/env python3
"""REST API server for NBA Game Recommender."""
import sys
from pathlib import Path
from flask import Flask, jsonify, request

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.recommender import GameRecommender
import yaml

app = Flask(__name__)

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

recommender = GameRecommender()


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


@app.route('/api/best-game', methods=['GET'])
def get_best_game():
    """
    Get the best game from the last N days.

    Query Parameters:
        days (int): Number of days to look back (default: 7)
        team (str): Favorite team abbreviation (optional)

    Returns:
        JSON with best game and score breakdown
    """
    try:
        days = int(request.args.get('days', 7))
        favorite_team = request.args.get('team')

        if days < 1 or days > 30:
            return jsonify({'error': 'Days must be between 1 and 30'}), 400

        result = recommender.get_best_game(days=days, favorite_team=favorite_team)

        if not result:
            return jsonify({'error': 'No games found'}), 404

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/games', methods=['GET'])
def get_all_games():
    """
    Get all games ranked by engagement score.

    Query Parameters:
        days (int): Number of days to look back (default: 7)
        team (str): Favorite team abbreviation (optional)

    Returns:
        JSON with all games ranked by score
    """
    try:
        days = int(request.args.get('days', 7))
        favorite_team = request.args.get('team')

        if days < 1 or days > 30:
            return jsonify({'error': 'Days must be between 1 and 30'}), 400

        results = recommender.get_all_games_ranked(days=days, favorite_team=favorite_team)

        return jsonify({
            'success': True,
            'count': len(results),
            'data': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    return jsonify({
        'success': True,
        'data': config
    })


def main():
    """Run the API server."""
    api_config = config.get('api', {})
    host = api_config.get('host', '0.0.0.0')
    port = api_config.get('port', 5000)
    debug = api_config.get('debug', False)

    print(f"🏀 NBA Game Recommender API starting on http://{host}:{port}")
    print(f"\nEndpoints:")
    print(f"  GET /api/health - Health check")
    print(f"  GET /api/best-game?days=7&team=LAL - Get best game")
    print(f"  GET /api/games?days=7 - Get all games ranked")
    print(f"  GET /api/config - Get configuration\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
