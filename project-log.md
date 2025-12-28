<!-- AGENT_CONTEXT
status: active development
current_focus: Lowered favorite team bonus
blockers: none
next_steps: Review PR #80, then work on daily data refresh
last_updated: 2025-12-28 12:00
-->

# Project Log

## 2025-12-28 12:00

**Did:** Lowered favorite team bonus from 40 to 20 points (PR #80)

- Reduced scoring weight so favorite team acts as tie-breaker, not dominant factor
- Updated config.yaml, game_scorer.py default, CLAUDE.md, and 7 test files
- All 115 tests passing

---

## 2025-12-19 13:40

**Did:** Expanded Testing section in README.md

- Added manual testing commands for all interfaces (Sync CLI, Main CLI, Web UI, REST API)
- Documented 115 automated tests
- All commands verified working

---

## 2025-12-19 10:15

**Did:** Updated README.md

- Replaced Ball Don't Lie references with nba_api
- Added sync step to Quick Start
- Updated port from 3000 to 8080
- Removed TRMNL viewer references
- Removed coverage flags
- Added Database section with SQLite info

---

## 2025-12-19 10:05

**Did:** Removed TRMNL simulator

- Deleted `trmnl_viewer.html` (354 lines)
- Removed `/trmnl-viewer` and `/trmnl-viewer/render` routes from app.py (159 lines)
- Removed unused `liquid` import
- `/api/trmnl` endpoint (actual TRMNL polling) remains intact
- Net: ~510 lines removed

---

## 2025-12-19 09:55

**Did:** Committed uv.lock for reproducible builds

- Removed uv.lock from .gitignore
- Lock file ensures exact dependency versions across all environments

---

## 2025-12-19 09:45

**Did:** Reduced local CLAUDE.md

- Reduced from 277 to 65 lines
- Removed content duplicated in global ~/.claude/CLAUDE.md
- Kept only project-specific: architecture, scoring, API endpoints, database, TRMNL

---

## 2025-12-19 09:35

**Did:** Dramatically simplified web UI

- Reduced index.html from 493 to 200 lines
- Removed Tailwind dependency, using vanilla CSS
- Removed golden glow animations, slider, score breakdowns
- Spoiler-free: shows matchup, date, reason badges only
- Single "Find Game" button (removed Full Rankings)
- Safe DOM manipulation (no innerHTML)

---

## 2025-12-19 09:25

**Did:** Simplified TRMNL full.liquid screen

- Reduced from 165 to 80 lines
- Spoiler-free: no scores or margins shown
- Shows: matchup (GSW @ LAL), date, reason badges (Close game, Top 5 teams, etc.)
- Clean minimal CSS

---

## 2025-12-19 09:15

**Did:** Added SQLite database to git for Render deployment

- Added `data/nba_games.db` (77KB) to repo
- Pre-seeded database means Render can serve recommendations immediately
- Note: `.gitignore` didn't have `data/` - it was just untracked

---

## 2025-12-18 21:40

**Did:** Removed test coverage tooling

- Deleted `.coveragerc` config file
- Removed `pytest-cov` from test dependencies
- Stripped `--cov*` flags from pytest.ini
- Removed codecov upload steps from CI workflow
- Cleaned up .gitignore coverage entries
- Tests now run in 0.30s (faster without coverage overhead)

---

## 2025-12-18 21:00

**Did:** Removed lead_changes criterion and old Ball Don't Lie files

- Removed `lead_changes` scoring criterion (not available in nba_api)
- Deleted `src/api/nba_client.py` (old Ball Don't Lie client - 837 lines)
- Deleted `src/utils/cache.py` (old file-based cache - 311 lines)
- Deleted `scripts/clear_cache.py` and `tests/unit/test_cache.py`
- Updated web UI to show 5 breakdown columns instead of 6
- Updated CLAUDE.md documentation for new architecture
- Fixed import in game_service.py to use nba_api_client
- All 115 tests passing
- Created PR #65

Net change: -1633 lines (removed 2433, added 800)

**Learned:** The old lead_changes criterion required quarter-by-quarter scores that Ball Don't Lie provided but nba_api doesn't expose through its sync endpoints.

---

## 2025-12-18 20:36

**Did:** Tested full pipeline with live December 2025 NBA data

- Fixed score retrieval: scores come from LineScore dataframe (index 1), not GameHeader
- Fixed CLI to show Margin/Stars instead of removed lead_changes field
- Updated test mocks to match new breakdown structure
- Synced 3 games from Dec 8, 2025 (season just starting)
- CLI recommendation working: Spurs @ Pelicans (135-132) ranked #1 with 60 pts
- All 144 tests passing

**Learned:** scoreboardv2 API returns multiple dataframes - GameHeader (index 0) has game metadata, LineScore (index 1) has actual scores by team ID.

---

## 2025-12-18 20:20

**Did:** Replaced Ball Don't Lie API with free nba_api + SQLite caching

Major changes:

- Added `nba_api` library (free, scrapes NBA.com directly)
- Created `src/utils/database.py` - SQLite database for persistent storage
- Created `src/api/nba_api_client.py` - New NBAClient using nba_api + SQLite
- Created `src/interfaces/sync_cli.py` - CLI to sync NBA data to local DB
- Updated `src/core/recommender.py` to use new client
- Updated `config.yaml` to remove Ball Don't Lie config, add database config
- All 144 tests passing

New workflow:

1. Run `uv run python src/interfaces/sync_cli.py` to populate database
2. Run `uv run python src/interfaces/cli.py` to get recommendations

Key benefits:

- No API key required (free!)
- Data stored locally in SQLite (fast, no rate limits after sync)
- Sync can be scheduled via cron for fresh data
- Built-in delays (600ms) prevent rate limiting during sync

**Learned:** nba_api needs delays between requests to avoid rate limiting from NBA.com. Using 600ms between calls works well.

---
