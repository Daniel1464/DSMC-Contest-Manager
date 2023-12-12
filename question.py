class Question:
  def __init__(self, contestInstance, correctAnswer: float, pointValue: int):
    self.contestInstance = contestInstance
    self.correctAnswer = correctAnswer
    self.pointValue = pointValue

  def get_data(self) -> dict:
    return {
      "correctAnswer": self.correctAnswer,
      "pointValue": self.pointValue
    }

  @staticmethod
  def from_data(contestInstance, data: dict):
    return Question(contestInstance, data["correctAnswer"], data["pointValue"])

  def get_number(self) -> int:
    return self.contestInstance.all_questions.index(self)+1

  # corrects for floating point error.
  def is_correct(self, answer: float): return abs(answer - self.correctAnswer) <= 0.00000000000001
