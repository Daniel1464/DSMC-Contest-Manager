import ast
import requests
import os

from exceptions import DataAPIException


class DataStorageAPI:
    # passwordStringKey represents the ENV variable key.
    def __init__(self, password_string_key: str = "password"):
        self.passwordStringKey = password_string_key
        self.session = requests.Session()
        self.__local_data: dict[str, str] = {}
        self.remote_data_out_of_sync = False
        self.session.get("https://data-storage-system.danielchen1464.repl.co")

    def get_local_data(self) -> dict[str, str]:
        return self.__local_data

    def get_keys(self) -> list[str]:
        res = self.session.get(
            "https://data-storage-system.danielchen1464.repl.co/get_keys?password={passcode}"
            .format(passcode=os.environ[self.passwordStringKey])
        )
        if res.ok:
            return ast.literal_eval(res.content.decode("utf-8").strip())
        else:
            raise DataAPIException

    def get_value(self, key: str, evaluate: bool = False, read_from_local_data: bool = True):
        if key in self.__local_data and read_from_local_data:
            return self.__local_data[key]
        res = self.session.get(
            "https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(
                passcode=os.environ[self.passwordStringKey], inputKey=key))
        if res.ok:
            if evaluate:
                # .strip removes the pesky newline characters from the string
                data = ast.literal_eval(res.content.decode("utf-8").strip())
            else:
                data = res.content.decode("utf-8")
            self.__local_data[key] = data
            return data
        else:
            raise DataAPIException

    def set_value(self, key: str, value):
        self.resync_data()
        self.__local_data[key] = value
        print(self.__local_data)
        res = self.session.post(
            "https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(
                passcode=os.environ[self.passwordStringKey], inputKey=key), data={"value": str(value)})
        if res.ok:
            return res.content.decode("utf-8")
        else:
            self.remote_data_out_of_sync = True
            raise DataAPIException

    def del_value(self, key: str):
        self.resync_data()
        try:
            del self.__local_data[key]
        except:
            self.remote_data_out_of_sync = True
            raise DataAPIException
        print(self.__local_data)
        res = self.session.get(
            "https://data-storage-system.danielchen1464.repl.co/delete_key?password={passcode}&key={inputKey}"
            .format(passcode=os.environ[self.passwordStringKey], inputKey=key))
        if res.ok:
            return res.content.decode("utf-8")
        else:
            self.remote_data_out_of_sync = True
            raise DataAPIException

    def resync_data(self):
        try:
            if self.remote_data_out_of_sync:
                print("data resync is starting.")
                local_keys = self.__local_data.keys()
                remote_keys = self.get_keys()
                for key in remote_keys:
                    if not (key in local_keys):
                        self.del_value(key)
                for key in local_keys:
                    self.set_value(key, self.__local_data[key])
                self.remote_data_out_of_sync = False
                print("data resync has finished.")
        except:
            print("Data has not successfully resynced; data storage API may be out of date.")
            raise DataAPIException

    def reset_local_data(self):
        self.__local_data = {}
