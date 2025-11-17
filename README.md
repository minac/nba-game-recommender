# NBA Game Recommender

Finds the most engaging NBA game from the past week using real NBA API data. Scores games based on lead changes, closeness, star power, and top teams.

## Quick Start

```bash
# Install
uv sync

# Run CLI
uv run python src/interfaces/cli.py

# Run API server
uv run python src/interfaces/api_server.py

# Run web interface
uv run python src/interfaces/web/app.py
```

## Commands

### CLI
```bash
uv run python src/interfaces/cli.py              # Best game, last 7 days
uv run python src/interfaces/cli.py -d 3         # Last 3 days
uv run python src/interfaces/cli.py -t LAL       # Set favorite team
uv run python src/interfaces/cli.py --all        # Show all games ranked
```

### API Server (localhost:3000)
```bash
uv run python src/interfaces/api_server.py
curl "http://localhost:3000/api/best-game?days=7&team=LAL"
```

**Endpoints**: `/api/health`, `/api/best-game`, `/api/games`, `/api/config`, `/api/trmnl`

### Web Interface (localhost:8080)
```bash
uv run python src/interfaces/web/app.py
# Open http://localhost:8080
```

### TRMNL Screen Viewer
Preview TRMNL layouts before deploying. Start web server, then visit:
```
http://localhost:8080/trmnl-viewer
```

### TRMNL E-ink Display
See [trmnl/README.md](trmnl/README.md) for setup. Deploy to Railway, then use:
```
https://your-app.railway.app/api/trmnl?days=7&team=LAL
```

## Testing

```bash
uv sync --extra test              # Install test dependencies
uv run pytest                     # Run all tests
uv run pytest --no-cov           # Skip coverage
uv run pytest tests/unit/        # Unit tests only
```

See [tests/README.md](tests/README.md) for details.

## Deploy to Railway

```bash
# Web UI: Connect GitHub repo at railway.com
# Or CLI:
npm install -g @railway/cli
railway login
railway init
railway up
```

## Config

Edit `config.yaml` for favorite team and scoring weights.

## Requirements

Python 3.11+ with [uv](https://github.com/astral-sh/uv)
