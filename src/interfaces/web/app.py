#!/usr/bin/env python3
"""Web interface for NBA Game Recommender."""

import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import os
from functools import lru_cache
from typing import Optional, Tuple, Any

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
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Create recommender (can be mocked by tests)
recommender = GameRecommender()
# Use the shared game service with the recommender
game_service = GameService(recommender=recommender)

# Request-level cache for ranked games (in-memory with TTL)
_request_cache = {}
_cache_ttl_seconds = 300  # 5 minutes


def get_cached_or_fetch(cache_key: str, fetch_func, ttl_seconds: int = 300):
    """
    Get data from cache or fetch if expired/missing.

    Args:
        cache_key: Unique key for this request
        fetch_func: Function to call if cache miss
        ttl_seconds: Time to live in seconds

    Returns:
        Cached or freshly fetched data
    """
    global _request_cache

    # Check if we have cached data
    if cache_key in _request_cache:
        cached_data, cached_time = _request_cache[cache_key]
        age = (datetime.now() - cached_time).total_seconds()

        if age < ttl_seconds:
            logger.info(f"Cache HIT for {cache_key} (age: {age:.1f}s)")
            return cached_data
        else:
            logger.info(f"Cache EXPIRED for {cache_key} (age: {age:.1f}s)")

    # Cache miss or expired - fetch fresh data
    logger.info(f"Cache MISS for {cache_key} - fetching fresh data")
    fresh_data = fetch_func()
    _request_cache[cache_key] = (fresh_data, datetime.now())

    # Clean up old cache entries (keep cache size bounded)
    if len(_request_cache) > 100:
        # Remove oldest 50% of entries
        sorted_keys = sorted(_request_cache.items(), key=lambda x: x[1][1])
        for key, _ in sorted_keys[:50]:
            del _request_cache[key]

    return fresh_data


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html", config=config)


@app.route("/api/health")
def health():
    """Health check endpoint."""
    logger.info("GET /api/health")
    return jsonify({"status": "ok"})


@app.route("/recommend", methods=["POST"])
def recommend():
    """Get game recommendation based on user preferences."""
    data = request.json
    days = data.get("days", 7)
    favorite_team = data.get("favorite_team")
    show_all = data.get("show_all", False)

    logger.info(
        f"POST /recommend - days={days}, team={favorite_team}, show_all={show_all}"
    )

    # Use shared service (handles validation and error handling)
    if show_all:
        # Use request-level caching for ranked games (significant speedup on repeat requests)
        cache_key = f"ranked_games_{days}_{favorite_team}"
        response = get_cached_or_fetch(
            cache_key,
            lambda: game_service.get_all_games_ranked(
                days=days, favorite_team=favorite_team
            ),
            ttl_seconds=_cache_ttl_seconds,
        )

        # Return appropriate HTTP status code
        if not response["success"]:
            error_code = response.get("error_code")
            if error_code == "VALIDATION_ERROR":
                return jsonify(response), 400
            elif error_code == "NO_GAMES":
                return jsonify(response), 404
            elif error_code == "NBA_API_TIMEOUT":
                return jsonify(response), 503  # Service Unavailable
            else:
                return jsonify(response), 500

        logger.info(f"Returning {response['count']} ranked games")
        # Format response for web client
        return jsonify(
            {
                "success": True,
                "show_all": True,
                "count": response["count"],
                "games": response["data"],
            }
        )
    else:
        # Use request-level caching for best game recommendation too
        cache_key = f"best_game_{days}_{favorite_team}"
        response = get_cached_or_fetch(
            cache_key,
            lambda: game_service.get_best_game(days=days, favorite_team=favorite_team),
            ttl_seconds=_cache_ttl_seconds,
        )

        # Return appropriate HTTP status code
        if not response["success"]:
            error_code = response.get("error_code")
            if error_code == "VALIDATION_ERROR":
                return jsonify(response), 400
            elif error_code == "NO_GAMES":
                return jsonify(response), 404
            elif error_code == "NBA_API_TIMEOUT":
                return jsonify(response), 503  # Service Unavailable
            else:
                return jsonify(response), 500

        logger.info("Best game recommendation returned successfully")
        # Format response for web client
        return jsonify({"success": True, "show_all": False, "game": response["data"]})


