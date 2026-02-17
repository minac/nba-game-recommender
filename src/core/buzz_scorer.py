"""AI-powered buzz scoring using Claude API with web search.

Evaluates how much online buzz/excitement each NBA game generated
by searching for articles, social media mentions, and news coverage.
"""

import json
import os
import re
import subprocess
from typing import Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_BUZZ_SCORE = 40


def _get_api_key() -> Optional[str]:
    """Get Anthropic API key from macOS keychain or environment variable.

    Priority:
    1. macOS keychain via `security` CLI
    2. ANTHROPIC_API_KEY environment variable
    """
    # Try macOS keychain first
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                "anthropic-api-key",
                "-a",
                "api-key",
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info("Loaded Anthropic API key from macOS keychain")
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fall back to environment variable
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        logger.info("Loaded Anthropic API key from environment variable")
        return key

    return None


class BuzzScorer:
    """Scores NBA games based on online buzz using Claude API with web search."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or _get_api_key()
        self._client = None

    @property
    def available(self) -> bool:
        """Whether buzz scoring is available (API key configured)."""
        return self.api_key is not None

    @property
    def client(self):
        """Lazy-init Anthropic client."""
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def score_games(self, games: List[Dict]) -> Dict[str, Dict]:
        """Score multiple games for online buzz in a single API call.

        Args:
            games: List of game dicts with game_id, game_date, home_team, away_team,
                   total_points, final_margin

        Returns:
            Dict mapping game_id to {"score": float, "reasoning": str}
            Score is 0-40. Returns all zeros on failure.
        """
        if not self.available:
            logger.info("Buzz scoring skipped: no API key configured")
            return {g["game_id"]: {"score": 0, "reasoning": ""} for g in games}

        if not games:
            return {}

        try:
            return self._call_claude(games)
        except Exception as e:
            logger.error(f"Buzz scoring failed: {e}")
            return {g["game_id"]: {"score": 0, "reasoning": ""} for g in games}

    def _format_game_list(self, games: List[Dict]) -> str:
        """Format games into a readable list for the prompt."""
        lines = []
        for g in games:
            home = g["home_team"]
            away = g["away_team"]
            lines.append(
                f"- Game {g['game_id']}: {away['abbr']} {away['score']} @ "
                f"{home['score']} {home['abbr']} on {g['game_date']} "
                f"(margin: {g['final_margin']})"
            )
        return "\n".join(lines)

    def _call_claude(self, games: List[Dict]) -> Dict[str, Dict]:
        """Call Claude API with web search to evaluate game buzz."""
        game_list = self._format_game_list(games)
        game_ids = [g["game_id"] for g in games]

        prompt = f"""Analyze the following NBA games and rate how much online buzz, excitement, and media attention each game generated. Search for recent articles, social media discussion, and news coverage about these games.

Games to analyze:
{game_list}

For each game, consider:
- Was this a rivalry game or marquee matchup?
- Did any player have a historic or standout performance?
- Was there a dramatic finish (buzzer beater, overtime, comeback)?
- Did this game have playoff implications or milestone moments?
- How much social media and news coverage did it receive?

Respond with ONLY a JSON object mapping each game ID to a score (0-40) and brief reasoning. Use this exact format:
{{
  "{game_ids[0]}": {{"score": <0-40>, "reasoning": "<one sentence>"}},
  ...
}}

Score guide: 0 = no buzz, 10 = below average, 20 = average coverage, 30 = significant buzz, 40 = massive viral moment.
Return ONLY the JSON object, no other text."""

        messages = [{"role": "user", "content": prompt}]
        tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]

        # Loop to handle pause_turn (Claude pauses after web searches)
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )

        # Continue if Claude paused after web search (up to 3 continuations)
        for _ in range(3):
            if response.stop_reason != "pause_turn":
                break
            # Pass response back and continue
            messages = messages + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": "Continue."},
            ]
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                tools=tools,
                messages=messages,
            )

        return self._parse_response(response, games)

    def _parse_response(self, response, games: List[Dict]) -> Dict[str, Dict]:
        """Parse Claude's response into buzz scores."""
        # Extract last text block from response (web search results come first)
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text

        if not text:
            logger.warning("No text in Claude response")
            return {g["game_id"]: {"score": 0, "reasoning": ""} for g in games}

        # Extract JSON from response — Claude may include preamble text
        json_str = text.strip()

        # Try markdown code fence first
        if "```" in json_str:
            match = re.search(r"```(?:json)?\s*\n(.*?)\n```", json_str, re.DOTALL)
            if match:
                json_str = match.group(1)

        # If that didn't work, find the outermost { ... }
        if not json_str.startswith("{"):
            brace_start = json_str.find("{")
            brace_end = json_str.rfind("}")
            if brace_start != -1 and brace_end != -1:
                json_str = json_str[brace_start : brace_end + 1]

        try:
            scores = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse buzz scores JSON: {text[:300]}")
            return {g["game_id"]: {"score": 0, "reasoning": ""} for g in games}

        # Validate and clamp scores
        result = {}
        for game in games:
            gid = game["game_id"]
            entry = scores.get(gid, {})
            raw_score = entry.get("score", 0) if isinstance(entry, dict) else 0
            reasoning = entry.get("reasoning", "") if isinstance(entry, dict) else ""

            # Clamp to 0-MAX_BUZZ_SCORE
            clamped = max(0, min(MAX_BUZZ_SCORE, float(raw_score)))
            result[gid] = {"score": clamped, "reasoning": reasoning}

        return result
