# NBA Game Recommender

Recommends the most engaging NBA game from the past week. Scores games on closeness, star power, top teams, and AI-detected online buzz. Supports CLI, REST API, Web UI, and TRMNL e-ink display.

## Architecture

```
src/
├── core/
│   ├── buzz_scorer.py      # AI buzz scoring via Claude API
│   ├── game_scorer.py      # Scoring algorithm (6 criteria)
│   └── recommender.py      # Orchestration
├── api/
│   └── nba_api_client.py   # nba_api + SQLite caching
├── utils/
│   ├── logger.py           # Centralized logging
│   └── database.py         # SQLite database
├── services/
│   └── game_service.py     # Business logic layer
└── interfaces/
    ├── cli.py              # Command-line
    ├── sync_cli.py         # Data sync CLI
    └── web/
        └── app.py          # Flask API + Web UI

trmnl/src/                  # Liquid templates for e-ink
```

## Scoring Algorithm

1. **Top 5 Teams** (20 pts/team) - From standings
2. **Close Game** (up to 50 pts) - Based on margin
3. **High Score** (10 pts) - If total >= 200
4. **Star Power** (20 pts/star) - Top 30 scorers
5. **Favorite Team** (20 pts) - User preference
6. **AI Buzz** (up to 40 pts) - Claude API + web search for online buzz/excitement

Weights configurable in `config.yaml`.

## Data Flow

1. Sync: `uv run python src/interfaces/sync_cli.py`
2. Request → Recommender → NBAClient → SQLite
3. GameScorer scores each game
4. Return sorted results

## API Endpoints

- `GET /api/health` - Health check
- `POST /recommend` - Best game or all ranked
- `GET /api/trmnl?days=7&team=LAL` - TRMNL webhook
- `POST /api/sync` - Trigger data sync (protected by X-Sync-Token header)

### Examples

```bash
# Health check
curl http://localhost:8080/api/health

# Get best game from last 7 days
curl -X POST http://localhost:8080/recommend \
  -H "Content-Type: application/json" \
  -d '{"days": 7}'

# With favorite team and all results
curl -X POST http://localhost:8080/recommend \
  -H "Content-Type: application/json" \
  -d '{"days": 7, "favorite_team": "LAL", "show_all": true}'
```

## Database

SQLite at `data/nba_games.db`:

- `teams`, `standings`, `players`, `games`, `game_players`, `game_buzz`, `sync_log`

Clear and resync: `rm data/nba_games.db && uv run python src/interfaces/sync_cli.py`

## TRMNL Integration

Liquid templates in `trmnl/src/`: `full.liquid`, `half_horizontal.liquid`, `half_vertical.liquid`, `quadrant.liquid`

## Environment Variables

- `DATABASE_PATH` - SQLite database path (default: `data/nba_games.db`, production: `/data/nba_games.db`)
- `SYNC_TOKEN` - Authentication token for `/api/sync` endpoint (production only)
- `ANTHROPIC_API_KEY` - Anthropic API key for AI buzz scoring (optional; locally reads from macOS keychain `anthropic-api-key`)

## Project-Specific Notes

- Sync data before first use: `uv run python src/interfaces/sync_cli.py`
- Use `get_logger(__name__)` from `src.utils.logger`
- All scoring weights in `config.yaml`
- Production runs on Render with persistent disk at `/data` for SQLite database