@app.route("/api/trmnl", methods=["GET"])
def trmnl_webhook():
    """
    TRMNL polling endpoint that returns game data in TRMNL-compatible format.

    For TRMNL's Polling strategy, data is returned at the root level (not wrapped in merge_variables).
    For Webhook strategy, use POST to /api/trmnl/webhook instead.

    Query parameters:
    - days: Number of days to look back (default: 7)
    - team: Favorite team abbreviation (optional)
    """
    days = request.args.get("days", 7)
    favorite_team = request.args.get("team", "").upper() or None

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

    # Prepare TRMNL-compatible response (root level for polling strategy)
    if response["success"]:
        result = response["data"]
        game_data = result.get("game", {})
        breakdown = result.get("breakdown", {})
        score = result.get("score", 0)

        # Format score to 1 decimal place
        formatted_score = f"{score:.1f}"

        # Format breakdown data for display
        formatted_breakdown = {
            "top5_teams": {
                "count": breakdown.get("top5_teams", {}).get("count", 0),
                "points": f"{breakdown.get('top5_teams', {}).get('points', 0):.1f}",
            },
            "close_game": {
                "margin": breakdown.get("close_game", {}).get("margin", 0),
                "points": f"{breakdown.get('close_game', {}).get('points', 0):.1f}",
            },
            "total_points": {
                "total": breakdown.get("total_points", {}).get("total", 0),
                "threshold_met": breakdown.get("total_points", {}).get(
                    "threshold_met", False
                ),
                "points": f"{breakdown.get('total_points', {}).get('points', 0):.1f}",
            },
            "star_power": {
                "count": breakdown.get("star_power", {}).get("count", 0),
                "points": f"{breakdown.get('star_power', {}).get('points', 0):.1f}",
            },
            "favorite_team": {
                "has_favorite": breakdown.get("favorite_team", {}).get(
                    "has_favorite", False
                ),
                "points": f"{breakdown.get('favorite_team', {}).get('points', 0):.1f}",
            },
        }

        # Return data at root level for TRMNL polling strategy
        data = {
            "game": game_data,
            "score": formatted_score,
            "breakdown": formatted_breakdown,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        logger.info("TRMNL polling endpoint returned game recommendation successfully")
        return jsonify(data)
    else:
        # No games found or error - return appropriate state
        error_code = response.get("error_code")
        error_message = response.get("error", "Unknown error")

        if error_code == "NO_GAMES":
            logger.warning(f"No games found for TRMNL polling endpoint (days={days})")
            # Return empty state at root level
            data = {
                "game": None,
                "score": "0",
                "breakdown": {},
                "error_message": f"No NBA games found in the past {days} days",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            return jsonify(data)
        else:
            # Return error state for TRMNL display
            logger.error(f"Error in /api/trmnl: {error_message}")
            data = {
                "game": None,
                "score": "0",
                "breakdown": {},
                "error_message": f"Error: {error_message}",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            return jsonify(data), 500


@app.route("/trmnl-viewer")
def trmnl_viewer():
    """Render the TRMNL screen viewer interface."""
    return render_template("trmnl_viewer.html", config=config)


@app.route("/trmnl-viewer/render", methods=["GET"])
def render_trmnl_screen():
    """
    Render a TRMNL screen layout with live data.

    Query parameters:
    - layout: Layout type (full, half_horizontal, half_vertical, quadrant)
    - days: Number of days to look back (default: 7)
    - team: Favorite team abbreviation (optional)
    """
    try:
        layout = request.args.get("layout", "full")
        days = int(request.args.get("days", 7))
        favorite_team = request.args.get("team", "").upper() or None

        # Validate layout
        valid_layouts = ["full", "half_horizontal", "half_vertical", "quadrant"]
        if layout not in valid_layouts:
            return jsonify(
                {"error": f"Invalid layout. Must be one of: {', '.join(valid_layouts)}"}
            ), 400

        logger.info(
            f"Rendering TRMNL screen - layout={layout}, days={days}, team={favorite_team}"
        )

        # Get game data (same as /api/trmnl endpoint)
        if days < 1 or days > 14:
            days = 7

        result = recommender.get_best_game(days=days, favorite_team=favorite_team)

        # Prepare merge variables
        if result:
            game_data = result.get("game", {})
            breakdown = result.get("breakdown", {})
            score = result.get("score", 0)

            formatted_score = f"{score:.1f}"

            formatted_breakdown = {
                "top5_teams": {
                    "count": breakdown.get("top5_teams", {}).get("count", 0),
                    "points": f"{breakdown.get('top5_teams', {}).get('points', 0):.1f}",
                },
                "close_game": {
                    "margin": breakdown.get("close_game", {}).get("margin", 0),
                    "points": f"{breakdown.get('close_game', {}).get('points', 0):.1f}",
                },
                "total_points": {
                    "total": breakdown.get("total_points", {}).get("total", 0),
                    "threshold_met": breakdown.get("total_points", {}).get(
                        "threshold_met", False
                    ),
                    "points": f"{breakdown.get('total_points', {}).get('points', 0):.1f}",
                },
                "star_power": {
                    "count": breakdown.get("star_power", {}).get("count", 0),
                    "points": f"{breakdown.get('star_power', {}).get('points', 0):.1f}",
                },
                "favorite_team": {
                    "has_favorite": breakdown.get("favorite_team", {}).get(
                        "has_favorite", False
                    ),
                    "points": f"{breakdown.get('favorite_team', {}).get('points', 0):.1f}",
                },
            }

            merge_variables = {
                "game": game_data,
                "score": formatted_score,
                "breakdown": formatted_breakdown,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        else:
            merge_variables = {
                "game": None,
                "score": "0",
                "breakdown": {},
                "error_message": f"No NBA games found in the past {days} days",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

        # Load and render the Liquid template
        trmnl_dir = Path(__file__).parent.parent.parent.parent / "trmnl" / "src"
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
                    <strong>TRMNL Screen Preview:</strong> {layout} layout | Days: {days} | Team: {favorite_team or "None"}
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
        return jsonify({"error": str(e)}), 500


def main():
    """Run the web server."""
    web_config = config.get("web", {})
    host = web_config.get("host", "0.0.0.0")
    port = web_config.get("port", 8080)

    logger.info(
        f"🏀 NBA Game Recommender Web Interface starting on http://{host}:{port}"
    )
    logger.info(f"Open your browser and navigate to http://localhost:{port}")

    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    main()
