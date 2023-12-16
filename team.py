from contestPeriod import ContestPeriod
from customExceptions import (
  AnswersAlreadySubmittedException,
  MemberInAnotherTeamException,
  MemberNotInTeamException,
  MemberNotInvitedException,
  OwnerLeaveTeamException,
  TeamSizeExceededException,
  WrongPeriodException
)


class Team:
  def __init__(
      self, 
      contest_instance, 
      name: str, 
      owner_id: int, 
      member_ids: list = [], 
      invited_member_ids: list = []
  ):
    if contest_instance.team_size_limit is not None and len(member_ids) > contest_instance.team_size_limit:
      raise TeamSizeExceededException
    else:
      self.submitRanking = 0
      self.answersSubmitted = False
      from contest import Contest
      self.contestInstance: Contest = contest_instance
      self.name = name
      self.owner_id = owner_id
      self.member_ids = member_ids
      self.invited_member_ids = invited_member_ids
      self.answerScore: dict = {}

  def member_in_team(self, memberID: int) -> bool:
    return memberID == self.owner_id or memberID in self.member_ids

  def member_invited_to_team(self, memberID: int) -> bool:
    return memberID in self.invited_member_ids

  def invite_member(self, memberID: int):
    self.invited_member_ids.append(memberID)

  def uninvite_member(self, memberID: int):
    try:
      self.invited_member_ids.remove(memberID)
    except:
      raise MemberNotInTeamException

  def add_member(self, memberID: int):
    if memberID not in self.invited_member_ids:
      raise MemberNotInvitedException
    if memberID in self.contestInstance.all_contest_participants:
      raise MemberInAnotherTeamException
    if self.contestInstance.team_size_limit is None or len(self.member_ids) < self.contestInstance.team_size_limit:
      self.member_ids.append(memberID)
    else:
      raise TeamSizeExceededException

  def remove_member(self, memberID: int):
    if memberID in self.member_ids:
      self.member_ids.remove(memberID)
    elif memberID == self.owner_id:
      raise OwnerLeaveTeamException
    else:
      raise MemberNotInTeamException

  def answer(self, question, answer: float):
    if self.contestInstance.period == ContestPeriod.competition:
      if self.answersSubmitted:
        raise AnswersAlreadySubmittedException
      if question.isCorrect(answer):
        self.answerScore[question.getNumber()] = question.pointValue
      else:
        self.answerScore[question.getNumber()] = 0
    else:
      raise WrongPeriodException(ContestPeriod.competition)

  def submit_answers(self):
    if self.contestInstance.period == ContestPeriod.competition:
      self.answersSubmitted = True
      self.submitRanking = self.contestInstance.team_submit_order
      self.contestInstance.team_submit_order += 1
    else:
      raise WrongPeriodException(ContestPeriod.competition)

  def transfer_ownership(self, newOwnerID: int):
    if newOwnerID in self.member_ids:
      self.member_ids.append(self.owner_id)
      self.member_ids.remove(newOwnerID)
      self.owner_id = newOwnerID
    else:
      raise MemberNotInTeamException

  @property
  def total_points(self) -> int:
    if not self.answersSubmitted:
      return 0
    total = 0
    for problemNumber in self.answerScore.keys():
      total += self.answerScore[problemNumber]
    return total

  def get_data(self):
    return {
      "name": self.name,
      "ownerID": self.owner_id,
      "memberIDs": self.member_ids,
      "invitedMemberIDs": self.invited_member_ids,
      "answerScore": self.answerScore,
      "answersSubmitted": self.answersSubmitted
    }

  @staticmethod
  def from_data(contestInstance, data: dict):
    team = Team(
      contestInstance,
      data["name"],
      data["ownerID"],
      data["memberIDs"],
      data["invitedMemberIDs"]
    )
    team.answerScore = data["answerScore"]
    team.answersSubmitted = data["answersSubmitted"]
    return team
