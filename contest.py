from question import Question
from team import Team
from functools import singledispatch
from exceptions import (
    ContestTeamLimitException,
    MemberInAnotherTeamException,
    TeamNameException,
    TeamNotInContestException,
    WrongPeriodException
)
from contestperiod import ContestPeriod


class Contest:
    # Here, questions and teams represent the questions and teams in dict form.
    def __init__(
            self,
            name: str,
            link: str,
            team_size_limit: int | None = None,
            total_teams_limit: int | None = None,
            questions: list[Question] | list[dict] | None = None,
            teams: list[Team] | list[dict] | None = None
    ):
        self.name = name
        self.link = link
        self.team_size_limit = team_size_limit
        self.total_teams_limit = total_teams_limit
        # used to keep track who submitted first, second, third, etc.
        self.team_submit_order = 1
        # used to keep track of which period the contest is currently in
        self.period = ContestPeriod.preSignup
        self.channel_id_info: dict = {}

        self.__questions: list[Question] = [] if questions is None else questions
        self.__teams: list[Team] = [] if teams is None else teams
        # note: self represents the contest instance below. this code essentially checks if the list of questions is
        # in fact a list of data dicts, and converts them into their respective objects (with class instances passed in)
        if questions != [] and not isinstance(questions[0], Question):
            self.__questions = [Question.from_data(self, data) for data in questions]
        if teams != [] and not isinstance(teams[0], Team):
            self.__teams = [Team.from_data(self, data) for data in teams]

    @property
    def all_contest_participants(self) -> list[int]:
        ids = []
        for team in self.__teams:
            if team.owner_id not in ids:
                ids.append(team.owner_id)
            for member_id in team.member_ids:
                if member_id not in ids:
                    ids.append(member_id)
        return ids

    @property
    def all_invited_members(self) -> list[int]:
        ids = []
        for team in self.__teams:
            for member_id in team.invited_member_ids:
                if member_id not in ids:
                    ids.append(member_id)
        return ids

    @property
    def all_teams(self) -> list[Team]:
        return self.__teams

    @property
    def team_rankings(self) -> list[Team]:
        if self.period == ContestPeriod.competition or self.period == ContestPeriod.postCompetition:
            # note: the team ranking is negated here because it's sorting by reverse:
            # the higher the key, the farther up it appears.
            return sorted(self.__teams, reverse=True, key=lambda team: (team.total_points, -team.submit_ranking))
        else:
            raise WrongPeriodException(ContestPeriod.competition, ContestPeriod.postCompetition)

    @property
    def total_problems(self) -> int:
        return len(self.all_questions)

    def add_question(self, question: Question, question_number: int | None = None):
        if self.period == ContestPeriod.preSignup or self.period == ContestPeriod.signup:
            if question_number is None:
                self.__questions.append(question)
            else:
                self.__questions.insert(question_number - 1, question)
        else:
            raise WrongPeriodException(ContestPeriod.preSignup, ContestPeriod.signup)

    # How these lines of code work:
    # Essentially, @singledispatch allows the remove_question function
    # to have 2 different functionalities.
    # inputting a question object into object.remove_question() will cause it to remove the question,
    # while inputting a question number into the function will cause it to remove the question with that number.
    @singledispatch
    def remove_question(self, question_number: int):
        if self.period == ContestPeriod.preSignup or self.period == ContestPeriod.signup:
            self.__questions.pop(question_number - 1)
        else:
            raise WrongPeriodException(ContestPeriod.preSignup, ContestPeriod.signup)

    @remove_question.register
    def _(self, question: Question):
        if self.period == ContestPeriod.preSignup or self.period == ContestPeriod.signup:
            self.__questions.remove(question)
        else:
            raise WrongPeriodException(ContestPeriod.preSignup, ContestPeriod.signup)

    def get_question(self, question_number: int) -> Question:
        return self.__questions[question_number - 1]

    @property
    def all_questions(self):
        return self.__questions

    def add_team(self, new_team: Team):
        if self.period == ContestPeriod.signup:
            if self.total_teams_limit is None or len(self.__teams) < self.total_teams_limit:
                for team in self.__teams:
                    if team.name == new_team.name:
                        raise TeamNameException
                all_members = self.all_contest_participants
                if new_team.owner_id in all_members:
                    raise MemberInAnotherTeamException
                for memberID in new_team.member_ids:
                    if memberID in all_members:
                        raise MemberInAnotherTeamException
                self.__teams.append(new_team)
            else:
                raise ContestTeamLimitException
        else:
            raise WrongPeriodException(ContestPeriod.signup)

    @singledispatch
    def remove_team(self, team: Team):
        self.__teams.remove(team)

    @remove_team.register
    def _(self, team_name: str):
        for team in self.__teams:
            if team.name == team_name:
                self.__teams.remove(team)
                return

    def get_team(self, team_name: str) -> Team:
        for team in self.__teams:
            if team.name.lower() == team_name.lower():
                return team
        raise TeamNotInContestException

    def get_team_of_user(self, user_id: int) -> Team | None:
        for team in self.__teams:
            if team.member_in_team(user_id):
                return team
        return None

    def get_winner(self) -> Team | None:
        if self.period == ContestPeriod.competition or self.period == ContestPeriod.postCompetition:
            top_ranked_team = self.team_rankings[0]
            if top_ranked_team.answers_submitted:
                return top_ranked_team
            else:
                return None
        else:
            raise WrongPeriodException(ContestPeriod.competition, ContestPeriod.postCompetition)
