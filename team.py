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
    def __init__(
            self,
            contest_instance: Contest,
            name: str,
            owner_id: int,
            member_ids: list[int] = None,
            invited_member_ids: list[int] = None
    ):
        if invited_member_ids is None:
            invited_member_ids = []
        if member_ids is None:
            member_ids = []
        if contest_instance.team_size_limit is not None and len(member_ids) > contest_instance.team_size_limit:
            raise TeamSizeExceededException
        else:
            self.submit_ranking = 0
            self.answers_submitted = False
            self.contest_instance: Contest = contest_instance
            self.name = name
            self.owner_id = owner_id
            self.member_ids = member_ids
            self.invited_member_ids = invited_member_ids
            self.answer_score: dict = {}

    def member_in_team(self, member_id: int) -> bool:
        return member_id == self.owner_id or member_id in self.member_ids

    def member_invited_to_team(self, member_id: int) -> bool:
        return member_id in self.invited_member_ids

    def invite_member(self, member_id: int):
        self.invited_member_ids.append(member_id)

    def uninvite_member(self, member_id: int):
        try:
            self.invited_member_ids.remove(member_id)
        except:
            raise MemberNotInTeamException

    def add_member(self, member_id: int):
        if member_id not in self.invited_member_ids:
            raise MemberNotInvitedException
        if member_id in self.contest_instance.all_contest_participants:
            raise MemberInAnotherTeamException
        if self.contest_instance.team_size_limit is None or len(
                self.member_ids) < self.contest_instance.team_size_limit:
            self.member_ids.append(member_id)
        else:
            raise TeamSizeExceededException

    def remove_member(self, member_id: int):
        if member_id in self.member_ids:
            self.member_ids.remove(member_id)
        elif member_id == self.owner_id:
            raise OwnerLeaveTeamException
        else:
            raise MemberNotInTeamException

    def answer(self, question: Question, answer: float):
        if self.contest_instance.period == ContestPeriod.competition:
            if self.answers_submitted:
                raise AnswersAlreadySubmittedException
            if question.is_correct(answer):
                self.answer_score[question.get_number()] = question.point_value
            else:
                self.answer_score[question.get_number()] = 0
        else:
            raise WrongPeriodException(ContestPeriod.competition)

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

    @property
    def total_points(self) -> int:
        if not self.answers_submitted:
            return 0
        total = 0
        for problem_number in self.answer_score.keys():
            total += self.answer_score[problem_number]
        return total

    def get_data(self):
        return {
            "name": self.name,
            "ownerID": self.owner_id,
            "memberIDs": self.member_ids,
            "invitedMemberIDs": self.invited_member_ids,
            "answerScore": self.answer_score,
            "answersSubmitted": self.answers_submitted,
            "submitRanking": self.submit_ranking
        }

    @staticmethod
    def from_data(contest_instance, data: dict):
        team = Team(
            contest_instance,
            data["name"],
            data["ownerID"],
            data["memberIDs"],
            data["invitedMemberIDs"]
        )
        team.answer_score = data["answerScore"]
        team.answers_submitted = data["answersSubmitted"]
        try:
            team.submit_ranking = data['submitRanking']
        except KeyError:
            print("submit rankings not posted yet; oops")
        return team
