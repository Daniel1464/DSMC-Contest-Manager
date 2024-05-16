from datastorageapi import DataStorageAPI
from contest import Contest
from contestperiod import ContestPeriod
import json
import os


def _to_file_name(contest_name: str) -> str:
    return "data/" + contest_name + ".json"


GENERAL_CONTEST_DATA_FILENAME = "data/generalContestInfo.json"


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
        with open(GENERAL_CONTEST_DATA_FILENAME, 'w+') as file:
            contest_info = json.load(file)
            if contest.name not in contest_info['allContestNames']:
                contest_info['allContestNames'].append(contest.name)
                json.dump(contest_info, file, indent=6)
        with open(_to_file_name(contest.name), 'w') as file:
            json.dump({"info": contest_information, "questions": questions_data, "teams": teams_data}, file, indent=6)

    def get_contest(self, name: str) -> Contest:
        with open(_to_file_name(name), 'w+') as file:
            all_data = json.load(file)
            contest_information: dict = all_data['info']
            questions_data: list = all_data['questions']
            teams_data: list = all_data['teams']
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
        os.remove(_to_file_name(contest_name))
        with open(GENERAL_CONTEST_DATA_FILENAME, 'w+') as file:
            contest_info = json.load(file)
            contest_info['allContestNames'].remove(contest_name)
            json.dump(contest_info, file, indent=6)
