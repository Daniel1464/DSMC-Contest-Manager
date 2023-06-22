import ast
import requests
import os
from customExceptions import DataAPIException
class DataStorageAPI:
  def __init__(self,passwordStringKey: str = "password"):
    self.passwordStringKey = passwordStringKey
    self.session = requests.Session()
    self.session.get("https://data-storage-system.danielchen1464.repl.co")

  def getValue(self,key: str,evaluate: bool = False):
    data = self.session.get("https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(passcode = os.environ[self.passwordStringKey], inputKey = key))
    if str(data) == "<Response [200]>":
      if evaluate:
        return ast.literal_eval(str(data.content)[2:-1])
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
    