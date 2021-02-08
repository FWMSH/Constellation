# This application sets up a small server to communicate with the window player
# and handle interacting with the system (since the browser cannot)

from http.server import HTTPServer, SimpleHTTPRequestHandler
import time
from datetime import datetime
import configparser
import json
import sys
import os
import serial

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
        global content

        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

        # Get the data from the request
        length = int(self.headers['Content-length'])
        data_str = self.rfile.read(length).decode("utf-8")

        # Unpack the data string into a dict
        data = {}
        split = data_str.split("&")
        for seg in split:
            split2 = seg.split("=")
            data[split2[0]] = split2[1]

        if "action" in data:
            if data["action"] == "sleepDisplays":
                sleepDisplays()
            elif data["action"] == "commandProjector":
                if "command" in data:
                    commandProjector(data["command"])
            elif data["action"] == "getDefaults":
                config = {'content': content}
                json_string = json.dumps(config)

                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            elif data["action"] == "updateDefaults":
                if "content" in data:
                    content = data["content"]
                    configFile.set("DEFAULT", "content", data["content"])

                    # Update file
                    with open('defaults.ini', 'w') as f:
                        configFile.write(f)


def sleepDisplays():

    if displayType == "screen":
        if sys.platform == "darwin": # MacOS
            os.system("pmset displaysleepnow")
    elif displayType == "projector":
        commandProjector("off")

def wakeDisplays():
    if displayType == "screen":
        if sys.platform == "darwin": # MacOS
            os.system("caffeinate -u -t 2")
    elif displayType == "projector":
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

def readDefaultConfiguration():

    global helper_port
    global server_port
    global server_ip_address
    global content
    global displayType

    config = configparser.ConfigParser()
    config.read('defaults.ini')
    default = config["DEFAULT"]
    content = default.get("content")
    helper_port = default.getint("helper_port", 8000)
    server_port = default.getint("server_port", 8000)
    server_ip_address = default.get("server_ip_address", "localhost")
    displayType = default.get("display_type", "screen")

    return(config)

helper_port = 8000 # Will be replaced by value in defaults.ini
server_port = 8082 # Will be replaced by value in defaults.ini
server_ip_address = "localhost" # Will be replaced by value in defaults.ini
address = "" # Accept packets from all interfaces
content = ""
displayType = "screen"

configFile = readDefaultConfiguration()

httpd = HTTPServer((address, helper_port), RequestHandler)
httpd.serve_forever()
