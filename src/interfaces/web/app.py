#!/usr/bin/env python3
"""Web interface for NBA Game Recommender."""
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.recommender import GameRecommender
from src.services.game_service import GameService
from src.utils.logger import get_logger
import yaml
from liquid import Environment, FileSystemLoader

logger = get_logger(__name__)

app = Flask(__name__)

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Create recommender (can be mocked by tests)
recommender = GameRecommender()
# Use the shared game service with the recommender
game_service = GameService(recommender=recommender)


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', config=config)


@app.route('/recommend', methods=['POST'])
def recommend():
    """Get game recommendation based on user preferences."""
    data = request.json
    days = data.get('days', 7)
    favorite_team = data.get('favorite_team')
    show_all = data.get('show_all', False)

    logger.info(f"POST /recommend - days={days}, team={favorite_team}, show_all={show_all}")

    # Use shared service (handles validation and error handling)
    if show_all:
        response = game_service.get_all_games_ranked(days=days, favorite_team=favorite_team)

        # Return appropriate HTTP status code
        if not response['success']:
            error_code = response.get('error_code')
            if error_code == 'VALIDATION_ERROR':
                return jsonify(response), 400
            elif error_code == 'NO_GAMES':
                return jsonify(response), 404
            else:
                return jsonify(response), 500

        logger.info(f"Returning {response['count']} ranked games")
        # Format response for web client
        return jsonify({
            'success': True,
            'show_all': True,
            'count': response['count'],
            'games': response['data']
        })
    else:
        response = game_service.get_best_game(days=days, favorite_team=favorite_team)

        # Return appropriate HTTP status code
        if not response['success']:
            error_code = response.get('error_code')
            if error_code == 'VALIDATION_ERROR':
                return jsonify(response), 400
            elif error_code == 'NO_GAMES':
                return jsonify(response), 404
            else:
                return jsonify(response), 500

        logger.info("Best game recommendation returned successfully")
        # Format response for web client
        return jsonify({
            'success': True,
            'show_all': False,
            'game': response['data']
        })


@app.route('/api/trmnl', methods=['GET'])
def trmnl_webhook():
    """
    TRMNL webhook endpoint that returns game data in TRMNL-compatible format.

    Query parameters:
    - days: Number of days to look back (default: 7)
    - team: Favorite team abbreviation (optional)
    """
    days = request.args.get('days', 7)
    favorite_team = request.args.get('team', '').upper() or None

    logger.info(f"GET /api/trmnl - days={days}, team={favorite_team}")

    # Clamp days to TRMNL's preferred range (1-14)
    try:
        days_int = int(days)
        if days_int < 1 or days_int > 14:
            logger.warning(f"Invalid days parameter {days}, using default: 7")
            days = 7
    except (ValueError, TypeError):
        logger.warning(f"Invalid days parameter {days}, using default: 7")
        days = 7

    # Use shared service
    response = game_service.get_best_game(days=days, favorite_team=favorite_team)

    # Prepare TRMNL-compatible response with merge_variables
    if response['success']:
        result = response['data']
        game_data = result.get('game', {})
        breakdown = result.get('breakdown', {})
        score = result.get('score', 0)

        # Format score to 1 decimal place
        formatted_score = f"{score:.1f}"

        # Format breakdown data for display
        formatted_breakdown = {
            'lead_changes': {
                'count': breakdown.get('lead_changes', {}).get('count', 0),
                'points': f"{breakdown.get('lead_changes', {}).get('points', 0):.1f}"
            },
            'top5_teams': {
                'count': breakdown.get('top5_teams', {}).get('count', 0),
                'points': f"{breakdown.get('top5_teams', {}).get('points', 0):.1f}"
            },
            'close_game': {
                'margin': breakdown.get('close_game', {}).get('margin', 0),
                'points': f"{breakdown.get('close_game', {}).get('points', 0):.1f}"
            },
            'total_points': {
                'total': breakdown.get('total_points', {}).get('total', 0),
                'threshold_met': breakdown.get('total_points', {}).get('threshold_met', False)
            },
            'star_power': {
                'count': breakdown.get('star_power', {}).get('count', 0),
                'points': f"{breakdown.get('star_power', {}).get('points', 0):.1f}"
            },
            'favorite_team': {
                'has_favorite': breakdown.get('favorite_team', {}).get('has_favorite', False),
                'points': f"{breakdown.get('favorite_team', {}).get('points', 0):.1f}"
            }
        }

        merge_variables = {
            'game': game_data,
            'score': formatted_score,
            'breakdown': formatted_breakdown,
            'updated_at': datetime.now().strftime('%I:%M %p')
        }
        logger.info("TRMNL webhook returned game recommendation successfully")
        return jsonify({
            'merge_variables': merge_variables
        })
    else:
        # No games found or error - return appropriate state
        error_code = response.get('error_code')
        error_message = response.get('error', 'Unknown error')

        if error_code == 'NO_GAMES':
            logger.warning(f"No games found for TRMNL webhook (days={days})")
            merge_variables = {
                'game': None,
                'score': '0',
                'breakdown': {},
                'error_message': f'No NBA games found in the past {days} days',
                'updated_at': datetime.now().strftime('%I:%M %p')
            }
            return jsonify({
                'merge_variables': merge_variables
            })
        else:
            # Return error state for TRMNL display
            logger.error(f"Error in /api/trmnl: {error_message}")
            return jsonify({
                'merge_variables': {
                    'game': None,
                    'score': '0',
                    'breakdown': {},
                    'error_message': f'Error: {error_message}',
                    'updated_at': datetime.now().strftime('%I:%M %p')
                }
            }), 500


