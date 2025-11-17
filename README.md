# NBA Game Recommender

Find the most engaging NBA game to watch from the past week based on multiple criteria including lead changes, close scores, star power, and more.

## Features

- **Modular Architecture**: Run as CLI, REST API, Web Application, or TRMNL E-ink Display
- **TRMNL Integration**: Display on your e-ink dashboard with multiple layout options
- **Smart Scoring Algorithm**: Evaluates games based on:
  - Lead changes (more exciting)
  - Top 5 team participation
  - Final margin (closer games score higher)
  - Minimum 200 points threshold
  - Star player participation
  - Favorite team bonus
- **Configurable**: Customize scoring weights and preferences via `config.yaml`
- **Real NBA Data**: Fetches actual game data from the NBA Stats API

## Installation

1. Clone the repository:
```bash
git clone https://github.com/minac/nba-most-engaging-game-of-the-week.git
cd nba-most-engaging-game-of-the-week
```

2. Install dependencies:
```bash
uv sync
```

3. Configure your preferences (optional):
```bash
# Edit config.yaml to set your favorite team and adjust scoring weights
```

## Usage

### CLI (Command Line Interface)

Find the best game from the last 7 days:
```bash
uv run python src/interfaces/cli.py
```

Options:
```bash
uv run python src/interfaces/cli.py --help

# Look back 3 days
uv run python src/interfaces/cli.py -d 3

# Set favorite team
uv run python src/interfaces/cli.py -t LAL

# Show all games ranked
uv run python src/interfaces/cli.py --all

# List current star players
uv run python src/interfaces/cli.py --list-stars
```

### REST API

Start the API server:
```bash
uv run python src/interfaces/api_server.py
```

Endpoints:
- `GET /api/health` - Health check
- `GET /api/best-game?days=7&team=LAL` - Get best game
- `GET /api/games?days=7` - Get all games ranked
- `GET /api/config` - Get configuration

Example:
```bash
curl "http://localhost:3000/api/best-game?days=7&team=BOS"
```

### Web Interface

Start the web server:
```bash
uv run python src/interfaces/web/app.py
```

Then open your browser to `http://localhost:8080`

### TRMNL E-ink Display

Display game recommendations on your TRMNL e-ink device!

**Quick Setup**:
1. Deploy this app to Railway or your preferred platform
2. In your TRMNL account, create a Private Plugin with "Polling" strategy
3. Set endpoint to: `https://your-app.railway.app/api/trmnl?days=7&team=LAL`
4. Copy the markup from `trmnl/src/full.liquid` (or other layouts)
5. Add to your TRMNL playlist

**How It Works**:
- Your TRMNL device automatically fetches the best game every hour
- Displays team scores, engagement score, and game breakdown
- Updates with the most exciting games based on the scoring algorithm
- Shows a favorite team indicator when your team plays

**Endpoints**:
- `GET /api/trmnl?days=7&team=LAL` - TRMNL-compatible webhook

**Layouts Available**:
- Full screen (`full.liquid`) - Complete game details and breakdown
- Half horizontal (`half_horizontal.liquid`) - Compact horizontal layout
- Half vertical (`half_vertical.liquid`) - Vertical optimized display
- Quadrant (`quadrant.liquid`) - Minimal quarter-screen view

See [trmnl/README.md](trmnl/README.md) for complete setup instructions, usage guide, and customization options.

## Configuration

Edit `config.yaml` to customize:

```yaml
favorite_team: "LAL"  # Set your favorite team (3-letter code)

scoring:
  lead_changes_weight: 10      # Points per lead change
  top5_team_bonus: 50          # Bonus for top 5 teams
  close_game_bonus: 100        # Max bonus for close games
  min_total_points: 200        # Minimum total points threshold
  star_power_weight: 20        # Points per star player
  favorite_team_bonus: 75      # Bonus if favorite team plays
```

### Data Source

This application uses the NBA Stats API to fetch game data:

- **Free**: No API key required
- **Features**: Full game data including play-by-play for lead changes
- **Limitations**: May be rate-limited, unofficial API

## Scoring Criteria

The engagement score is calculated based on:

1. **Lead Changes** (10 points each)
   - More lead changes = more exciting game

2. **Top 5 Teams** (50 points per team)
   - Games featuring elite teams get bonus points

