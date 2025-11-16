# Claude.md - NBA Game Recommender

This document provides context for Claude (or any AI assistant/developer) working with the NBA Game Recommender codebase.

## Project Overview

This is a modular NBA game recommendation system that finds the most engaging game from the past week based on multiple scoring criteria. The system can be used via CLI, REST API, or web interface.

**Core Purpose**: Analyze NBA games and recommend the most exciting one to watch based on engagement factors like lead changes, star power, game closeness, and team quality.

## Architecture

### Modular Design

The project follows a clean, modular architecture with clear separation of concerns:

```
src/
├── core/              # Business logic
│   ├── game_scorer.py      # Scoring algorithm implementation
│   └── recommender.py      # Main recommendation engine
├── api/               # External data access
│   └── nba_client.py       # NBA Stats API client
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
   - Handles all NBA Stats API interactions
   - Fetches game schedules, box scores, standings
   - Manages API rate limiting and error handling

4. **Interfaces** (`src/interfaces/`)
   - Three separate interfaces sharing the same core logic
   - Each can be run independently
   - CLI, REST API, and Web UI

## Scoring Algorithm

The engagement score is calculated using 6 criteria (see `src/core/game_scorer.py:22-123`):

1. **Lead Changes** (configurable weight, default: 10 pts each)
   - More lead changes = more exciting game

2. **Top 5 Teams** (default: 50 pts per team)
   - Bonus for games featuring elite teams

3. **Game Closeness** (default: up to 100 pts)
   - 0-3 pts: 100 pts
   - 4-5 pts: 80 pts
   - 6-10 pts: 50 pts
   - 11-15 pts: 25 pts
   - 15+ pts: 0 pts

4. **Total Points Threshold** (default: 200+)
   - 90% penalty if below threshold

5. **Star Power** (default: 20 pts per star)
   - Counts star players participating

6. **Favorite Team** (default: 75 pts)
   - Bonus if user's favorite team played

## Configuration

All configuration is in `config.yaml`:

- **Scoring weights**: Customize how each criterion is weighted
- **Favorite team**: Set user preference
- **API/Web settings**: Host, port, debug mode

When making changes:
- Always validate scoring weights are positive numbers
- Team abbreviations must be valid NBA team codes (3 letters)
- Changes take effect on next application start (no hot reload)

## Development Patterns

### Adding New Scoring Criteria

1. Update `config.yaml` with new weight parameter
2. Modify `GameScorer.__init__()` to load the weight
3. Add scoring logic in `GameScorer.score_game()`
4. Update breakdown dictionary with new criterion
5. Update README.md documentation

### Adding New Data Points

1. Modify `NBAClient` methods to fetch new data
2. Update game dictionary structure in `recommender.py`
3. Make data available to `GameScorer.score_game()`
4. Consider caching implications

### Adding New Interfaces

1. Create new file in `src/interfaces/`
2. Import and use `GameRecommender` from `src/core/recommender.py`
3. Call `recommender.get_best_game()` or `recommender.get_ranked_games()`
4. Format output appropriately for the interface
5. Add run script (optional)

## Important Files

- **config.yaml**: All configuration, scoring weights, API settings
- **src/core/game_scorer.py**: Complete scoring algorithm implementation
- **src/core/recommender.py**: Main orchestration logic
- **src/api/nba_client.py**: NBA API integration
- **pyproject.toml**: Python dependencies (uv)

## Working with the Codebase

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

1. User request (via CLI/API/Web) → Interface layer
2. Interface calls `GameRecommender.get_best_game(days, favorite_team)`
3. Recommender calls `NBAClient` to fetch games
4. For each game, `GameScorer.score_game()` calculates engagement score
5. Games sorted by score
6. Result formatted and returned to user

### Error Handling

- NBA API errors are caught and logged in `NBAClient`
- Configuration validation happens at startup
- Missing game data falls back to defaults (0 lead changes, etc.)
- Invalid team abbreviations are handled gracefully

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
- **requests**: NBA API calls
- **flask**: REST API and web interface
- **pyyaml**: Configuration file parsing
- **python-dateutil**: Date manipulation
- **gunicorn**: Production WSGI server

**Test Dependencies** (optional):
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **responses**: HTTP response mocking
- **freezegun**: Time/date mocking

All managed in `pyproject.toml`:
- Install production only: `uv sync`
- Install with tests: `uv sync --extra test`

## Future Enhancement Ideas

Consider these when adding features:
- Caching game data to reduce API calls
- Historical game database for faster queries
- Machine learning to personalize scoring weights
- Social features (what friends are watching)
- Live game recommendations during season
- Playoff importance factor
- Player injury impact on star power
- Advanced metrics (offensive rating, pace, etc.)

## Tips for Claude

1. **Read config first**: Always check `config.yaml` to understand current settings
2. **Follow the architecture**: Keep core logic in `src/core/`, interfaces separate
3. **Preserve modularity**: Changes should work across all interfaces (CLI, API, Web)
4. **Update documentation**: If changing scoring, update README.md
5. **Test all interfaces**: A change to core logic affects all three interfaces
6. **Run tests**: Use `uv run pytest` to verify changes don't break existing functionality
7. **Check game data structure**: Look at what `NBAClient` returns before using it
8. **Scoring is configurable**: Don't hardcode values, use config weights
9. **Use uv for dependencies**: All package management is done via `uv`, not pip
