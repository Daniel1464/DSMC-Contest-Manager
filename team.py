from functools import singledispatch
from customExceptions import *
from contestPeriod import ContestPeriod


class Team:
    
  def __init__(self,contestInstance, name:str, ownerID: int, memberIDs: list = [], invitedMemberIDs: list = []):
    from contest import Contest
    if contestInstance.teamSizeLimit != None and len(memberIDs) > contestInstance.teamSizeLimit:
      raise TeamSizeExceededException
    else:
      self.submitRanking = 0
      self.answersSubmitted = False
      self.contestInstance = contestInstance
      self.name = name
      self.ownerID = ownerID
      self.memberIDs = memberIDs
      self.invitedMemberIDs = invitedMemberIDs
      self.answerScore = {}


  def memberInTeam(self,memberID: int) -> bool:
    return memberID == self.ownerID or memberID in self.memberIDs

  def memberInvitedToTeam(self,memberID: int) -> bool:
    return memberID in self.invitedMemberIDs
    

  def inviteMember(self,memberID: int):
    self.invitedMemberIDs.append(memberID)

  def uninviteMember(self,memberID: int):
    try:
      self.invitedMemberIDs.remove(memberID)
    except:
      raise MemberNotInTeamException
  
  def addMember(self,memberID: int):

    if not memberID in self.invitedMemberIDs:
      raise MemberNotInvitedException
      return
    
    if memberID in self.contestInstance.all_contest_participants:
      raise MemberInAnotherTeamException
      return
    
    if self.contestInstance.teamSizeLimit == None or len(self.memberIDs) < self.contestInstance.teamSizeLimit:
      self.memberIDs.append(memberID)
    else:
      raise TeamSizeExceededException

  def removeMember(self, memberID: int):
    if memberID in self.memberIDs:
      self.memberIDs.remove(memberID)
    elif memberID == self.ownerID:
      raise OwnerLeaveTeamException
    else:
      raise MemberNotInTeamException

  def answer(self,question, answer: float):
    if self.contestInstance.period == ContestPeriod.competition:
      if self.answersSubmitted:
        raise AnswersAlreadySubmittedException
        return
      
      if question.isCorrect(answer):
        self.answerScore[question.getNumber()] = question.pointValue
      else:
        self.answerScore[question.getNumber()] = 0
    else:
      raise WrongPeriodException([ContestPeriod.competition])

  def submit_answers(self):
    if self.contestInstance.period == ContestPeriod.competition:
      self.answersSubmitted = True
      self.submitRanking = self.contestInstance.teamSubmitOrder
      self.contestInstance.teamSubmitOrder += 1
    else:
      raise WrongPeriodException([ContestPeriod.competition])

  def transfer_ownership(self, newOwnerID: int):
    if newOwnerID in self.memberIDs:
      self.memberIDs.append(self.ownerID)
      self.memberIDs.remove(newOwnerID)
      self.ownerID = newOwnerID
    else:
      raise MemberNotInTeamException 


  @property
  def totalPoints(self) -> int:
    if not self.answersSubmitted:
      return 0
    
    total = 0
    for problemNumber in self.answerScore.keys():
      total += self.answerScore[problemNumber]
    return total



  def getData(self):
    return {
      "name": self.name,
      "ownerID": self.ownerID,
      "memberIDs": self.memberIDs,
      "invitedMemberIDs": self.invitedMemberIDs,
      "answerScore": self.answerScore,
      "answersSubmitted": self.answersSubmitted
    }

  @staticmethod
  def fromData(contestInstance, data: dict):
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