# BallDontLie Backup Data Source Setup

## Overview

BallDontLie API has been integrated as a backup data source for when the NBA Stats API is unavailable or slow. The system will automatically fallback to BallDontLie when the primary NBA API fails.

## Configuration

### Environment Variable

The BallDontLie API key is stored as an environment variable for security:

```bash
BALLDONTLIE_API_KEY=26d048e1-2af0-4901-8199-5e27de6ad070
```

### Local Development

To use the backup source locally, set the environment variable:

```bash
# In your shell
export BALLDONTLIE_API_KEY=26d048e1-2af0-4901-8199-5e27de6ad070

# Or create a .env file
echo "BALLDONTLIE_API_KEY=26d048e1-2af0-4901-8199-5e27de6ad070" > .env
```

### Render Deployment

1. Go to your Render service dashboard
2. Navigate to **Environment** tab
3. Add a new secret environment variable:
   - **Key**: `BALLDONTLIE_API_KEY`
   - **Value**: `26d048e1-2af0-4901-8199-5e27de6ad070`
4. Save and redeploy

The `render.yaml` file includes this environment variable with `sync: false`, meaning it won't be automatically synced and must be set manually in the Render dashboard for security.

## How It Works

### Automatic Fallback

When `get_games_last_n_days()` is called:

1. **Primary**: Attempts to fetch from NBA Stats API
2. **On Timeout/Error**: Automatically switches to BallDontLie API
3. **If Both Fail**: Raises an error with appropriate message

### Error Handling

- `NBAAPITimeoutError`: Raised when NBA API times out
- `NBAAPIError`: Raised for general NBA API errors
- Both errors trigger the BallDontLie fallback

### Configuration

In `config.yaml`:

```yaml
balldontlie:
  enabled: true  # Enable/disable BallDontLie as backup source
```

Note: The API key is **not** in the config file - it's in the environment variable.

## Limitations

BallDontLie API has some limitations compared to NBA Stats API:

1. **No play-by-play data**: Lead changes are estimated based on final score
2. **No player data**: Star player counts default to 0
3. **Rate limits**: 100 requests per minute

### Lead Change Estimation

Since BallDontLie doesn't provide play-by-play data, lead changes are estimated:

- Very close game (≤3 pts): 15 lead changes
- Close game (≤5 pts): 10 lead changes
- Competitive (≤10 pts): 5 lead changes
- Moderately competitive (≤15 pts): 2 lead changes
- Blowout (>15 pts): 0 lead changes

## Testing

Tests are included to verify the fallback mechanism:

```bash
# Test BallDontLie client
uv run pytest tests/unit/test_balldontlie_client.py -v

# Test fallback mechanism
uv run pytest tests/unit/test_nba_client.py::TestBallDontLieFallback -v
```

## Monitoring

Check logs for fallback usage:

```
WARNING: NBA Stats API failed: <error>. Attempting fallback to BallDontLie...
INFO: Successfully retrieved X games from BallDontLie backup
```

If both sources fail:

```
ERROR: Both primary and backup data sources failed
```

## Disabling Backup

To disable the BallDontLie backup, set in `config.yaml`:

```yaml
balldontlie:
  enabled: false
```
