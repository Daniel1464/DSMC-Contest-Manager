from dataStorageAPI import DataStorageAPI
from contest import Contest
from contestPeriod import ContestPeriod
class ContestDatabase:
  def __init__(self,passkey: str):
    self.storageAPI = DataStorageAPI(passkey)

  def get_all_contest_names(self):
    return self.storageAPI.getValue(key="all-contest-names",evaluate=True)



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
    questions_data = [question.getData() for question in contest.all_questions]
    teams_data = [team.getData() for team in contest.all_teams]

    allContestNames = self.storageAPI.getValue("all-contest-names",evaluate = True)
    if not (contest.name in allContestNames):
      allContestNames.append(contest.name)
      self.storageAPI.setValue("all-contest-names",allContestNames)

    self.storageAPI.setValue("{contest}-INFO:".format(contest = contest.name), contest_information)
    self.storageAPI.setValue("{contest}-QUESTIONS:".format(contest = contest.name),questions_data)
    self.storageAPI.setValue("{contest}-TEAMS:".format(contest = contest.name),teams_data)




  def get_contest(self,name:str) -> Contest:
    contest_information = self.storageAPI.getValue(key = "{contest}-INFO:".format(contest = name), evaluate = True)
    questions_data = self.storageAPI.getValue(key = "{contest}-QUESTIONS:".format(contest = name), evaluate = True)
    teams_data = self.storageAPI.getValue(key = "{contest}-TEAMS:".format(contest = name), evaluate = True)

    # a special property of enums is that if you do ContestPeriod["preSignup"],
    # it"ll return ContestPeriod.preSignup, the enum that we want.
    contest = Contest(contest_information["name"],
                  contest_information["link"],
                  contest_information["teamSizeLimit"],
                  contest_information["totalTeamsLimit"],
                  questions_data,
                  teams_data)
    contest.period = ContestPeriod[contest_information["period"]]
    contest.teamSubmitOrder = contest_information["teamSubmitOrder"]
    contest.channelIDInfo = contest_information["channelIDInfo"]
    return contest

  def delete_contest(self,contestName: str):
    self.storageAPI.delValue("{contest}-INFO:".format(contest = contestName))
    self.storageAPI.delValue("{contest}-QUESTIONS:".format(contest = contestName))
    self.storageAPI.delValue("{contest}-TEAMS:".format(contest = contestName))

    all_contest_names = self.storageAPI.getValue("all-contest-names",evaluate=True)
    all_contest_names.remove(contestName)
    self.storageAPI.setValue("all-contest-names",all_contest_names)
