# Application to manage the use of OMXPlayer for playing HD videos
# on Raspberry Pi 4

import requests
import time
from datetime import datetime
import configparser
import sys
import os
import serial
import subprocess
import signal

def startVideo():

    global config
    global omxProcess

    if omxProcess != None:
        print("Killing process...")
        #omxProcess.kill()
        omxProcess.stdin.write(b'q')
        omxProcess.stdin.flush()

    print(f"starting video with content {config['content']}")
    omxProcess = subprocess.Popen(["omxplayer", "--loop", config["content"]],stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    #print(omxProcess)

def handle_ctrl_c(sig, frame):

    # Called when ctrl-c is pressed to kill the OMXPlayer cleanly

    global omxProcess

    print("Shtting down OMXPlayer")
    omxProcess.stdin.write(b'q')
    omxProcess.stdin.flush()

    sys.exit(0)

def updateContent(content):

    global config
    global configFile

    # First, update the defaults.ini file
    configFile.set("DEFAULT", "content", content)
    config["content"] = content
    with open('defaults.ini', 'w') as f:
        configFile.write(f)

    startVideo()

def readDefaultConfiguration():

    config_object = configparser.ConfigParser()
    config_object.read('defaults.ini')
    default = config_object["DEFAULT"]
    config_dict = dict(default.items())

    return(config_object, config_dict)

def sendPing():

    global config

    requestString = "class=exhibitComponent&id=" + config["id"] + "&type=" + config["type"]

    server_full_address = "http://" + str(config["server_ip_address"]) + ":" + str(config["server_port"])

    try:
        headers = {'Content-type': 'application/json'}
        response = requests.post(server_full_address, data = bytes(requestString, encoding="UTF-8"), headers=headers, timeout=1)
    except:
        type, value, traceback = sys.exc_info()
        print("Error sending request", type, value)
        return()
    
    updates = response.json()
    if "content" in updates:
        if updates["content"] != config["content"]:
            updateContent(updates["content"])
    if "commands" in updates:
        for command in updates["commands"]:
            if command == "sleepDisplay":
                sleepDisplays()
            elif command == "wakeDisplay":
                wakeDisplays()
            else:
                print(f"Error: command {command} not recognized!")

def sleepDisplays():

    if config["display_type"] == "screen":
        if sys.platform == "darwin": # MacOS
            os.system("pmset displaysleepnow")
        elif sys.platform == "linux":
            os.system("xset dpms force off")
    elif config["display_type"] == "projector":
        commandProjector("off")

def wakeDisplays():
    if config["display_type"] == "screen":
        if sys.platform == "darwin": # MacOS
            os.system("caffeinate -u -t 2")
        elif sys.platform == "linux":
            os.system("xset dpms force on")
    elif config["display_type"] == "projector":
        commandProjector("on")

def commandProjector(cmd):

    make = "Optoma"

    if make == "Optoma":
        ser = serial.Serial("/dev/ttyUSB0",9600, timeout=0, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        if cmd == "on":
            ser.write(b"~0000 1\r")
        elif cmd == "off":
            ser.write(b"~0000 0\r")
        elif cmd == "checkState":
            ser.write(b"~00124 1\r")
            time.sleep(0.3)
            response = ser.readline()
            print(response)
        else:
            print(f"commandProjector: Error: Unknown command: {cmd}")


configFile, config = readDefaultConfiguration()

omxProcess = None
startVideo()
signal.signal(signal.SIGINT, handle_ctrl_c)  # Catch CTRL-C and handle it gracefully

while True:
    sendPing()
    time.sleep(5)
