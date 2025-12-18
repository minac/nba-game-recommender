# Claude.md - NBA Game Recommender Technical Guide

Technical documentation for developers and AI assistants working with the NBA Game Recommender codebase.

## Project Overview

Modular NBA game recommendation system that analyzes past week's games using nba_api (free, scrapes NBA.com). Scores games on engagement factors (closeness, star power, top teams) and ranks them. Supports CLI, REST API, Web UI, and TRMNL e-ink display.

## Architecture

### Modular Design

```
src/
├── core/              # Business logic
│   ├── game_scorer.py      # Scoring algorithm (5 criteria)
│   └── recommender.py      # Orchestration
├── api/
│   └── nba_api_client.py   # nba_api client + SQLite caching
├── utils/
│   ├── logger.py           # Centralized logging
│   └── database.py         # SQLite database
└── interfaces/
    ├── cli.py              # Command-line
    ├── sync_cli.py         # Data sync CLI
    ├── api_server.py       # REST API (Flask)
    └── web/app.py          # Web UI

trmnl/src/            # Liquid templates for e-ink
tests/                # Unit + integration tests
```

### Key Components

**GameScorer** (`src/core/game_scorer.py`)

- Pure scoring logic, no side effects
- Configurable weights from `config.yaml`
- Returns score + detailed breakdown

**GameRecommender** (`src/core/recommender.py`)

- Fetches games via NBAClient
- Applies GameScorer to each game
- Returns sorted results

**NBAClient** (`src/api/nba_api_client.py`)

- Uses nba_api library (free, scrapes NBA.com)
- Data stored in local SQLite database
- No API key required

**NBASyncService** (`src/api/nba_api_client.py`)

- Syncs teams, standings, star players, and games to database
- Run via `sync_cli.py` before using recommendations

**NBADatabase** (`src/utils/database.py`)

- SQLite database for persistent storage
- Tables: teams, standings, players, games, game_players, sync_log
- Fast queries, no rate limits after sync

**Logger** (`src/utils/logger.py`)

- Centralized config using stdlib logging
- Consistent formatting across all modules

## Scoring Algorithm

See `src/core/game_scorer.py`:

1. **Top 5 Teams** (20 pts/team) - From standings in database
2. **Game Closeness** (up to 50 pts) - 0-3 margin: 50pts, 4-5: 40pts, 6-10: 25pts, 11-15: 12.5pts
3. **High Score Bonus** (10 pts) - If total points >= 200
4. **Star Power** (20 pts/star) - Top 30 scorers from database
5. **Favorite Team** (75 pts) - User preference bonus

All weights configurable in `config.yaml`.

## Configuration

Single `config.yaml` controls everything:

```yaml
favorite_team: "GSW"
scoring:
  top5_team_bonus: 20
  close_game_bonus: 50
  min_total_points: 200
  high_score_bonus: 10
  star_power_weight: 20
  favorite_team_bonus: 40
database:
  path: "data/nba_games.db"
```

Changes take effect on restart (no hot reload).

## Data Flow

1. Run sync: `uv run python src/interfaces/sync_cli.py` (populates database)
2. User request → Interface layer (CLI/API/Web/TRMNL)
3. Interface → `GameRecommender.get_best_game(days, team)`
4. Recommender → `NBAClient.get_games_last_n_days()`
5. NBAClient queries SQLite database
6. For each game: `GameScorer.score_game()` calculates score
7. Sort by score, return results

## Development Patterns

### Adding Scoring Criteria

1. Add weight to `config.yaml` scoring section
2. Load in `GameScorer.__init__()`
3. Add logic in `GameScorer.score_game()`
4. Update breakdown dict
5. Update tests

### Adding API Endpoints

1. Add route in `src/interfaces/api_server.py`
2. Use existing `recommender` instance
3. Return JSON response
4. Add integration test

### Syncing New Data

1. Add method to `NBASyncService`
2. Add table/columns to `NBADatabase`
3. Call sync method in `sync_all()`

## Important Files

