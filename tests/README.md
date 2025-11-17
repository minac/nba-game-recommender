# Tests

Uses real NBA API calls for normal tests, mocks only for error conditions. Uses real file I/O for cache tests.

## Commands

```bash
# Install dependencies
uv sync --extra test

# Run all tests
uv run pytest

# Run without coverage (faster)
uv run pytest --no-cov

# Specific categories
uv run pytest tests/unit/              # Unit tests only
uv run pytest tests/integration/       # Integration tests only
uv run pytest -m "not slow"            # Skip slow API tests

# With coverage reports
uv run pytest --cov=src --cov-report=html
uv run pytest --cov=src --cov-report=term-missing
```

## Cache

Tests use `/tmp/nba_cache` to avoid rate limiting and speed up execution.

```bash
# Clear cache
rm -rf /tmp/nba_cache

# Check cache
ls -lh /tmp/nba_cache/scoreboards/
ls -lh /tmp/nba_cache/games/
```

## Test Coverage

125+ tests across:
- `tests/unit/test_game_scorer.py` - Scoring algorithm
- `tests/unit/test_nba_client.py` - NBA API client (real API)
- `tests/unit/test_cache.py` - Cache (real file I/O)
- `tests/unit/test_recommender.py` - Game recommender
- `tests/integration/test_api_server.py` - Flask API
- `tests/integration/test_cli.py` - CLI interface
