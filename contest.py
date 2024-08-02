import json
import os
from typing import Self

from question import Question
from team import Team
from exceptions import (
    MemberInAnotherTeamException,
    TeamNameException,
    TeamNotInContestException,
    WrongPeriodException
)
from contestperiod import ContestPeriod


def _contest_name_to_path(contest_name: str) -> str:
    return "data/" + contest_name + ".json"


_GENERAL_DATA_FILE_PATH = "data/generalContestInfo.json"


class Contest:
    # Here, questions and teams represent the questions and teams in dict form.
    def __init__(self, name: str, link: str, team_size_limit: int | None = None):
        self.name = name
        self.link = link
        self.team_size_limit = team_size_limit
        # used to keep track who submitted first, second, third, etc.
        self.team_submit_order: int = 1
        # used to keep track of which period the contest is currently in
        self.period: ContestPeriod = ContestPeriod.preSignup
        self.questions: list[Question] = []
        self.teams: list[Team] = []

    @staticmethod
    def all_names() -> list[str]:
        with open(_GENERAL_DATA_FILE_PATH, 'r') as file:
            return json.load(file)['allContestNames']

    @classmethod
    def from_json(cls, contest_name: str) -> Self:
        with open(_contest_name_to_path(contest_name), 'r') as file:
            contest_data = json.load(file)
        contest_info = contest_data['info']
        question_data_list = contest_data['questions']
        team_data_list = contest_data['teams']
        contest = Contest(
            contest_info["name"],
            contest_info["link"],
            contest_info["teamSizeLimit"]
        )
        contest.team_submit_order = contest_info["teamSubmitOrder"]
        # a special property of enums is that if you do ContestPeriod["preSignup"],
        # it"ll return ContestPeriod.preSignup, the enum that we want.
        contest.period = ContestPeriod[contest_info["period"]]
        contest.questions = [
            Question.from_data(contest, data)
            for data in question_data_list
        ]
        contest.teams = [
            Team.from_data(contest, data)
            for data in team_data_list
        ]
        return contest

    @staticmethod
    def delete_json(contest_name: str):
        os.remove(_contest_name_to_path(contest_name))
        with open(_GENERAL_DATA_FILE_PATH, 'r') as file:
            contest_info = json.load(file)
            contest_info['allContestNames'].remove(contest_name)
        with open(_GENERAL_DATA_FILE_PATH, 'w') as file:
            json.dump(contest_info, file, indent=6)

    def update_json(self):
        with open(_GENERAL_DATA_FILE_PATH, 'r') as file:
            data = json.load(file)
        if self.name not in data['allContestNames']:
            data['allContestNames'].append(self.name)
            with open(_GENERAL_DATA_FILE_PATH, 'w') as file:
                json.dump(data, file, indent=6)
        # when we do str(contest.period), it will return ContestPeriod.(SomePeriod)
        # str(contest.period)[contest.period.index(".")+1:] makes it return only the period name.
        # for example, ContestPeriod.preSignup would turn into preSignup.
        contest_info = {
            "teamSizeLimit": self.team_size_limit,
            "link": self.link,
            "name": self.name,
            "period": str(self.period)[str(self.period).index(".") + 1:],
            "teamSubmitOrder": self.team_submit_order
        }
        question_data_list = [question.data for question in self.questions]
        team_data_list = [team.data for team in self.teams]
        with open(_contest_name_to_path(self.name), 'w') as file:
            json.dump({"info": contest_info, "questions": question_data_list, "teams": team_data_list}, file, indent=6)

    @property
    def registered_member_ids(self) -> list[int]:
        ids = []
        for team in self.teams:
            for member_id in team.member_ids + [team.owner_id]:
                if member_id not in ids:
                    ids.append(member_id)
        return ids

    @property
    def invited_member_ids(self) -> list[int]:
        ids = []
        for team in self.teams:
            for member_id in team.invited_member_ids:
                if member_id not in ids:
                    ids.append(member_id)
        return ids

    @property
    def team_rankings(self) -> list[Team]:
        if self.period == ContestPeriod.competition or self.period == ContestPeriod.postCompetition:
            # note: the team ranking is negated here because it's sorting by reverse:
            # the higher the key, the farther up it appears.
            return sorted(self.teams, reverse=True, key=lambda team: (team.total_points, -team.submit_ranking))
        else:
            raise WrongPeriodException(ContestPeriod.competition, ContestPeriod.postCompetition)

    def add_question(self, question: Question, question_number: int | None = None):
        if self.period == ContestPeriod.preSignup or self.period == ContestPeriod.signup:
            if question_number is None:
                self.questions.append(question)
            else:
                self.questions.insert(question_number - 1, question)
        else:
            raise WrongPeriodException(ContestPeriod.preSignup, ContestPeriod.signup)

    def remove_question(self, identifier: Question | int):
        if self.period == ContestPeriod.preSignup or self.period == ContestPeriod.signup:
            if isinstance(identifier, Question):
                self.questions.remove(identifier)
            else:
                # identifier now represents a question number instead
                self.questions.pop(identifier - 1)
        else:
            raise WrongPeriodException(ContestPeriod.preSignup, ContestPeriod.signup)

    def get_question(self, question_number: int) -> Question:
        return self.questions[question_number - 1]

    def add_team(self, new_team: Team):
        if self.period == ContestPeriod.signup:
            for team in self.teams:
                if team.name == new_team.name:
                    raise TeamNameException
            for memberID in new_team.member_ids + [new_team.owner_id]:
                if memberID in self.registered_member_ids:
                    raise MemberInAnotherTeamException
            self.teams.append(new_team)
        else:
            raise WrongPeriodException(ContestPeriod.signup)

    def remove_team(self, identifier: Team | str):
        team = identifier if isinstance(identifier, Team) else self.get_team(team_name=identifier)
        self.teams.remove(team)

    def get_team(self, team_name: str) -> Team:
        for team in self.teams:
            if team.name.lower() == team_name.lower():
                return team
        raise TeamNotInContestException

    def get_team_of_user(self, user_id: int) -> Team | None:
        for team in self.teams:
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
