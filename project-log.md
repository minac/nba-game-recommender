<!-- AGENT_CONTEXT
status: active development
current_focus: AI buzz scoring added
blockers: none
next_steps: Store Anthropic API key in macOS keychain and production env, test with live sync
last_updated: 2026-02-17
-->

# Project Log

## 2026-02-17

**Did:** Added AI buzz scoring via Claude API with web search (6th scoring criterion, up to 40 pts)

New `BuzzScorer` module uses Anthropic's Messages API with web search tool to evaluate how much online buzz each game generated — searching for articles, social media, and news coverage. Runs at sync time and caches in SQLite so recommendations stay instant.

- Created `src/core/buzz_scorer.py` with Claude API integration and web search
- Added `game_buzz` table to SQLite database
- Integrated buzz as criterion 6 in `GameScorer` (0-40 pts)
- API key sourced from macOS keychain (`security` CLI) with `ANTHROPIC_API_KEY` env var fallback
- Graceful degradation: no API key = buzz score of 0 (feature is opt-in)
- Updated all display surfaces: CLI, web API, TRMNL, detailed explain mode
- 135 tests passing (was 115, added 20 new buzz scorer tests)

**Learned:** Python 3.11 f-strings don't support nested quotes of the same type — extract variables before the template string to avoid `SyntaxError: unmatched '['`.

---

## 2025-01-20

**Did:** Unified app naming to `nba-game-recommender`

Standardized on single naming convention across all services:

- Package: `nba-game-recommender`
- Web service: `nba-game-recommender`
- Cron job: `nba-game-recommender-sync` (was `nba-data-sync`)
- URL: `nba-game-recommender.onrender.com`

Changes made:

- Updated `render.yaml` cron job name from `nba-data-sync` to `nba-game-recommender-sync`
- Updated `render.yaml` sync URL to `nba-game-recommender.onrender.com`

Manual Render cleanup needed:

- Delete suspended `nba-frontend` service (obsolete)
- Rename/recreate cron job as `nba-game-recommender-sync`

---

## 2025-12-28 21:35

**Did:** Troubleshot and fixed Render cron job sync issues

Two issues found and fixed via Render REST API:

1. Cron job was calling wrong URL (`nba-game-recommender.onrender.com` instead of `nba-engaging-game-week.onrender.com`)
2. Web service was missing `SYNC_TOKEN` env var (cron job had it, web service didn't)

Fixes applied:

- `PATCH /v1/services/crn-d58p8i3e5dus73e3afn0` - Updated start command URL
- `PUT /v1/services/srv-d4dijafdiees73ckgrmg/env-vars/SYNC_TOKEN` - Added matching token
- Triggered redeploy, verified sync works

**Learned:**

- **Render MCP server has auth bugs** - Filed [render-oss/render-mcp-server#10](https://github.com/render-oss/render-mcp-server/issues/10). OAuth endpoint returns 404, and API key auth shows "not authenticated" despite working with REST API. Workaround: use REST API directly.
- **MCP config location**: `~/.claude.json` under `projects.<path>.mcpServers`
- **Render REST API works perfectly** - Same API key that fails with MCP works fine with `api.render.com/v1/*`
- **Env vars need redeploy** - Adding env vars via API requires triggering a new deploy for them to take effect

---

## 2025-12-28 16:00

**Did:** Added daily data sync via Render cron job (PR #81)

- Added persistent disk to web service for SQLite persistence
- Created `/api/sync` endpoint with token authentication
- Added cron job service that syncs data daily at 9am UTC
- Supports `DATABASE_PATH` env var for production paths
- Fixed broken `clear_cache.py` step in CD workflow

**Learned:** Render cron jobs are separate services that can't share disk with web services. Solution: cron job calls an HTTP endpoint on the web service which has the persistent disk.

---

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