@app.route('/trmnl-viewer')
def trmnl_viewer():
    """Render the TRMNL screen viewer interface."""
    return render_template('trmnl_viewer.html', config=config)


@app.route('/trmnl-viewer/render', methods=['GET'])
def render_trmnl_screen():
    """
    Render a TRMNL screen layout with live data.

    Query parameters:
    - layout: Layout type (full, half_horizontal, half_vertical, quadrant)
    - days: Number of days to look back (default: 7)
    - team: Favorite team abbreviation (optional)
    """
    try:
        layout = request.args.get('layout', 'full')
        days = int(request.args.get('days', 7))
        favorite_team = request.args.get('team', '').upper() or None

        # Validate layout
        valid_layouts = ['full', 'half_horizontal', 'half_vertical', 'quadrant']
        if layout not in valid_layouts:
            return jsonify({'error': f'Invalid layout. Must be one of: {", ".join(valid_layouts)}'}), 400

        logger.info(f"Rendering TRMNL screen - layout={layout}, days={days}, team={favorite_team}")

        # Get game data (same as /api/trmnl endpoint)
        if days < 1 or days > 14:
            days = 7

        result = recommender.get_best_game(days=days, favorite_team=favorite_team)

        # Prepare merge variables
        if result:
            game_data = result.get('game', {})
            breakdown = result.get('breakdown', {})
            score = result.get('score', 0)

            formatted_score = f"{score:.1f}"

            formatted_breakdown = {
                'lead_changes': {
                    'count': breakdown.get('lead_changes', {}).get('count', 0),
                    'points': f"{breakdown.get('lead_changes', {}).get('points', 0):.1f}"
                },
                'top5_teams': {
                    'count': breakdown.get('top5_teams', {}).get('count', 0),
                    'points': f"{breakdown.get('top5_teams', {}).get('points', 0):.1f}"
                },
                'close_game': {
                    'margin': breakdown.get('close_game', {}).get('margin', 0),
                    'points': f"{breakdown.get('close_game', {}).get('points', 0):.1f}"
                },
                'total_points': {
                    'total': breakdown.get('total_points', {}).get('total', 0),
                    'threshold_met': breakdown.get('total_points', {}).get('threshold_met', False)
                },
                'star_power': {
                    'count': breakdown.get('star_power', {}).get('count', 0),
                    'points': f"{breakdown.get('star_power', {}).get('points', 0):.1f}"
                },
                'favorite_team': {
                    'has_favorite': breakdown.get('favorite_team', {}).get('has_favorite', False),
                    'points': f"{breakdown.get('favorite_team', {}).get('points', 0):.1f}"
                }
            }

            merge_variables = {
                'game': game_data,
                'score': formatted_score,
                'breakdown': formatted_breakdown,
                'updated_at': datetime.now().strftime('%I:%M %p')
            }
        else:
            merge_variables = {
                'game': None,
                'score': '0',
                'breakdown': {},
                'error_message': f'No NBA games found in the past {days} days',
                'updated_at': datetime.now().strftime('%I:%M %p')
            }

        # Load and render the Liquid template
        trmnl_dir = Path(__file__).parent.parent.parent.parent / 'trmnl' / 'src'
        liquid_env = Environment(loader=FileSystemLoader(str(trmnl_dir)))

        template_file = f"{layout}.liquid"
        template = liquid_env.get_template(template_file)
        rendered_html = template.render(**merge_variables)

        logger.info(f"Successfully rendered {layout} layout")

        # Return the rendered HTML wrapped in a container for display
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TRMNL Screen Preview - {layout}</title>
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: #f0f0f0;
                }}
                .trmnl-container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border: 2px solid #333;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .trmnl-info {{
                    background: #333;
                    color: white;
                    padding: 10px 20px;
                    font-size: 14px;
                }}
                .trmnl-screen {{
                    background: white;
                    padding: 0;
                    min-height: 400px;
                }}
            </style>
        </head>
        <body>
            <div class="trmnl-container">
                <div class="trmnl-info">
                    <strong>TRMNL Screen Preview:</strong> {layout} layout | Days: {days} | Team: {favorite_team or 'None'}
                </div>
                <div class="trmnl-screen">
                    {rendered_html}
                </div>
            </div>
        </body>
        </html>
        """

    except Exception as e:
        logger.error(f"Error in /trmnl-viewer/render: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def main():
    """Run the web server."""
    web_config = config.get('web', {})
    host = web_config.get('host', '0.0.0.0')
    port = web_config.get('port', 8080)

    logger.info(f"🏀 NBA Game Recommender Web Interface starting on http://{host}:{port}")
    logger.info(f"Open your browser and navigate to http://localhost:{port}")

    app.run(host=host, port=port, debug=True)


if __name__ == '__main__':
    main()
