# Application to change PowerPoint presentations in response
# to commands from the control server

import requests
import time
from datetime import datetime
import configparser
import sys
import os
import serial
import subprocess
import signal

def startPowerPoint():

    global ppProcess

    if ppProcess != None:
        print("Killing process...")
        ppProcess.kill()

    if "powerpoint_path" in config:
        ppPath = config["powerpoint_path"]
    else:
        print("PowerPoint_control: Error: you must specify the path to the PowerPoint executable with powerpoint_path in defaults.ini")
        return()

    if "content" in config:
        if isinstance(config['content'], list):
            content = (config["content"])[0] # Supports only one content file
        else:
            content = config["content"]
    else:
        print("PowerPoint_control: Error: you must specify a filepath to the content in defaults.ini")
        return()
        #return(config.get("DEFAULT", "content"))

    root = os.path.dirname(os.path.abspath(__file__))
    content_path = os.path.join(root, "content", config["current_exhibit"], content)

    cmd = [ppPath, '/S', content_path]

    print(cmd)
    try:
        ppProcess = subprocess.Popen(cmd)
    except Exception as e:
        print(e)

def handle_ctrl_c(sig, frame):

    # Called when ctrl-c is pressed to kill PowerPoint cleanly

    global ppProcess

    print("Shtting down PowerPoint")

    ppProcess.kill()
    sys.exit(0)

def updateContent(content):

    global config

    config["content"] = content

    startPowerPoint()

def askForDefaults():

    # Ask the helper to send the default configuration

    global helperAddress
    global config

    headers = {'Content-type': 'application/json'}
    requestDict = {"action": "getDefaults"}
    result = requests.post(helperAddress, json=requestDict, headers=headers)

    config = result.json()

def updateDefaults(update):

    # Send a JSON dictionary to the helper to update the defaults

    global helperAddress

    requestDict = {"action": "updateDefaults"}

    if "content" in update:
        requestDict["content"] = update["content"]
    if "current_exhibit" in update:
        requestDict["current_exhibit"] = update["current_exhibit"]

    headers = {'Content-type': 'application/json'}
    requests.post(helperAddress, json=requestDict, headers=headers)

def sendPing():

    global config

    headers = {'Content-type': 'application/json'}
    requestDict = {"class": "exhibitComponent",
                   "id": config["id"],
                   "type": config["type"]}

    server_full_address = "http://" + str(config["server_ip_address"]) + ":" + str(config["server_port"])

    try:
        response = requests.post(server_full_address, headers=headers, json=requestDict, timeout=1)
    except:
        type, value, traceback = sys.exc_info()
        print("Error sending request", type, value)
        return()

    updates = response.json()
    updateDefaults(updates)

    if "content" in updates:
        if 'current_exhibit' in updates:
            config["current_exhibit"] = updates["current_exhibit"]
        content = (updates["content"])[0] # No support for multiple files
        if content != config["content"]:
            updateContent(content)
    if "commands" in updates:
        for command in updates["commands"]:
            if command == "sleepDisplay":
                sleepDisplays()
            elif command == "wakeDisplay":
                wakeDisplays()
            else:
                print(f"Error: command {command} not recognized!")


def sleepDisplays():

    pass

def wakeDisplays():

    pass

helperAddress = "http://localhost:8000"

ppProcess = None
askForDefaults()
startPowerPoint()
signal.signal(signal.SIGINT, handle_ctrl_c)  # Catch CTRL-C and handle it gracefully

while True:
    sendPing()
    time.sleep(5)
