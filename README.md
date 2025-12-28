# NBA Game Recommender

Finds the most engaging NBA game from the past week. Scores games based on closeness, star players, top teams, your favorite team, and high-scoring games (200+ points).

## Features

- **Multiple Interfaces**: CLI, REST API, Web UI, TRMNL E-ink Display
- **Free Data**: Uses nba_api (scrapes NBA.com, no API key needed)
- **Fast**: SQLite database for instant queries after initial sync

## Quick Start

```bash
# Install dependencies
uv sync

# Sync NBA data (required before first use)
uv run python src/interfaces/sync_cli.py

# Run CLI
uv run python src/interfaces/cli.py

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

Start server: `uv run python src/interfaces/web/app.py`

- `GET /api/health` - Health check
- `POST /recommend` - Get best game or all games ranked (JSON body)
- `GET /api/trmnl?days=7&team=LAL` - TRMNL webhook format

Example:

```bash
# Best game
curl -X POST http://localhost:8080/recommend \
  -H "Content-Type: application/json" \
  -d '{"days": 7, "favorite_team": "LAL"}'

# All games ranked
curl -X POST http://localhost:8080/recommend \
  -H "Content-Type: application/json" \
  -d '{"days": 7, "show_all": true}'
```

## TRMNL E-ink Display

The `/api/trmnl` endpoint returns data formatted for TRMNL's polling strategy. Liquid templates in `trmnl/src/`.

## Testing

### Automated Tests (115 tests)

```bash
# Install test dependencies
uv sync --extra test

# Run all tests
uv run pytest

# Unit or integration tests only
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### Manual Testing

**Sync CLI** - Data synchronization:

```bash
uv run python src/interfaces/sync_cli.py --status    # Check sync status
uv run python src/interfaces/sync_cli.py --days 7    # Sync last 7 days
uv run python src/interfaces/sync_cli.py --metadata-only  # Sync teams/standings only
```

**Main CLI** - Game recommendations:

```bash
uv run python src/interfaces/cli.py              # Best game (last 7 days)
uv run python src/interfaces/cli.py -d 3         # Last 3 days
uv run python src/interfaces/cli.py -t LAL       # With favorite team
uv run python src/interfaces/cli.py --all        # All games ranked
uv run python src/interfaces/cli.py --explain    # Detailed scoring breakdown
uv run python src/interfaces/cli.py --list-stars # Show tracked star players
uv run python src/interfaces/cli.py --top-teams  # Show top 5 teams
```

**Web UI** - Browser interface:

```bash
uv run python src/interfaces/web/app.py
# Open http://localhost:8080 in browser
# Click "Find Game" to get recommendation
```

**REST API** - HTTP endpoints:

```bash
# Start server first
uv run python src/interfaces/web/app.py &

# Test endpoints
curl http://localhost:8080/api/health
curl -X POST http://localhost:8080/recommend -H "Content-Type: application/json" -d '{"days": 7}'
curl -X POST http://localhost:8080/recommend -H "Content-Type: application/json" -d '{"days": 7, "favorite_team": "LAL"}'
curl -X POST http://localhost:8080/recommend -H "Content-Type: application/json" -d '{"days": 3, "show_all": true}'
curl "http://localhost:8080/api/trmnl?days=7"
```

## Database

Data stored in SQLite (`data/nba_games.db` locally, `/data/nba_games.db` on Render).

**Local refresh:**

```bash
uv run python src/interfaces/sync_cli.py           # Full sync
uv run python src/interfaces/sync_cli.py --games-only  # Games only
rm data/nba_games.db && uv run python src/interfaces/sync_cli.py  # Reset
```

**Production (Render):** Data syncs automatically daily at 9am UTC via cron job. The web service has a persistent disk so data survives restarts.

## Configuration

See `config.yaml` for scoring weights and settings.

## Documentation

See `CLAUDE.md` for technical documentation.
