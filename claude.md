# Claude.md - NBA Game Recommender

This document provides context for Claude (or any AI assistant/developer) working with the NBA Game Recommender codebase.

## Project Overview

This is a modular NBA game recommendation system that finds the most engaging game from the past week based on multiple scoring criteria. The system can be used via CLI, REST API, or web interface.

**Core Purpose**: Analyze NBA games and recommend the most exciting one to watch based on engagement factors like star power, game closeness, and team quality.

## Architecture

### Modular Design

The project follows a clean, modular architecture with clear separation of concerns:

```
src/
├── core/              # Business logic
│   ├── game_scorer.py      # Scoring algorithm implementation
│   └── recommender.py      # Main recommendation engine
├── api/               # External data access
│   └── nba_client.py       # Ball Don't Lie API client with caching
├── utils/             # Shared utilities
│   ├── logger.py           # Centralized logging configuration
│   └── cache.py            # Date-based caching system
└── interfaces/        # User-facing interfaces
    ├── cli.py              # Command-line interface
    ├── api_server.py       # REST API (Flask)
    └── web/
        └── app.py          # Web application
```

### Key Components

1. **GameScorer** (`src/core/game_scorer.py`)
   - Implements the scoring algorithm
   - Configurable weights for different criteria
   - Pure scoring logic, no side effects
   - Returns score + detailed breakdown

2. **GameRecommender** (`src/core/recommender.py`)
   - Orchestrates the recommendation process
   - Fetches games, applies scoring, ranks results
   - Manages configuration loading

3. **NBAClient** (`src/api/nba_client.py`)
   - Handles all Ball Don't Lie API interactions
   - Fetches game schedules, scores, standings, and season leaders
   - Manages API rate limiting (100 requests/min) and error handling
   - Integrated with DateBasedCache for performance
   - Dynamically fetches top 5 teams from standings
   - Dynamically fetches star players from season leaders (top 30 scorers)

4. **DateBasedCache** (`src/utils/cache.py`)
   - File-based caching system for NBA game data
   - Organizes cache by date (scoreboards) and game ID (game details)
   - Configurable TTL (time-to-live) per cache type
   - Automatic cleanup of expired cache entries
   - Significantly reduces API calls and improves performance

5. **Logger** (`src/utils/logger.py`)
   - Centralized logging configuration
   - Structured logging with consistent formatting
   - Configurable log levels (DEBUG, INFO, WARNING, ERROR)
   - Used throughout the application for debugging and monitoring

6. **Interfaces** (`src/interfaces/`)
   - Four separate interfaces sharing the same core logic
   - Each can be run independently
   - CLI, REST API, Web UI, and TRMNL e-ink plugin

### Complete File Structure

```
nba-most-engaging-game-of-the-week/
├── src/
│   ├── __init__.py
│   ├── core/                       # Business logic layer
│   │   ├── __init__.py
│   │   ├── game_scorer.py          # Scoring algorithm (6 criteria)
│   │   └── recommender.py          # Recommendation orchestration
│   ├── api/                        # External API integration
│   │   ├── __init__.py
│   │   └── nba_client.py           # Ball Don't Lie API client + caching
│   ├── utils/                      # Shared utilities
│   │   ├── __init__.py
│   │   ├── logger.py               # Centralized logging setup
│   │   └── cache.py                # Date-based file caching
│   └── interfaces/                 # User-facing interfaces
│       ├── __init__.py
│       ├── cli.py                  # Command-line interface
│       ├── api_server.py           # REST API (Flask)
│       └── web/
│           ├── app.py              # Web application
│           └── templates/
│               └── index.html      # Web UI template
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest configuration
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── sample_data.py          # Shared test data
│   ├── unit/                       # Unit tests
│   │   ├── __init__.py
│   │   ├── test_game_scorer.py
│   │   ├── test_recommender.py
│   │   ├── test_nba_client.py
│   │   └── test_cache.py
│   └── integration/                # Integration tests
│       ├── __init__.py
│       ├── test_cli.py
│       └── test_api_server.py
├── trmnl/                          # TRMNL e-ink plugin
│   ├── README.md                   # TRMNL setup guide
│   ├── .trmnlp.yml                 # Local dev config
│   └── src/
│       ├── settings.yml            # Plugin settings
│       ├── shared.liquid           # Shared template components
│       ├── full.liquid             # Full screen layout
│       ├── half_horizontal.liquid  # Half screen horizontal
│       ├── half_vertical.liquid    # Half screen vertical
│       └── quadrant.liquid         # Quarter screen
├── config.yaml                     # Configuration (scoring, cache, API)
├── pyproject.toml                  # Python dependencies (uv)
├── README.md                       # User-facing documentation
├── claude.md                       # AI assistant context (this file)
├── .python-version                 # Python 3.11
├── render.yaml                     # Render deployment config
└── Procfile                        # Process definition (legacy)
```

