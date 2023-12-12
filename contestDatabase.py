from dataStorageAPI import DataStorageAPI
from contest import Contest
from contestPeriod import ContestPeriod


class ContestDatabase:
  def __init__(self, passkey: str):
    self.storageAPI = DataStorageAPI(passkey)

  def get_all_contest_names(self):
    return self.storageAPI.get_value(key="all-contest-names", evaluate=True)

  def update_contest(self, contest: Contest):

    # when we do str(contest.period), it will return ContestPeriod.(SomePeriod)
    # str(contest.period)[contest.period.index(".")+1:] makes it return only the period name.
    # for example, ContestPeriod.preSignup would turn into preSignup.
    contest_information = {
      "teamSizeLimit": contest.teamSizeLimit,
      "totalTeamsLimit": contest.totalTeamsLimit,
      "link": contest.link,
      "name": contest.name,
      "period": str(contest.period)[str(contest.period).index(".")+1:],
      "teamSubmitOrder": contest.teamSubmitOrder,
      "channelIDInfo": contest.channelIDInfo
    }
    questions_data = [question.get_data() for question in contest.all_questions]
    teams_data = [team.get_data() for team in contest.all_teams]

    allContestNames = self.storageAPI.get_value("all-contest-names", evaluate = True)
    if contest.name not in allContestNames:
      allContestNames.append(contest.name)
      self.storageAPI.set_value("all-contest-names", allContestNames)

    self.storageAPI.set_value("{contest}-INFO:".format(contest = contest.name), contest_information)
    self.storageAPI.set_value("{contest}-QUESTIONS:".format(contest = contest.name), questions_data)
    self.storageAPI.set_value("{contest}-TEAMS:".format(contest = contest.name), teams_data)

  def get_contest(self, name: str) -> Contest:
    contest_information = self.storageAPI.get_value(key = "{contest}-INFO:".format(contest = name), evaluate = True)
    questions_data = self.storageAPI.get_value(key = "{contest}-QUESTIONS:".format(contest = name), evaluate = True)
    teams_data = self.storageAPI.get_value(key = "{contest}-TEAMS:".format(contest = name), evaluate = True)

    # a special property of enums is that if you do ContestPeriod["preSignup"],
    # it"ll return ContestPeriod.preSignup, the enum that we want.
    contest: Contest = Contest(
      contest_information["name"],
      contest_information["link"],
      contest_information["teamSizeLimit"],
      contest_information["totalTeamsLimit"],
      questions_data,
      teams_data
    )

    contest.period = ContestPeriod[contest_information["period"]]
    contest.teamSubmitOrder = contest_information["teamSubmitOrder"]
    contest.channelIDInfo = contest_information["channelIDInfo"]
    return contest

  def delete_contest(self, contestName: str):
    self.storageAPI.del_value("{contest}-INFO:".format(contest = contestName))
    self.storageAPI.del_value("{contest}-QUESTIONS:".format(contest = contestName))
    self.storageAPI.del_value("{contest}-TEAMS:".format(contest = contestName))

    all_contest_names = self.storageAPI.get_value("all-contest-names", evaluate=True)
    all_contest_names.remove(contestName)
    self.storageAPI.set_value("all-contest-names", all_contest_names)
