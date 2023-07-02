from functools import singledispatch
import ast


class Question:
  def __init__(self, contestInstance, correctAnswer: float, pointValue: int):
    from contest import Contest
    self.contestInstance = contestInstance
    self.correctAnswer = correctAnswer
    self.pointValue = pointValue

  def getData(self) -> dict:
    return {
      "correctAnswer": self.correctAnswer,
      "pointValue": self.pointValue
    }

  @staticmethod
  def fromData(contestInstance, data: dict):
    return Question(contestInstance, data["correctAnswer"], data["pointValue"])

  def getNumber(self) -> int:
    return self.contestInstance.all_questions.index(self)+1

  # corrects for floating point error.
  def isCorrect(self, answer: float): return abs(answer - self.correctAnswer) <= 0.00000000000001