- `config.yaml` - All configuration
- `src/core/game_scorer.py` - Scoring algorithm
- `src/core/recommender.py` - Main orchestration
- `src/api/nba_api_client.py` - API client + sync service
- `src/utils/database.py` - SQLite database
- `pyproject.toml` - Dependencies (managed by uv)

## Working with the Codebase

**CRITICAL**: Always use `uv` - never use `pip`, `python`, or `python3` directly.

### Common Commands

```bash
# Dependencies
uv sync                    # Install production deps
uv sync --extra test       # Include test deps
uv add <package>           # Add dependency
uv remove <package>        # Remove dependency

# Syncing data (required before first use)
uv run python src/interfaces/sync_cli.py        # Full sync
uv run python src/interfaces/sync_cli.py games  # Games only

# Running
uv run python src/interfaces/cli.py
uv run python src/interfaces/api_server.py
uv run python src/interfaces/web/app.py

# Testing
uv run pytest                          # All tests
uv run pytest --cov=src               # With coverage
uv run pytest tests/unit/             # Unit only
uv run pytest tests/integration/      # Integration only
```

### Database System

**Location:** `data/nba_games.db` (SQLite)

**Tables:**

- `teams` - NBA team info
- `standings` - Current season standings
- `players` - Player info + star status
- `games` - Game results
- `game_players` - Players in each game
- `sync_log` - Sync timestamps

**Management:**

- View: `sqlite3 data/nba_games.db ".tables"`
- Clear: `rm data/nba_games.db && uv run python src/interfaces/sync_cli.py`

### API Endpoints

- `GET /api/health` - Health check
- `GET /api/best-game?days=7&team=LAL` - Best game
- `GET /api/games?days=7&team=LAL` - All ranked
- `GET /api/config` - Current config
- `GET /api/trmnl?days=7&team=LAL` - TRMNL webhook

### TRMNL Integration

E-ink display endpoint returns Liquid template variables:

```json
{
  "game": {...},
  "score": "85.5",
  "breakdown": {
    "top5_teams": {"count": 2, "points": "40.0"},
    "close_game": {"margin": 3, "points": "50.0"},
    "star_power": {"count": 3, "points": "60.0"},
    ...
  }
}
```

Layouts in `trmnl/src/`: `full.liquid`, `half_horizontal.liquid`, `half_vertical.liquid`, `quadrant.liquid`

## Error Handling

- NBA API errors caught and logged in sync service
- Config validation at startup
- Missing data falls back to defaults
- Top teams/stars fall back if database is empty
- Database errors logged with appropriate fallbacks

## Testing

**Test Structure:**

- `tests/unit/` - Component tests (scorer, recommender, database)
- `tests/integration/` - Interface tests (CLI, API)
- `tests/fixtures/` - Shared test data

**Key Practices:**

- Mock database for unit tests
- Use `freezegun` for date mocking
- Test edge cases: no games, empty database, tied games

## Code Style

- Python 3.11+
- Docstrings on classes and public methods
- Type hints (Dict, Optional, etc.)
- Configuration over hardcoding
- Use `get_logger(__name__)` from `src.utils.logger`
- No `print()` in production code

## Dependencies

**Production:**

- nba_api, flask, pyyaml, python-dateutil, gunicorn, python-dotenv

**Test (optional):**

- pytest, pytest-cov, pytest-mock, freezegun

Managed in `pyproject.toml` via uv.

## Tips for AI Assistants

1. **Always use uv** - Never use pip/python directly
2. **Sync data first** - Run sync_cli.py before testing recommendations
3. **Use logger utility** - `get_logger(__name__)` not `print()`
4. **Read config first** - Check `config.yaml` for current settings
5. **Follow architecture** - Keep core in `src/core/`, interfaces separate
6. **Preserve modularity** - Changes work across all interfaces
7. **Run tests** - Use `uv run pytest` to verify changes
8. **Check data structure** - Look at NBAClient returns before using
9. **Scoring is configurable** - Don't hardcode, use config weights
10. **Test TRMNL** - Verify `/api/trmnl` endpoint if changing data structure

## Future Enhancements

- ML for personalized weights
- Live game recommendations
- Playoff importance factor
- Advanced metrics from box scores
