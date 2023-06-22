from flask import Flask, request
from threading import Thread
from subprocess import call

app = Flask('')

statusMessage = "Bot is working!"

@app.route('/',methods=['GET','HEAD'])
def home():
  return statusMessage

@app.route('/killContainer')
def killContainer():
  # credits: https://stackoverflow.com/users/4279/jfs
  with open('killcontainer.sh', 'rb') as file:
      script = file.read()
  rc = call(script, shell=True)
  return "Success."
  

def run():
  app.run(host='0.0.0.0', port=8080)

def running():
  thread = Thread(target=run)
  thread.start()