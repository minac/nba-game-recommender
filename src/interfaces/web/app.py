#!/usr/bin/env python3
"""Web interface for NBA Game Recommender."""
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.recommender import GameRecommender
import yaml

app = Flask(__name__)

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

recommender = GameRecommender()


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', config=config)


@app.route('/recommend', methods=['POST'])
def recommend():
    """Get game recommendation based on user preferences."""
    try:
        data = request.json
        days = int(data.get('days', 7))
        favorite_team = data.get('favorite_team')
        show_all = data.get('show_all', False)

        if days < 1 or days > 30:
            return jsonify({'error': 'Days must be between 1 and 30'}), 400

        if show_all:
            results = recommender.get_all_games_ranked(days=days, favorite_team=favorite_team)
            return jsonify({
                'success': True,
                'show_all': True,
                'count': len(results),
                'games': results
            })
        else:
            result = recommender.get_best_game(days=days, favorite_team=favorite_team)

            if not result:
                return jsonify({'error': 'No games found'}), 404

            return jsonify({
                'success': True,
                'show_all': False,
                'game': result
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def main():
    """Run the web server."""
    web_config = config.get('web', {})
    host = web_config.get('host', '0.0.0.0')
    port = web_config.get('port', 8080)

    print(f"🏀 NBA Game Recommender Web Interface starting on http://{host}:{port}")
    print(f"Open your browser and navigate to http://localhost:{port}\n")

    app.run(host=host, port=port, debug=True)


if __name__ == '__main__':
    main()
