"""Explainable topic score: importance × 10 plus stepped exam urgency.

Completed topics score zero. Sprint scheduling adds its documented adjustments;
no trained prediction model or automatic mastery diagnosis is involved.
"""
from typing import Optional


class PriorityEngine:
    @staticmethod
    def calculate_topic_priority_score(
        importance_score: int = 3,
        days_until_exam: Optional[int] = None,
        is_completed: bool = False,
    ) -> float:
        """
        Lightweight heuristic:
        - If completed, priority score is 0.
        - Closer exam dates add stepped urgency bonuses.
        - Higher importance increases baseline weight.
        """
        if is_completed:
            return 0.0

        score = float(importance_score * 10)

        if days_until_exam is not None:
            if days_until_exam <= 2:
                score += 50.0
            elif days_until_exam <= 7:
                score += 30.0
            elif days_until_exam <= 14:
                score += 15.0

        return score


priority_engine = PriorityEngine()
