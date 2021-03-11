# This application sets up a small server to communicate with the screen players
# and handle interacting with the system (since the browser cannot)

from http.server import HTTPServer, SimpleHTTPRequestHandler
import time
from datetime import datetime
import configparser
import json
import sys
import os
import serial
from sockio.sio import TCP
import signal

class RequestHandler(SimpleHTTPRequestHandler):

    def log_request(code='-', size='-'):

        # Override to suppress the automatic logging

        pass

    def do_GET(self):

        # Receive a GET

        pass

    def do_OPTIONS(self):

        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

    def do_POST(self):

        # Receives pings from client devices and respond with any updated
        # information

        global configFile
        global config

        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

        # Get the data from the request
        length = int(self.headers['Content-length'])
        data_str = self.rfile.read(length).decode("utf-8")

        # Unpack the data
        try: # JSON
            data = json.loads(data_str)
        except: # not JSON
            data = {}
            split = data_str.split("&")
            for seg in split:
                split2 = seg.split("=")
                data[split2[0]] = split2[1]

        if "action" in data:
            if data["action"] == "sleepDisplays":
                sleepDisplays()
            elif data["action"] == "wakeDisplays":
                wakeDisplays()
            elif data["action"] == "commandProjector":
                if "command" in data:
                    commandProjector(data["command"])
            elif data["action"] == "getDefaults":
                configToSend = dict(config.items())
                if dictionary is not None:
                    configToSend["dictionary"] = dict(dictionary.items("DEFAULT"))
                json_string = json.dumps(configToSend)
                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            elif data["action"] == "updateDefaults":
                if "content" in data:
                    content = data["content"]
                    configFile.set("DEFAULT", "content", data["content"])
                    config["content"] = content

                    # Update file
                    with open('defaults.ini', 'w') as f:
                        configFile.write(f)


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

def sendSOSCommand(cmd, multiline=False):

    # Function to send a command to Science on a Sphere adn read its response

    global sosSocket

    if sosSocket is not None:
        if not multiline:
            return(sosSocket.write_readline(bytes(cmd + '\n', encoding='UTF-8')).decode('UTF-8').strip())
        else:
            sosSocket.write(bytes(cmd + '\n', encoding='UTF-8'))
            return(sosSocket.read(10000).decode("UTF-8"))
    else:
        return(None)

def readDefaultConfiguration():

    config_object = configparser.ConfigParser()
    config_object.read('defaults.ini')
    default = config_object["DEFAULT"]
    config_dict = dict(default.items())

    return(config_object, config_dict)

def quit_handler(sig, frame):
    print('\nKeyboard interrupt detected. Cleaning up and shutting down...')
    sys.exit(0)

def loadDictionary():

    # look for a file called dictionary.ini and load it if it exists

    if "dictionary.ini" in os.listdir():
        parser = configparser.ConfigParser()
        parser.read("dictionary.ini")
        return(parser)
    else:
        return(None)

signal.signal(signal.SIGINT, quit_handler)

configFile, config = readDefaultConfiguration()

# If it exists, load the dictionary that maps one value into another
dictionary = loadDictionary()


httpd = HTTPServer(("", int(config["helper_port"])), RequestHandler)
httpd.serve_forever()