3. **Game Closeness** (up to 100 points)
   - 0-3 point margin: 100 points
   - 4-5 point margin: 80 points
   - 6-10 point margin: 50 points
   - 11-15 point margin: 25 points
   - 15+ point margin: 0 points

4. **Total Points** (threshold)
   - Games must have 200+ total points
   - Below threshold: 90% score penalty

5. **Star Power** (20 points per star player)
   - Counts participation of star players

6. **Favorite Team** (75 points)
   - Bonus if your favorite team played

## Project Structure

```
nba-most-engaging-game-of-the-week/
├── src/
│   ├── core/
│   │   ├── game_scorer.py      # Scoring algorithm
│   │   └── recommender.py      # Main recommendation engine
│   ├── api/
│   │   └── nba_client.py       # NBA Stats API client
│   └── interfaces/
│       ├── cli.py              # Command-line interface
│       ├── api_server.py       # REST API server
│       └── web/
│           ├── app.py          # Web application
│           └── templates/
│               └── index.html  # Web UI
├── trmnl/                      # TRMNL e-ink plugin
│   ├── src/
│   │   ├── full.liquid         # Full screen layout
│   │   ├── half_horizontal.liquid
│   │   ├── half_vertical.liquid
│   │   ├── quadrant.liquid     # Quarter screen layout
│   │   ├── shared.liquid       # Shared components
│   │   └── settings.yml        # Plugin settings
│   ├── .trmnlp.yml            # Local dev config
│   └── README.md              # TRMNL setup guide
├── config.yaml                 # Configuration file
├── pyproject.toml              # Python dependencies (uv)
└── README.md
```

## Example Output

```
============================================================
🏀 MOST ENGAGING GAME 🏀
============================================================

Lakers @ Celtics
Date: 2024-01-15

Final Score: LAL 118 - 115 BOS

============================================================
ENGAGEMENT SCORE: 425.50
============================================================

Score Breakdown:
  • Lead Changes: 12 (120.0 pts)
  • Top 5 Teams: 2 team(s) (100.0 pts)
  • Game Closeness: 3 pt margin (100.0 pts)
  • Total Points: 233 (threshold: True)
  • Star Players: 4 (80.0 pts)
  • Favorite Team: Yes (75.0 pts)

============================================================
```

## Deployment

### Deploy to Railway

This application is configured for easy deployment to [Railway](https://railway.com/).

#### Quick Deploy

1. **Fork or clone this repository**

2. **Sign up for Railway** at https://railway.com/

3. **Create a new project**:
   - Click "New Project" in your Railway dashboard
   - Select "Deploy from GitHub repo"
   - Choose this repository
   - Railway will automatically detect the configuration and deploy

4. **Configure environment (optional)**:
   - No environment variables are required for basic functionality
   - The app will use the default `config.yaml` settings
   - Railway will automatically assign a PORT environment variable

5. **Access your deployed app**:
   - Railway will provide a public URL (e.g., `https://your-app.up.railway.app`)
   - The web interface will be available at the root URL
   - No additional configuration needed!

#### Configuration Files

The repository includes the following Railway-specific files:

- `railway.toml` - Railway deployment configuration
- `Procfile` - Process definition for the web server
- `.python-version` - Python version specification (3.11)
- `.railwayignore` - Files to exclude from deployment

#### Manual Deployment

You can also use the Railway CLI:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize and deploy
railway init
railway up
```

#### Environment Variables (Optional)

While not required, you can set these in Railway for customization:

- `PORT` - Automatically set by Railway (default: assigned by Railway)
- You can also override config.yaml settings via environment variables in your code if needed

## Testing

This project includes comprehensive test coverage with unit and integration tests.

### Running Tests

Install test dependencies:
```bash
uv sync --extra test
```

Run all tests:
```bash
uv run pytest
```

Run with coverage report:
```bash
uv run pytest --cov=src --cov-report=html
```

Run specific test files:
```bash
uv run pytest tests/unit/test_game_scorer.py
uv run pytest tests/integration/
```

### Test Structure

- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for CLI, API, and Web interfaces
- `tests/fixtures/` - Shared test data and fixtures

See `tests/README.md` for detailed testing documentation.

## Requirements

- Python 3.11+
- Package management via [uv](https://github.com/astral-sh/uv)
- All dependencies managed in `pyproject.toml`

## License

MIT License
