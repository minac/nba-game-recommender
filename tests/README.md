# NBA Game Recommender Tests

This directory contains comprehensive tests for the NBA Game Recommender project.

## Test Structure

```
tests/
├── unit/                      # Unit tests for individual components
│   ├── test_game_scorer.py   # Tests for GameScorer class
│   ├── test_nba_client.py    # Tests for NBAClient class
│   └── test_recommender.py   # Tests for GameRecommender class
├── integration/               # Integration tests
│   ├── test_api_server.py    # Tests for Flask API endpoints
│   └── test_cli.py           # Tests for CLI interface
├── fixtures/                  # Test fixtures and sample data
│   └── sample_data.py        # Reusable test data
└── conftest.py               # Shared pytest fixtures

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=src --cov-report=html
```

### Run specific test categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_game_scorer.py

# Specific test class or function
pytest tests/unit/test_game_scorer.py::TestGameScorer::test_lead_changes_scoring
```

### Run tests with markers
```bash
# Unit tests
pytest -m unit

# Integration tests
pytest -m integration

# API tests
pytest -m api
```

### Run with verbose output
```bash
pytest -v
```

### Run with output capture disabled (see print statements)
```bash
pytest -s
```

## Test Coverage

The test suite aims for high code coverage across all components:

- **GameScorer**: Comprehensive tests for all scoring criteria and edge cases
- **NBAClient**: Tests for API interactions with mocked HTTP responses
- **GameRecommender**: Tests for game ranking and formatting logic
- **API Server**: Integration tests for all endpoints and error handling
- **CLI**: Tests for command-line argument parsing and output

### Viewing Coverage Reports

After running tests with coverage:
```bash
# View in terminal
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html  # Opens coverage report in browser
```

## Test Fixtures

Reusable test data is available in `fixtures/sample_data.py`:

- `get_sample_game()`: Creates sample game data with customizable parameters
- `get_sample_config()`: Provides default scoring configuration
- `get_sample_scoreboard_response()`: Mock NBA API scoreboard response
- `get_sample_playbyplay_response()`: Mock play-by-play data
- `get_sample_boxscore_response()`: Mock box score with star players

## Writing New Tests

### Example Unit Test
```python
from src.core.game_scorer import GameScorer
from tests.fixtures.sample_data import get_sample_game, get_sample_config

def test_score_calculation():
    scorer = GameScorer(get_sample_config())
    game = get_sample_game(lead_changes=10)
    result = scorer.score_game(game)

    assert result['score'] > 0
    assert result['breakdown']['lead_changes']['count'] == 10
```

### Example Integration Test
```python
from src.interfaces.api_server import app

def test_api_endpoint():
    client = app.test_client()
    response = client.get('/api/health')

    assert response.status_code == 200
    assert response.json['status'] == 'ok'
```

## Dependencies

Test dependencies are listed in `requirements.txt`:
- `pytest`: Test framework
- `pytest-cov`: Coverage plugin
- `pytest-mock`: Mocking utilities
- `responses`: HTTP response mocking
- `freezegun`: Time mocking (if needed)

## Continuous Integration

These tests are designed to run in CI/CD pipelines. The pytest configuration in `pytest.ini` ensures consistent behavior across different environments.

## Troubleshooting

### Import Errors
If you encounter import errors, ensure the project root is in your Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Coverage Not Working
Ensure you're running from the project root directory and that `.coveragerc` is present.

### Mock Issues
Make sure to patch at the correct location. For example, patch where the object is used, not where it's defined.
