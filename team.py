from __future__ import annotations
from contestperiod import ContestPeriod
from exceptions import (
    AnswersAlreadySubmittedException,
    MemberInAnotherTeamException,
    MemberNotInTeamException,
    MemberNotInvitedException,
    OwnerLeaveTeamException,
    TeamSizeExceededException,
    WrongPeriodException
)
# this is the only way to prevent circular imports; which is only importing contest if 
# type checking is happening, which does not occur at runtime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contest import Contest
    from question import Question


class Team:
    def __init__(self, contest_instance: Contest, name: str, owner_id: int, channel_id: int | None = None):
        self.contest_instance: Contest = contest_instance
        self.name = name
        self.owner_id = owner_id
        self.channel_id = channel_id
        self.submit_ranking = 0
        self.answers_submitted = False
        self.member_ids: list[int] = []
        self.invited_member_ids: list[int] = []
        self.answers: dict[int, float] = {}

    def member_in_team(self, member_id: int) -> bool:
        return member_id == self.owner_id or member_id in self.member_ids

    def member_invited(self, member_id: int) -> bool:
        return member_id in self.invited_member_ids

    def invite_member(self, member_id: int):
        if member_id not in self.member_ids and member_id not in self.invited_member_ids:
            self.invited_member_ids.append(member_id)

    def uninvite_member(self, member_id: int):
        if member_id in self.invited_member_ids:
            self.invited_member_ids.remove(member_id)

    def register_member(self, member_id: int, ignore_invite: bool = False):
        if member_id not in self.invited_member_ids and not ignore_invite:
            raise MemberNotInvitedException
        if member_id in self.contest_instance.registered_member_ids:
            raise MemberInAnotherTeamException
        if self.contest_instance.team_size_limit and len(self.member_ids) > self.contest_instance.team_size_limit:
            raise TeamSizeExceededException
        if not ignore_invite:
            self.invited_member_ids.remove(member_id)
        self.member_ids.append(member_id)

    def remove_member(self, member_id: int):
        if member_id in self.member_ids:
            self.member_ids.remove(member_id)
        elif member_id in self.invited_member_ids:
            self.invited_member_ids.remove(member_id)
        elif member_id == self.owner_id:
            raise OwnerLeaveTeamException

    def answer(self, question: Question, answer: float):
        if self.contest_instance.period != ContestPeriod.competition:
            raise WrongPeriodException(ContestPeriod.competition)
        if self.answers_submitted:
            raise AnswersAlreadySubmittedException
        self.answers[question.number] = answer

    def submit_answers(self):
        if self.contest_instance.period == ContestPeriod.competition:
            self.answers_submitted = True
            self.submit_ranking = self.contest_instance.team_submit_order
            self.contest_instance.team_submit_order += 1
        else:
            raise WrongPeriodException(ContestPeriod.competition)

    def transfer_ownership(self, new_owner_id: int):
        if new_owner_id in self.member_ids:
            self.member_ids.append(self.owner_id)
            self.member_ids.remove(new_owner_id)
            self.owner_id = new_owner_id
        else:
            raise MemberNotInTeamException

    def answering_status(self, display_correct_answer: bool = False) -> str:
        strings: list[str] = []
        for question_num, answer in self.answers.items():
            status = "Question " + str(question_num) + ": Answered as " + str(answer)
            if display_correct_answer:
                status += ", Actual Answer: " + str(self.contest_instance.get_question(question_num).correct_answer)
            strings.append(status)
        return "\n".join(strings)

    @property
    def total_points(self) -> int:
        if not self.answers_submitted:
            return 0
        total = 0
        for problem_num, solution in self.answers.items():
            question = self.contest_instance.get_question(problem_num)
            if question.verify(solution):
                total += question.point_value
        return total

    @property
    def data(self):
        return {
            "name": self.name,
            "ownerID": self.owner_id,
            "memberIDs": self.member_ids,
            "invitedMemberIDs": self.invited_member_ids,
            "answers": self.answers,
            "answersSubmitted": self.answers_submitted,
            "submitRanking": self.submit_ranking
        }

    @staticmethod
    def from_data(contest_instance, data: dict):
        team = Team(contest_instance, data["name"], data["ownerID"])
        team.answers_submitted = data["answersSubmitted"]
        team.member_ids = data["memberIDs"]
        team.invited_member_ids = data["invitedMemberIDs"]
        team.answers = data["answers"]
        team.submit_ranking = data['submitRanking']
        return team
