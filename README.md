# NBA Game Recommender

Find the most engaging NBA game to watch from the past week based on multiple criteria including lead changes, close scores, star power, and more.

## Features

- **Modular Architecture**: Run as CLI, REST API, or Web Application
- **Smart Scoring Algorithm**: Evaluates games based on:
  - Lead changes (more exciting)
  - Top 5 team participation
  - Final margin (closer games score higher)
  - Minimum 200 points threshold
  - Star player participation
  - Favorite team bonus
- **Configurable**: Customize scoring weights and preferences via `config.yaml`
- **Real NBA Data**: Fetches actual game data from NBA Stats API

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nba-most-engaging-game-of-the-week
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your preferences (optional):
```bash
# Edit config.yaml to set your favorite team and adjust scoring weights
```

## Usage

### CLI (Command Line Interface)

Find the best game from the last 7 days:
```bash
python src/interfaces/cli.py
```

Options:
```bash
python src/interfaces/cli.py --help

# Look back 3 days
python src/interfaces/cli.py -d 3

# Set favorite team
python src/interfaces/cli.py -t LAL

# Show all games ranked
python src/interfaces/cli.py --all
```

### REST API

Start the API server:
```bash
python src/interfaces/api_server.py
```

Endpoints:
- `GET /api/health` - Health check
- `GET /api/best-game?days=7&team=LAL` - Get best game
- `GET /api/games?days=7` - Get all games ranked
- `GET /api/config` - Get configuration

Example:
```bash
curl "http://localhost:5000/api/best-game?days=7&team=BOS"
```

### Web Interface

Start the web server:
```bash
python src/interfaces/web/app.py
```

Then open your browser to `http://localhost:8080`

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
│   │   └── nba_client.py       # NBA API client
│   └── interfaces/
│       ├── cli.py              # Command-line interface
│       ├── api_server.py       # REST API server
│       └── web/
│           ├── app.py          # Web application
│           └── templates/
│               └── index.html  # Web UI
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
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

## Requirements

- Python 3.7+
- requests
- flask
- pyyaml
- python-dateutil

## License

MIT License
