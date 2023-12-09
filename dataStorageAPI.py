import ast
import requests
from getenv import getenv

class DataAPIException(Exception):
  def __init__(self):
    super().__init__("There was an issue with the Data API. Check it's page for the specific error.")


class DataStorageAPI:
  # passwordStringKey represents the ENV variable key.
  def __init__(self, passwordStringKey: str = "password"):
    self.passwordStringKey = passwordStringKey
    self.session = requests.Session()
    self.session.get("https://data-storage-system.danielchen1464.repl.co")
    self.__local_data: dict[str,str] = {}
    self.remote_data_out_of_sync = False

  def getLocalData(self):
    return self.__local_data

  

  def getKeys(self):
    res = self.session.get(
      "https://data-storage-system.danielchen1464.repl.co/get_keys?password={passcode}"
      .format(passcode = getenv(self.passwordStringKey))
    )

    if res.ok:
      return ast.literal_eval(res.content.decode("utf-8").strip())
    else:
      raise DataAPIException

  def getValue(self, key: str, evaluate: bool = False):
    if key in self.__local_data:
      return self.__local_data[key]
    print(self.__local_data)
    
    res = self.session.get("https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(passcode = getenv(self.passwordStringKey), inputKey = key))

    if res.ok:
      if evaluate:
        # .strip removes the pesky newline characters from the string
        data =  ast.literal_eval(res.content.decode("utf-8").strip())
      else:
        data =  res.content.decode("utf-8")
      self.__local_data[key] = data
      return data
    else:
      raise DataAPIException


  def setValue(self, key: str, value):
    self.resync_data()
    self.__local_data[key] = value
    print(self.__local_data)
    input = str(value)
    res = self.session.post("https://data-storage-system.danielchen1464.repl.co/database?password={passcode}&key={inputKey}".format(passcode = getenv(self.passwordStringKey), inputKey = key), data = {"value": input})
    
    if res.ok:
      return res.content.decode("utf-8")
    else:
      self.remote_data_out_of_sync = True
      raise DataAPIException

  def delValue(self, key: str):
    self.resync_data()
    try:
      del self.__local_data[key]
    except:
      self.remote_data_out_of_sync = True
      raise DataAPIException
    print(self.__local_data)
    
    res = self.session.get("https://data-storage-system.danielchen1464.repl.co/delete_key?password={passcode}&key={inputKey}".format(passcode = getenv(self.passwordStringKey), inputKey = key))

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
        remote_keys = self.getKeys()
  
        for key in remote_keys:
          if not (key in local_keys):
            self.delValue(key)
        for key in local_keys:
          self.setValue(key,self.__local_data[key])
        self.remote_data_out_of_sync = False
        print("data resync has finished.")
    except:
      print("Data has not successfully resynced; data storage API may be out of date.")
      raise DataAPIException
