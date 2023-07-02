import ast
import requests
import os
from customExceptions import DataAPIException
class DataStorageAPI:
  def __init__(self,passwordStringKey: str = "password"):
    self.passwordStringKey = passwordStringKey
    self.session = requests.Session()
    self.session.get("https://data-storage-system.danielchen1464.repl.co")

  def getKeys(self):
    req = self.session.get(
      "https://data-storage-system.danielchen1464.repl.co/get_keys?password={passcode}"
        .format(passcode = os.environ[self.passwordStringKey])
      )

    if req.ok:
      return str(req.content)
    else:
      raise DataAPIException

  def getValue(self,key: str,evaluate: bool = False):
    data = self.session.get("https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(passcode = os.environ[self.passwordStringKey], inputKey = key))
    if str(data) == "<Response [200]>":
      if evaluate:
        # the [2:-1] is nessecary because all content comes out like b'something_here', and the [2:-1] removes all of that.
        # .strip removes the pesky newline characters from the string
        return ast.literal_eval(str(data.content).strip()[2:-1])
      else:
        return data.content[2:-1]
    else:
      raise DataAPIException
      return

  def setValue(self,key:str,value):
    input = str(value)

    data = self.session.post("https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(passcode = os.environ[self.passwordStringKey], inputKey = key), data = {"value":input})
    if str(data) == "<Response [200]>":
      return data.content[2:-1]
    else:
      raise DataAPIException

  def delValue(self,key:str):
    data = self.session.get("https://data-storage-system.danielchen1464.repl.co/delete_key?password={passcode}&key={inputKey}".format(passcode = os.environ[self.passwordStringKey], inputKey = key))
    if str(data) == "<Response [200]>":
      return data.content[2:-1]
    else:
      raise DataAPIException
