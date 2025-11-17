# NBA Game Recommender

Finds the most engaging NBA game* from the past week using Ball Don't Lie NBA API data. Scores games based on closeness in points, whether star players played, if there were top teams involved, if your favorite team played, and whether the game had at least 200 points.

## Features

- **Multiple Interfaces**: CLI, REST API, Web UI, or TRMNL E-ink Display
- **Balanced Configurable Scoring**: Evaluates games based on weights and preferences via `config.yaml`
- **Cached**: File-based caching reduces API calls and improves performance

## Quick Start

```bash
# Install dependencies
uv sync

# Run CLI
uv run python src/interfaces/cli.py

# Run API server (localhost:3000)
uv run python src/interfaces/api_server.py

# Run web interface (localhost:8080)
uv run python src/interfaces/web/app.py
```

## CLI Usage

```bash
uv run python src/interfaces/cli.py              # Best game, last 7 days
uv run python src/interfaces/cli.py -d 3         # Last 3 days
uv run python src/interfaces/cli.py -t LAL       # Set favorite team
uv run python src/interfaces/cli.py --all        # Show all games ranked
```

## API Endpoints

Start server: `uv run python src/interfaces/api_server.py`

- `GET /api/health` - Health check
- `GET /api/best-game?days=7&team=LAL` - Best game
- `GET /api/games?days=7&team=LAL` - All games ranked
- `GET /api/config` - Current configuration
- `GET /api/trmnl?days=7&team=LAL` - TRMNL webhook format

Example:
```bash
curl "http://localhost:3000/api/best-game?days=7&team=LAL"
```

## Web Interface

```bash
uv run python src/interfaces/web/app.py
open http://localhost:8080
```

## TRMNL E-ink Display

To preview TRMNL layouts:

```bash
uv run python src/interfaces/web/app.py
open http://localhost:8080/trmnl-viewer
```

## Testing

```bash
# Install test dependencies
uv sync --extra test

# Run all tests with coverage
uv run pytest --cov=src --cov-report=html

# Run without coverage (faster)
uv run pytest --no-cov

# Unit or integration tests only
uv run pytest tests/unit/
uv run pytest tests/integration/

```

**Cache Management:**
Tests use `/tmp/nba_cache` by default.
```bash
# Clear cache
rm -rf /tmp/nba_cache

# Check cache
ls -lh /tmp/nba_cache/scoreboards/
```

## Configuration

See `config.yaml`

## Claude.md

See `claude.md` for detailed technical documentation.
