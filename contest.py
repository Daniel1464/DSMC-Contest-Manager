from question import Question
from team import Team
from functools import singledispatch
from customExceptions import *
from contestPeriod import ContestPeriod



class Contest:

  def __init__(self, name: str, link: str, teamSizeLimit: int = None, totalTeamsLimit: int = None, questions: list = [], teams: list = []):
    self.name = name
    self.link = link
    self.teamSizeLimit = teamSizeLimit
    self.totalTeamsLimit = totalTeamsLimit

    # used to keep track who submitted first, second, third, etc.
    self.teamSubmitOrder = 1

    # used to keep track of which period the contest is currently in
    self.period = ContestPeriod.preSignup


    self.__questions = questions
    self.__teams = teams


    self.channelIDInfo = {}



    # note: self represents the contest instance below.
    # this code essentially checks if the list of questions is in fact a list of data dicts, and converts them into their respective objects
    #(with class instances passed in)
    if questions != [] and not isinstance(questions[0],Question):
      self.__questions = [Question.fromData(self,data) for data in questions]
    if teams != [] and not isinstance(teams[0],Team):
      self.__teams = [Team.fromData(self,data) for data in teams]

  @property
  def all_contest_participants(self) -> list:
    ids = []
    for team in self.__teams:
      if team.ownerID not in ids:
        ids.append(team.ownerID)
      for memberID in team.memberIDs:
        if memberID not in ids:
          ids.append(memberID)
    return ids

  @property
  def all_invited_members(self) -> list:
    ids = []
    for team in self.__teams:
      for memberID in team.invitedMemberIDs:
        if memberID not in ids:
          ids.append(memberID)
    return ids


  @property
  def all_teams(self) -> list:
    return self.__teams

  @property
  def team_rankings(self) -> list:
    if self.period == ContestPeriod.competition or self.period == ContestPeriod.postCompetition:
      # note: the team ranking is negated here because it's sorting by reverse(the higher the key, the farther up it appears.)
      return sorted(self.__teams, reverse = True, key = lambda team: (team.totalPoints, -team.submitRanking))
    else:
      raise WrongPeriodException([ContestPeriod.competition,ContestPeriod.postCompetition])
      return


  @property
  def total_problems(self) -> int:
    return len(self.all_questions)


  def add_question(self, question: Question, questionNumber: int = None):
    if self.period == ContestPeriod.preSignup or self.period == ContestPeriod.signup:
      if questionNumber is None:
        self.__questions.append(question)
      else:
        self.__questions.insert(questionNumber-1,question)
    else:
      raise WrongPeriodException([ContestPeriod.preSignup,ContestPeriod.signup])
      return


  # How these lines of code work:
  # Essentially, @singledispatch allows the remove_question function
  # to have 2 different functionalities.
  # inputting a question object into object.remove_question() will cause it to remove the question,
  # while inputting a question number into the function will cause it to remove the question with that number.
  @singledispatch
  def remove_question(self,questionNumber: int):
    if self.period == ContestPeriod.preSignup or self.period == ContestPeriod.signup:
      self.__questions.pop(questionNumber-1)
    else:
      raise WrongPeriodException([ContestPeriod.preSignup,ContestPeriod.signup])
  @remove_question.register
  def _(self,question: Question):
    if self.period == ContestPeriod.preSignup or self.period == ContestPeriod.signup:
      self.__questions.remove(question)
    else:
      raise WrongPeriodException([ContestPeriod.preSignup,ContestPeriod.signup])
      return

  def get_question(self, questionNumber: int) -> Question:
    try:
      return self.__questions[questionNumber-1]
    except:
      raise IndexError



  @property
  def all_questions(self): return self.__questions



  def add_team(self, newTeam: Team):
    if self.period == ContestPeriod.signup:
      if self.totalTeamsLimit is None or len(self.__teams) < self.totalTeamsLimit:
        for team in self.__teams:
          if team.name == newTeam.name:
            raise TeamNameException
            return
        allMembers = self.all_contest_participants
        if newTeam.ownerID in allMembers:
          raise MemberInAnotherTeamException
          return
        for memberID in newTeam.memberIDs:
          if memberID in allMembers:
            raise MemberInAnotherTeamException
            return
        self.__teams.append(newTeam)
      else:
        raise ContestTeamLimitException
    else:
      raise WrongPeriodException([ContestPeriod.signup])
      return

  @singledispatch
  def remove_team(self,team: Team):
    self.__teams.remove(team)
  @remove_team.register
  def _(self,teamName: str):
    for team in self.__teams:
      if team.name == teamName:
        self.__teams.remove(team)
        return

  def get_team(self,teamName: str) -> Team:
    for team in self.__teams:
      if team.name.lower() == teamName.lower():
        return team
    raise TeamNotInContestException
    return

  def get_team_of_user(self,userID:int) -> Team:
    for team in self.__teams:
      if team.memberInTeam(userID):
        return team
    return None

  def get_winner(self) -> Team:
    if self.period == ContestPeriod.competition or self.period == ContestPeriod.postCompetition:
      topRankedTeam = self.team_rankings[0]
      if topRankedTeam.answersSubmitted:
        return topRankedTeam
      else:
        return None
    else:
      raise WrongPeriodException([ContestPeriod.competition, ContestPeriod.postCompetition])
