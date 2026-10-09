"""
Rule-Based Priority Engine (Scaffolding for Milestone Phase 2)

This engine calculates study priority for topics and subjects based on:
1. Days remaining until exam
2. Topic completion status and estimated study hours
3. Importance score (1-5) and user difficulty rating
"""
from datetime import date
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
        - Closer exam dates scale urgency up exponentially.
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
