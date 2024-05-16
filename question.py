# this is the only way to prevent circular imports; which is only importing contest if 
# type checking is happening, which does not occur at runtime
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contest import Contest


class Question:
    def __init__(self, contest_instance: Contest, correct_answer: float, point_value: int):
        self.contest_instance: Contest = contest_instance
        self.correct_answer = correct_answer
        self.point_value = point_value

    def get_data(self) -> dict:
        return {
            "correctAnswer": self.correct_answer,
            "pointValue": self.point_value
        }

    @staticmethod
    def from_data(contest_instance, data: dict):
        return Question(contest_instance, data["correctAnswer"], data["pointValue"])

    def get_number(self) -> int:
        return self.contest_instance.all_questions.index(self) + 1

    # corrects for floating point error.
    def is_correct(self, answer: float): return abs(answer - self.correct_answer) <= 0.00000000000001