**Key Points:**
- **Separation of concerns**: Core logic, API, utilities, interfaces all separate
- **Test coverage**: Unit tests for components, integration tests for interfaces
- **Multiple interfaces**: CLI, API, Web, TRMNL - all use same core
- **Configuration-driven**: Single config.yaml controls all behavior
- **Production-ready**: Deployment configs for Render included

## Scoring Algorithm

The engagement score is calculated using 5 criteria (see `src/core/game_scorer.py`):

1. **Top 5 Teams** (default: 20 pts per team)
   - Bonus for games featuring elite teams
   - Dynamically fetched from Ball Don't Lie standings API

2. **Game Closeness** (default: up to 50 pts)
   - Based on final margin
   - 0-3 pts: 50 pts
   - 4-5 pts: 40 pts
   - 6-10 pts: 25 pts
   - 11-15 pts: 12.5 pts
   - 15+ pts: 0 pts

3. **Total Points Threshold** (default: 200+)
   - 90% penalty if below threshold

4. **Star Power** (default: 20 pts per star)
   - Counts star players participating
   - Dynamically fetched from Ball Don't Lie season leaders API (top 30 scorers)

5. **Favorite Team** (default: 100 pts)
   - Bonus if user's favorite team played

## Configuration

All configuration is in `config.yaml`:

- **Scoring weights**: Customize how each criterion is weighted
- **Favorite team**: Set user preference
- **API/Web settings**: Host, port, debug mode
- **Cache settings**: Enable/disable caching, TTL configuration, auto-cleanup

### Configuration Sections

```yaml
favorite_team: "LAL"  # or null for no favorite

scoring:
  top5_team_bonus: 20
  close_game_bonus: 50
  min_total_points: 200
  star_power_weight: 20
  favorite_team_bonus: 100

cache:
  enabled: true                    # Enable/disable caching
  directory: "/tmp/nba_cache"      # Cache storage location
  scoreboard_ttl_days: 30          # Cache duration for scoreboards
  game_details_ttl_days: 30        # Cache duration for game details
  auto_cleanup: true               # Auto-remove expired cache on startup

nba_api:
  api_key: null                    # Ball Don't Lie API key (or use BALLDONTLIE_API_KEY env var)

api:
  host: "0.0.0.0"
  port: 3000
  debug: false

web:
  host: "0.0.0.0"
  port: 8080
```

