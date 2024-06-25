from enum import Enum


class ContestPeriod(Enum):
    preSignup = "pre-signup"
    signup = "signup"
    competition = "competition"
    postCompetition = "post-competition"
