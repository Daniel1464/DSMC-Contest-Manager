from contestperiod import ContestPeriod


class TeamNameException(Exception):
    def __init__(self):
        super().__init__(
            "This team shares a name with another team within the contest. Each team must have a unique name.")


class TeamSizeExceededException(Exception):
    def __init__(self):
        super().__init__("The size of this team has exceeded it's limit.")


class MemberNotInTeamException(Exception):
    def __init__(self):
        super().__init__("This member is not in the team specified.")


class AnswersAlreadySubmittedException(Exception):
    def __init__(self):
        super().__init__("The team that has attempted to answer a question has already submitted all of their answers.")


class TeamNotInContestException(Exception):
    def __init__(self):
        super().__init__("This team does not exist within the contest.")


class MemberInAnotherTeamException(Exception):
    def __init__(self):
        super().__init__("This member has already been added to another team.")


class MemberNotInvitedException(Exception):
    def __init__(self):
        super().__init__("This Member is not invited into this team.")


class WrongPeriodException(Exception):
    def __init__(self, *correct_periods: ContestPeriod):
        super().__init__("This function can only be accessed during these periods: " + str(correct_periods))


class OwnerLeaveTeamException(Exception):
    def __init__(self):
        super().__init__(
            "The owner cannot leave the team. They must either delete it, "
            "or transfer ownership using /transfer_ownership to another team member.")
