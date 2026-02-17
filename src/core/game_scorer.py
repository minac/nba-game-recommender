"""Game scoring algorithm for NBA game recommendations."""

from typing import Dict, Optional


class GameScorer:
    """Scores NBA games based on multiple engagement criteria."""

    def __init__(self, config: Dict):
        """
        Initialize the game scorer with configuration.

        Args:
            config: Configuration dictionary with scoring weights
        """
        self.top5_team_bonus = config.get("top5_team_bonus", 50)
        self.close_game_bonus = config.get("close_game_bonus", 100)
        self.min_total_points = config.get("min_total_points", 200)
        self.high_score_bonus = config.get("high_score_bonus", 10)
        self.star_power_weight = config.get("star_power_weight", 20)
        self.favorite_team_bonus = config.get("favorite_team_bonus", 20)
        self.buzz_bonus = config.get("buzz_bonus", 40)

    def score_game(
        self, game: Dict, favorite_team: Optional[str] = None, top5_teams: set = None
    ) -> Dict:
        """
        Calculate engagement score for a game.

        Args:
            game: Game dictionary with all game information
            favorite_team: Optional favorite team abbreviation
            top5_teams: Set of top 5 team abbreviations

        Returns:
            Dictionary with score and breakdown
        """
        score = 0
        breakdown = {}

        # Criterion 1: Top 5 team participation
        home_abbr = game["home_team"]["abbr"]
        away_abbr = game["away_team"]["abbr"]
        top5_count = 0

        if top5_teams:
            if home_abbr in top5_teams:
                top5_count += 1
            if away_abbr in top5_teams:
                top5_count += 1

        top5_score = top5_count * self.top5_team_bonus
        score += top5_score
        breakdown["top5_teams"] = {"count": top5_count, "points": top5_score}

        # Criterion 2: Final margin (closer is better)
        # Use exponential decay: closer games get more points
        # Max bonus at 0 margin, decreasing as margin increases
        margin = game.get("final_margin", 100)
        if margin <= 3:
            close_score = self.close_game_bonus
        elif margin <= 5:
            close_score = self.close_game_bonus * 0.8
        elif margin <= 10:
            close_score = self.close_game_bonus * 0.5
        elif margin <= 15:
            close_score = self.close_game_bonus * 0.25
        else:
            close_score = 0

        score += close_score
        breakdown["close_game"] = {"margin": margin, "points": close_score}

        # Criterion 3: High scoring game bonus (200+)
        total_points = game.get("total_points", 0)
        meets_threshold = total_points >= self.min_total_points
        high_score_points = self.high_score_bonus if meets_threshold else 0
        score += high_score_points
        breakdown["total_points"] = {
            "total": total_points,
            "threshold_met": meets_threshold,
            "points": high_score_points,
        }

        # Criterion 4: Star power
        star_count = game.get("star_players_count", 0)
        star_score = star_count * self.star_power_weight
        score += star_score
        breakdown["star_power"] = {"count": star_count, "points": star_score}

        # Criterion 5: Favorite team bonus
        has_favorite = False
        if favorite_team:
            if home_abbr == favorite_team or away_abbr == favorite_team:
                score += self.favorite_team_bonus
                has_favorite = True

        breakdown["favorite_team"] = {
            "has_favorite": has_favorite,
            "points": self.favorite_team_bonus if has_favorite else 0,
        }

        # Criterion 6: AI buzz score (pre-computed during sync)
        buzz_score = game.get("buzz_score", 0)
        score += buzz_score
        buzz_reasoning = game.get("buzz_reasoning", "")
        breakdown["buzz"] = {"points": buzz_score, "reasoning": buzz_reasoning}

        return {"score": round(score, 2), "breakdown": breakdown}