When making changes:
- Always validate scoring weights are positive numbers
- Team abbreviations must be valid NBA team codes (3 letters)
- Cache TTL should be at least 1 day (completed games don't change)
- Changes take effect on next application start (no hot reload)

## Development Patterns

### Adding New Scoring Criteria

1. Update `config.yaml` with new weight parameter
2. Modify `GameScorer.__init__()` to load the weight
3. Add scoring logic in `GameScorer.score_game()`
4. Update breakdown dictionary with new criterion
5. Update README.md documentation

### Adding New Data Points

1. Check if Ball Don't Lie API supports the new data point
2. Modify `NBAClient` methods to fetch new data (or add heuristic if unavailable)
3. Update game dictionary structure in `recommender.py`
3. Make data available to `GameScorer.score_game()`
4. Consider caching implications

### Adding New Interfaces

1. Create new file in `src/interfaces/`
2. Import and use `GameRecommender` from `src/core/recommender.py`
3. Call `recommender.get_best_game()` or `recommender.get_ranked_games()`
4. Format output appropriately for the interface
5. Add run script (optional)

## Important Files

- **config.yaml**: All configuration, scoring weights, API settings, cache settings
- **src/core/game_scorer.py**: Complete scoring algorithm implementation
- **src/core/recommender.py**: Main orchestration logic
- **src/api/nba_client.py**: NBA API integration with caching
- **src/utils/cache.py**: Date-based caching system
- **src/utils/logger.py**: Centralized logging configuration
- **pyproject.toml**: Python dependencies (uv)
- **trmnl/**: TRMNL e-ink display plugin with multiple layouts

## Working with the Codebase

**IMPORTANT**: This project uses `uv` for all package management and Python execution. **Always use `uv` - never use `pip`, `pip3`, `python`, or `python3` directly.**

### Running the Application

```bash
# Install dependencies first
uv sync

# Install with testing dependencies
uv sync --extra test

# CLI
uv run python src/interfaces/cli.py

# API Server
uv run python src/interfaces/api_server.py

# Web Interface
uv run python src/interfaces/web/app.py
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_game_scorer.py

# Run only unit or integration tests
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### Common Tasks

**Modify scoring weights**:
- Edit `config.yaml` scoring section
- No code changes needed

**Change favorite team**:
- Edit `config.yaml` favorite_team field
- Or use CLI flag: `--team LAL`

**Add new API endpoint**:
- Add route in `src/interfaces/api_server.py`
- Use existing `recommender` instance
- Return JSON response

**Debug scoring**:
- Check `breakdown` in returned score dictionary
- Each criterion shows its contribution
- Look for penalty application

### Data Flow

1. User request (via CLI/API/Web/TRMNL) → Interface layer
2. Interface calls `GameRecommender.get_best_game(days, favorite_team)`
3. Recommender calls `NBAClient` to fetch games
4. NBAClient checks `DateBasedCache` for cached data
   - **Cache HIT**: Returns cached data (fast, no API call)
   - **Cache MISS**: Fetches from Ball Don't Lie API, caches result
5. For each game, `GameScorer.score_game()` calculates engagement score
6. Games sorted by score
7. Result formatted and returned to user

### Caching System

The caching system dramatically improves performance and reduces API load:

**How It Works:**
- **Two-tier cache**: Scoreboards (by date) and Game Details (by game ID)
- **File-based storage**: JSON files in `/tmp/nba_cache/` (or custom directory)
- **Configurable TTL**: Default 30 days for completed games
- **Auto-cleanup**: Removes expired cache entries on startup (if enabled)

**Cache Structure:**
```
/tmp/nba_cache/
├── scoreboards/
│   ├── 2024-01-15.json    # All games on this date
│   ├── 2024-01-16.json
│   └── ...
└── games/
    ├── 0022300123.json    # Game-specific details
    ├── 0022300124.json
    └── ...
```

**When to Clear Cache:**
- Manually: Call `cache.clear_all()` or delete cache directory
- Auto: Set `auto_cleanup: true` in config.yaml
- Programmatically: Use `cache.clear_expired(ttl_days)`

**Cache Statistics:**
- Check cache stats: `cache.get_cache_stats()` returns entry counts and size
- Useful for monitoring and debugging

**Performance Impact:**
- **Without cache**: ~2-5 seconds per game (API latency)
- **With cache**: ~0.01 seconds (file read)
- **Ideal for**: Historical game queries, repeated lookups, TRMNL polling

### TRMNL Integration

The project includes a complete e-ink display plugin for TRMNL devices:

**What is TRMNL?**
- E-ink display device for personal dashboards
- Automatically polls configured endpoints
- Displays data in a low-power, always-on format
- See: https://usetrmnl.com/

**API Endpoint:**
- `GET /api/trmnl?days=7&team=LAL`
- Returns JSON in TRMNL webhook format
- Includes `merge_variables` for Liquid template rendering
- Designed for hourly polling by TRMNL device

**Available Layouts** (`trmnl/src/`):
1. **full.liquid** - Full screen layout with complete game details and breakdown
2. **half_horizontal.liquid** - Compact horizontal layout for half-screen display
3. **half_vertical.liquid** - Vertical optimized layout for half-screen display
4. **quadrant.liquid** - Minimal quarter-screen view with essential info only

**Template Variables:**
```liquid
{{ home_team }}           # Team abbreviation (e.g., "LAL")
{{ home_score }}          # Final score
{{ away_team }}
{{ away_score }}
{{ game_date }}           # Formatted date
{{ engagement_score }}    # Overall score
{{ final_margin }}        # Final score margin
{{ star_players }}        # Count
{{ is_favorite }}         # "yes" or "no"
{{ breakdown_* }}         # Individual score components
```

**Setup:**
1. Deploy app to Render (or other hosting service)
2. Create TRMNL Private Plugin with "Polling" strategy
3. Set webhook URL: `https://your-app.com/api/trmnl?days=7&team=LAL`
4. Copy desired layout markup into TRMNL plugin
5. Add to TRMNL playlist

**Testing Locally:**
```bash
# Start the API server
uv run python src/interfaces/api_server.py

# Test the endpoint
curl "http://localhost:3000/api/trmnl?days=7&team=LAL"
```

See `trmnl/README.md` for complete setup instructions and customization guide.

### API Endpoints

The REST API (`src/interfaces/api_server.py`) provides the following endpoints:

**Health Check:**
- `GET /api/health`
- Returns: `{"status": "ok"}`
- Use: Service health monitoring

**Best Game:**
- `GET /api/best-game?days=7&team=LAL`
- Query params:
  - `days` (int, 1-30): Lookback period (default: 7)
  - `team` (str, optional): Favorite team abbreviation
- Returns: Best game with engagement score and breakdown
- Example:
  ```json
  {
    "success": true,
    "data": {
      "game_id": "0022300123",
      "home_team": "LAL",
      "away_team": "BOS",
      "score": 425.5,
      "breakdown": {...}
    }
  }
  ```

**All Games Ranked:**
- `GET /api/games?days=7&team=LAL`
- Query params: Same as `/api/best-game`
- Returns: All games sorted by engagement score
- Example:
  ```json
  {
    "success": true,
    "count": 15,
    "data": [...]
  }
  ```

**Configuration:**
- `GET /api/config`
- Returns: Current configuration from config.yaml
- Useful for debugging and configuration verification

**TRMNL Webhook:**
- `GET /api/trmnl?days=7&team=LAL`
- Query params: Same as `/api/best-game`
- Returns: TRMNL-compatible JSON with merge_variables
- Designed for TRMNL device polling
- Example:
  ```json
  {
    "merge_variables": {
      "home_team": "LAL",
      "home_score": 118,
      "away_team": "BOS",
      "away_score": 115,
      "engagement_score": 425.5,
      "is_favorite": "yes"
    }
  }
  ```

**Testing API Locally:**
```bash
# Start server
uv run python src/interfaces/api_server.py

# Test endpoints
curl http://localhost:3000/api/health
curl "http://localhost:3000/api/best-game?days=7&team=LAL"
curl "http://localhost:3000/api/trmnl?days=7&team=BOS"
```

### Error Handling

- NBA API errors are caught and logged in `NBAClient`
- Configuration validation happens at startup
- Missing game data falls back to defaults
- Top teams and star players fall back to reasonable defaults if API fails
- Invalid team abbreviations are handled gracefully
- Cache errors are logged but don't block execution (falls back to API)

## Testing

### Test Suite

The project includes comprehensive test coverage:

**Unit Tests** (`tests/unit/`):
- `test_game_scorer.py` - Tests scoring algorithm logic
- `test_recommender.py` - Tests recommendation engine
- `test_nba_client.py` - Tests NBA API client with mocking

**Integration Tests** (`tests/integration/`):
- `test_cli.py` - Tests CLI interface end-to-end
- `test_api_server.py` - Tests REST API endpoints

**Fixtures** (`tests/fixtures/`):
- `sample_data.py` - Shared test data for consistent testing

### Running Tests

```bash
# Install test dependencies
uv sync --extra test

# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=html
```

### Testing Best Practices

When testing or debugging:

1. **Mock NBA API**: Responses can be slow/unreliable; tests use `responses` library for mocking
2. **Test with various dates**: Use `freezegun` to test different time periods
3. **Edge cases**: Tests cover no games in date range, API failures, missing data
4. **Scoring edge cases**: Tests include tied games, blowouts, low-scoring games
5. **Use fixtures**: Leverage `tests/fixtures/sample_data.py` for consistent test data

## Code Style

- Python 3.7+ syntax
- Docstrings on all classes and public methods
- Type hints where helpful (Dict, Optional, etc.)
- Configuration over hardcoding
- Clear variable names (avoid abbreviations except standard NBA terms)

## Dependencies

**Production Dependencies**:
- **requests**: Ball Don't Lie API calls
- **flask**: REST API and web interface
- **pyyaml**: Configuration file parsing
- **python-dateutil**: Date manipulation
- **gunicorn**: Production WSGI server
- **python-dotenv**: Environment variable loading

**Built-in Utilities** (no external deps):
- **src.utils.logger**: Centralized logging (uses stdlib logging)
- **src.utils.cache**: File-based caching (uses stdlib json, pathlib)

**Test Dependencies** (optional):
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **responses**: HTTP response mocking
- **freezegun**: Time/date mocking

All managed in `pyproject.toml` using **uv only** (never use pip):
- Install production only: `uv sync`
- Install with tests: `uv sync --extra test`
- Add new dependency: `uv add <package>`
- Remove dependency: `uv remove <package>`

## Future Enhancement Ideas

Consider these when adding features:
- ✅ **Caching game data to reduce API calls** (IMPLEMENTED)
- ✅ **TRMNL e-ink display integration** (IMPLEMENTED)
- Historical game database (persistent storage beyond file cache)
- Machine learning to personalize scoring weights
- Social features (what friends are watching)
- Live game recommendations during season
- Playoff importance factor
- Player injury impact on star power
- Advanced metrics (offensive rating, pace, etc.) - **Note**: Limited by Ball Don't Lie API capabilities
- Cache warming (pre-cache upcoming games)
- Redis/memcached for distributed caching
- ✅ **Dynamic top teams/star players** (IMPLEMENTED) - Fetched from Ball Don't Lie standings and leaders APIs

## Tips for Claude

1. **ALWAYS use uv**: Never use `pip`, `pip3`, `python`, or `python3` directly. Always use `uv sync` for dependencies and `uv run python` for execution

2. **Use the logger utility**: Import and use `get_logger(__name__)` from `src.utils.logger` for all logging
   - Don't use `print()` statements in production code
   - Use appropriate log levels: DEBUG, INFO, WARNING, ERROR
   - Logger is already configured with consistent formatting

3. **Understand the caching layer**:
   - Cache is automatically used by `NBAClient`
   - Completed games are cached for 30 days by default
   - Check cache config in `config.yaml` before modifying
   - Cache significantly improves performance for historical queries
   - Don't bypass cache unless absolutely necessary

4. **Read config first**: Always check `config.yaml` to understand current settings
   - Includes scoring weights, cache settings, API config, favorite team

5. **Follow the architecture**: Keep core logic in `src/core/`, interfaces separate, utilities in `src/utils/`

6. **Preserve modularity**: Changes should work across all interfaces (CLI, API, Web, TRMNL)

7. **Update documentation**: If changing scoring, update README.md and claude.md

8. **Test all interfaces**: A change to core logic affects all four interfaces

9. **Run tests**: Use `uv run pytest` to verify changes don't break existing functionality
   - Tests include cache testing (`tests/unit/test_cache.py`)

10. **Check game data structure**: Look at what `NBAClient` returns before using it

11. **Scoring is configurable**: Don't hardcode values, use config weights

12. **TRMNL integration**: If modifying game data structure, verify TRMNL endpoint still works
    - Test endpoint: `/api/trmnl?days=7&team=LAL`
    - Ensure all merge_variables are present in response

13. **Cache debugging**: If data seems stale, check cache stats or clear cache
    - Cache location: `/tmp/nba_cache/` (or `config.yaml` setting)
    - Clear manually: `rm -rf /tmp/nba_cache/`
