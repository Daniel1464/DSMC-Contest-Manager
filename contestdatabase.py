from datastorageapi import DataStorageAPI
from contest import Contest
from contestperiod import ContestPeriod


class ContestDatabase:
    def __init__(self, passkey: str):
        self.storage_api = DataStorageAPI(passkey)

    def get_all_contest_names(self):
        return self.storage_api.get_value(key="all-contest-names", evaluate=True)

    def update_contest(self, contest: Contest):
        # when we do str(contest.period), it will return ContestPeriod.(SomePeriod)
        # str(contest.period)[contest.period.index(".")+1:] makes it return only the period name.
        # for example, ContestPeriod.preSignup would turn into preSignup.
        contest_information = {
            "teamSizeLimit": contest.team_size_limit,
            "totalTeamsLimit": contest.total_teams_limit,
            "link": contest.link,
            "name": contest.name,
            "period": str(contest.period)[str(contest.period).index(".") + 1:],
            "teamSubmitOrder": contest.team_submit_order,
            "channelIDInfo": contest.channel_id_info
        }
        questions_data = [question.get_data() for question in contest.all_questions]
        teams_data = [team.get_data() for team in contest.all_teams]
        all_contest_names: list[str] = self.storage_api.get_value("all-contest-names", evaluate=True)
        if contest.name not in all_contest_names:
            all_contest_names.append(contest.name)
            self.storage_api.set_value("all-contest-names", all_contest_names)
        self.storage_api.set_value("{contest}-INFO:".format(contest=contest.name), contest_information)
        self.storage_api.set_value("{contest}-QUESTIONS:".format(contest=contest.name), questions_data)
        self.storage_api.set_value("{contest}-TEAMS:".format(contest=contest.name), teams_data)

    def get_contest(self, name: str) -> Contest:
        contest_information: dict = self.storage_api.get_value(key="{contest}-INFO:".format(contest=name),
                                                               evaluate=True)
        questions_data: list = self.storage_api.get_value(key="{contest}-QUESTIONS:".format(contest=name),
                                                          evaluate=True)
        teams_data: list = self.storage_api.get_value(key="{contest}-TEAMS:".format(contest=name), evaluate=True)

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
        contest.team_submit_order = contest_information["teamSubmitOrder"]
        contest.channel_id_info = contest_information["channelIDInfo"]
        return contest

    def delete_contest(self, contest_name: str):
        self.storage_api.del_value("{contest}-INFO:".format(contest=contest_name))
        self.storage_api.del_value("{contest}-QUESTIONS:".format(contest=contest_name))
        self.storage_api.del_value("{contest}-TEAMS:".format(contest=contest_name))

        all_contest_names = self.storage_api.get_value("all-contest-names", evaluate=True)
        all_contest_names.remove(contest_name)
        self.storage_api.set_value("all-contest-names", all_contest_names)
