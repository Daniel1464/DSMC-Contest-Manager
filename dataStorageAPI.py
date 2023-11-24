import ast
import requests
import os

class DataAPIException(Exception):
  def __init__(self):
    super().__init__("There was an issue with the Data API. Check it's page for the specific error.")


class DataStorageAPI:
  # passwordStringKey represents the ENV variable key.
  def __init__(self, passwordStringKey: str = "password"):
    self.passwordStringKey = passwordStringKey
    self.session = requests.Session()
    self.session.get("https://data-storage-system.danielchen1464.repl.co")

  def getKeys(self):
    res = self.session.get(
      "https://data-storage-system.danielchen1464.repl.co/get_keys?password={passcode}"
      .format(passcode = os.environ[self.passwordStringKey])
    )

    if res.ok:
      return res.content.decode("utf-8")
    else:
      raise DataAPIException

  def getValue(self, key: str, evaluate: bool = False):
    res = self.session.get("https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(passcode = os.environ[self.passwordStringKey], inputKey = key))

    if res.ok:
      if evaluate:
        # .strip removes the pesky newline characters from the string
        return ast.literal_eval(res.content.decode("utf-8").strip())
      else:
        return res.content.decode("utf-8")
    else:
      raise DataAPIException
      return

  def setValue(self, key: str, value):
    input = str(value)

    res = self.session.post("https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(passcode = os.environ[self.passwordStringKey], inputKey = key), data = {"value": input})

    if res.ok:
      return res.content.decode("utf-8")
    else:
      raise DataAPIException

  def delValue(self, key: str):
    
    res = self.session.get("https://data-storage-system.danielchen1464.repl.co/delete_key?password={passcode}&key={inputKey}".format(passcode = os.environ[self.passwordStringKey], inputKey = key))

    if res.ok:
      return res.content.decode("utf-8")
    else:  
      raise DataAPIException
