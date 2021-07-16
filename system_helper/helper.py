# This application sets up a small server to communicate with user-facing interfaces
# and handle interacting with the system (since the browser cannot)

from http.server import HTTPServer, SimpleHTTPRequestHandler
import time
import datetime
import configparser
import json
import sys
import os
import serial
from sockio.sio import TCP
import signal
import cgi
import shutil
import psutil
import mimetypes
import socket
import dateutil.parser
import requests

class RequestHandler(SimpleHTTPRequestHandler):

    def log_request(code='-', size='-'):

        # Override to suppress the automatic logging

        pass

    def do_GET(self):

        # Receive a GET request and respond with a console webpage
        #print("do_GET: ENTER")
        #print("  ", self.path)
        global config
        if self.path == "/":
            pass
        elif self.path.lower().endswith(".html"):
            #print("  Handling HTML file", self.path)
            try:
                f = open(self.path[1:],"r")
            except IOError:
                self.send_error(404, "File Not Found: %s" % self.path)
                print(f"GET for unexpected file {self.path}")
                #print("do_GET: EXIT")
                return()

                #logging.error(f"GET for unexpected file {self.path}")

            page = str(f.read())
            # Build the address that the webpage should contact to reach this helper
            if self.address_string() == "127.0.0.1": # Request is coming from this machine too
                address_to_insert = "'http://localhost:" + config["helper_port"] + "'"
            else: # Request is coming from the network
                address_to_insert = "'http://" + socket.gethostbyname(socket.gethostname()) + config["helper_port"] + "'"
            # Then, insert that into the document
            page = page.replace("INSERT_HELPERIP_HERE", address_to_insert)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(page, encoding="UTF-8"))

            f.close()
            #print("do_GET: EXIT")
            return()
        else:
            # Open the file requested and send it
            mimetype = mimetypes.guess_type(self.path, strict=False)[0]
            #print(f"  Handling {mimetype}")
            try:
                #print(f"  Opening file {self.path}")
                f = open(self.path[1:], 'rb')
                #print(f"    File opened")
                self.send_response(200)
                self.send_header('Content-type', mimetype)
                self.end_headers()
                #print(f"    Writing data to client")
                self.wfile.write(f.read())
                #print(f"    Write complete")
                f.close()
                #print(f"  File closed")
                #print("do_GET: EXIT")
                return
            except IOError:
                self.send_error(404, "File Not Found: %s" % self.path)
                #logging.error(f"GET for unexpected file {self.path}")
        #print("do_GET: EXIT")

    def do_OPTIONS(self):
        # print("do_OPTIONS: ENTER")
        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
        # print("do_OPTIONS: EXIT")

    def do_POST(self):

        # Receives pings from client devices and respond with any updated
        # information
        # print("do_POST: ENTER")
        global configFile
        global config
        global clipList
        global commandList

        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

        # Get the data from the request
        ctype, pdict = cgi.parse_header(self.headers.get('content-type'))

        if (ctype == "multipart/form-data"): # File upload
            try:
                pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                content_len = int(self.headers.get('Content-length'))
                pdict['CONTENT-LENGTH'] = content_len
                fields = cgi.parse_multipart(self.rfile, pdict)
                file = fields.get('file')[0]

                root = os.path.dirname(os.path.abspath(__file__))
                content_path = os.path.join(root, "content")
                split = fields.get("exhibit")[0].split(".")
                if len(split) > 2:
                    exhibit = ".".join(spilt[:-2])
                else:
                    exhibit = split[0]
                filepath = os.path.join(content_path, fields.get("filename")[0])
                print(f"Saving uploaded file to {filepath}")
                with open(filepath, "wb") as f:
                    f.write(file)

                responseDict = {"success": True}
                json_string = json.dumps(responseDict)
                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            except:
                json_string = json.dumps({"success": False})
                self.wfile.write(bytes(json_string, encoding="UTF-8"))

        elif (ctype == "application/json"):

            # Unpack the data
            length = int(self.headers['Content-length'])
            data_str = self.rfile.read(length).decode("utf-8")

            try: # JSON
                data = json.loads(data_str)
            except: # not JSON
                data = {}
                split = data_str.split("&")
                for seg in split:
                    split2 = seg.split("=")
                    if len(split2) > 1:
                        data[split2[0]] = split2[1]
                    else:
                        print("Missing equal sign in argument:", seg, "in", data_str)

            if "action" in data:
                if data["action"] == "sleepDisplays":
                    sleepDisplays()
                elif data["action"] == "reboot":
                    reboot()
                elif data["action"] == "wakeDisplays":
                    wakeDisplays()
                elif data["action"] == "commandProjector":
                    if "command" in data:
                        commandProjector(data["command"])
                elif data["action"] == "getDefaults":
                    configToSend = dict(config.items())

                    # Reformat this content list as an array
                    configToSend['content'] = [s.strip() for s in configToSend['content'].split(",")]

                    if dictionary is not None:
                        # If there are multiple sections, build a meta-dictionary
                        if len(dictionary.items()) > 1:
                            meta_dict = {"meta": True}
                            for item in dictionary.items():
                                name = item[0]
                                meta_dict[name] = dict(dictionary.items(name))
                            configToSend["dictionary"] = meta_dict
                        else:
                            configToSend["dictionary"] = dict(dictionary.items("CURRENT"))
                    configToSend["availableContent"] = {"all_exhibits": getAllDirectoryContents()}

                    root = os.path.dirname(os.path.abspath(__file__))
                    content_path = os.path.join(root, "content")
                    configToSend["contentPath"] = content_path
                    json_string = json.dumps(configToSend)
                    self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif data["action"] == "updateDefaults":
                    update_made = False
                    if "content" in data:

                        if isinstance(data["content"], str):
                            content = data["content"]
                        elif isinstance(data["content"], list):
                            content = ""
                            for i in range(len(data["content"])):
                                file = (data["content"])[i]
                                if i != 0:
                                    content += ', '
                                content += file

                        # If content has changed, update our configuration
                        if content != config["content"]:
                            configFile.set("CURRENT", "content", content)
                            config["content"] = content
                            update_made = True
                    if "current_exhibit" in data:
                        if data["current_exhibit"] != config["current_exhibit"]:
                            configFile.set("CURRENT", "current_exhibit", data["current_exhibit"])
                            config["current_exhibit"] = data["current_exhibit"]
                            update_made = True

                    # Update file
                    if update_made:
                        with open('defaults.ini', 'w') as f:
                            configFile.write(f)
                elif data["action"] == "getAvailableContent":
                    active_content = [s.strip() for s in config["content"].split(",")]
                    response = {"all_exhibits": getAllDirectoryContents(),
                                "active_content": active_content,
                                "system_stats": getSystemStats()}

                    json_string = json.dumps(response)
                    self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif data["action"] == "getCurrentExhibit":
                    self.wfile.write(bytes(config["current_exhibit"], encoding="UTF-8"))
                elif data["action"] == "deleteFile":
                    if ("file" in data):
                        deleteFile(data["file"])
                        response = {"success": True}
                    else:
                        response = {"success": False,
                                    "reason": "Request missing field 'field'"}
                    json_string = json.dumps(response)
                    self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif data["action"] == 'copyFile':
                    if ("file" in data) and ("fromExhibit" in data) and ("toExhibit" in data):
                        copyFile(data["file"], data["fromExhibit"], data["toExhibit"])
                        response = {"success": True}
                    else:
                        response = {"success": False,
                                    "reason": "Request missing necessary field"}
                    json_string = json.dumps(response)
                    self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif data["action"] == "updateClipList":
                    if "clipList" in data:
                        clipList["clipList"] = data["clipList"]
                elif data["action"] == "updateActiveClip":
                    if "index" in data:
                        clipList["activeClip"] = data["index"]
                elif data["action"] == "getClipList":

                    # If we don't have a clip list, ask for one to be sent for
                    # next time.
                    if (len(clipList) == 0):
                        commandList.append("sendClipList")
                        self.wfile.write(bytes(json.dumps([]), encoding="UTF-8"))
                    else:
                        json_string = json.dumps(clipList)
                        self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif data["action"] == 'gotoClip':
                    if "clipNumber" in data:
                        commandList.append("gotoClip_"+str(data["clipNumber"]))
                elif data["action"] == "getUpdate":
                    responseDict = {"commands": commandList,
                                    "missingContentWarnings": missingContentWarningList}

                    event_content = checkEventSchedule()
                    if event_content is not None:
                        responseDict["content"] = event_content

                    json_string = json.dumps(responseDict)
                    try:
                        self.wfile.write(bytes(json_string, encoding="UTF-8"))
                    except socket.error as e:
                        print("Socket error in getUpdate:", e)
                    commandList = []
                elif data["action"] == "setAutoplay":
                    if "state" in data:
                        if data["state"] == "on":
                            commandList.append("enableAutoplay")
                        elif data["state"] == "off":
                            commandList.append("disableAutoplay")
                        elif data["state"] == "toggle":
                            commandList.append("toggleAutoplay")
                elif data["action"] == "seekVideo":
                    if ("direction" in data) and ("fraction" in data):
                        commandList.append("seekVideo_"+data["direction"]+"_"+str(data["fraction"]))
                elif data["action"] == "pauseVideo":
                    commandList.append("pauseVideo")
                elif data["action"] == "playVideo":
                    commandList.append("playVideo")
                elif data["action"] == 'getLabelText':
                    if "lang" in data:
                        lang = data["lang"]
                    else:
                        lang = "en"
                    if "name" in data:
                        root = os.path.dirname(os.path.abspath(__file__))
                        label_path = os.path.join(root, "labels", config["current_exhibit"], lang, data["name"])
                        try:
                            f = open(label_path,"r")
                            label = f.read()
                        except:
                            print(f"Error: Unknown label {data['name']} requested in language {lang} for exhibit {config['current_exhibit']}")
                            return()

                        self.wfile.write(bytes(label, encoding="UTF-8"))
                    else:
                        print(f"Error: Label requested without name")
                else:
                    print("Error: unrecognized action:", data["action"])
        #print("do_POST: EXIT")

def reboot():

    # Send an OS-appropriate command to restart the computer

    reboot_allowed = config.getboolean("allow_restart", True)

    if reboot_allowed:
        if sys.platform == "darwin": # MacOS
            os.system("osascript -e 'tell app \"System Events\" to restart'")
        elif sys.platform == "linux":
            os.system("systemctl reboot")
        elif sys.platform == "win32":
            os.system("shutdown -t 0 -r -f")

def sleepDisplays():

    if strToBool(config.get("allow_sleep", True)):
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
            if strToBool(config.get("allow_sleep", True)):
                ser.write(b"~0000 0\r")
        elif cmd == "checkState":
            ser.write(b"~00124 1\r")
            time.sleep(0.3)
            response = ser.readline()
            print(response)
        else:
            print(f"commandProjector: Error: Unknown command: {cmd}")

def deleteFile(file):

    # Function to delete a file

    root = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(root, "content", file)
    print("Deleting file:", file_path)
    os.remove(file_path)

def copyFile(filename, fromExhibit, toExhibit):

    # Function to copy a file from one exhibit to another

    root = os.path.dirname(os.path.abspath(__file__))
    file_path_from = os.path.join(root, "content", fromExhibit, filename)
    file_path_to = os.path.join(root, "content", toExhibit, filename)
    print("Copying file", file_path_from, "to", file_path_to)
    shutil.copyfile(file_path_from, file_path_to)

def getAllDirectoryContents():

    # Recursively search for files in the content directory and its subdirectories

    root = os.path.dirname(os.path.abspath(__file__))
    content_path = os.path.join(root, "content")
    result = [os.path.relpath(os.path.join(dp, f), content_path) for dp, dn, fn in os.walk(content_path) for f in fn]

    return([x for x in result if x.find(".DS_Store") == -1 ])

def getDirectoryContents(path):

    # Return the contents of an exhibit directory

    root = os.path.dirname(os.path.abspath(__file__))
    content_path = os.path.join(root, "content")
    contents = os.listdir(os.path.join(content_path, path))
    return([x for x in contents if x[0] != "."]) # Don't return hidden files

def checkDirectoryStructure():

    # Function that makes sure the appropriate content directories are present
    # and creates them if they are not.

    root = os.path.dirname(os.path.abspath(__file__))
    content_path = os.path.join(root, "content")
    try:
        os.listdir(content_path)
    except FileNotFoundError:
        print("Warning: content directory not found. Creating it...")

        try:
            os.mkdir(content_path)
        except:
            print("Error: unable to create directory. Do you have write permission?")

def strToBool(val):

    # Take a string value like "false" and convert it to a bool

    if isinstance(val, bool):
        return(val)
    else:
        val = str(val).strip()
        if val in ["false", "False"]:
            return(False)
        elif val in ["true", "True"]:
            return(True)
        else:
            print("strToBool: Error: ambiguous string", val)

def getSystemStats():

    # Function to return a dictionary with the total and free space available
    # on the disk where we are storing files, as well as the current CPU and RAM
    # load

    result = {}

    # Get the percentage the disk is full
    total, used, free = shutil.disk_usage(__file__)
    # Used is not right sometimes, so calulate it
    used = total - free
    result["disk_pct_free"] = round((free/total) * 100)
    result["disK_free_GB"] = round(free / (2**30)) # GB

    # Get CPU load
    cpu_load = [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()] # percent used in the last 1, 5, 15 min
    result["cpu_load_pct"] = round(cpu_load[1])

    # Get memory usage
    result["ram_used_pct"] = round(psutil.virtual_memory().percent)

    return(result)

def performManualContentUpdate(content):

    # Take the given list of content and update the control server

    global config

    # First, update the control server
    requestDict = {"class": "webpage",
                   "id": config["id"],
                   "action": "setComponentContent",
                   "content": content}

    headers = {'Content-type': 'application/json'}
    r = requests.post("http://" + config["server_ip_address"] + ":" + config["server_port"],
                        headers=headers, json=requestDict)

def retrieveSchedule():

    # Function to search the schedules directory for an appropriate schedule

    global schedule

    # Try several possible sources for the schedule with increasing generality
    root = os.path.dirname(os.path.abspath(__file__))
    sources_to_try = [config["current_exhibit"], "default"]
    today_filename = datetime.datetime.now().date().isoformat() + ".ini" # eg. 2021-04-14.ini
    today_day_filename = datetime.datetime.now().strftime("%A").lower() + ".ini" # eg. monday.ini
    schedule_to_read = None

    for source in sources_to_try:
        sched_path = os.path.join(root, "schedules", source)
        try:
            schedules = os.listdir(sched_path)
            if today_filename in schedules:
                print("Found schedule", today_filename, "in", source)
                schedule_to_read = os.path.join(sched_path, today_filename)
                break
            elif today_day_filename in schedules:
                print("Found schedule", today_day_filename, "in", source)
                schedule_to_read = os.path.join(sched_path, today_day_filename)
                break
            elif "default.ini" in schedules:
                print("Found schedule default.ini in", source)
                schedule_to_read = os.path.join(sched_path, "default.ini")
                break
        except FileNotFoundError:
            pass

    if schedule_to_read is not None:
        parser = configparser.ConfigParser(delimiters=("="))
        parser.read(schedule_to_read)
        if "SCHEDULE" in parser:
            readSchedule(parser["SCHEDULE"])
        else:
            print("retrieveSchedule: error: no INI section 'SCHEDULE' found!")
    else:
        # Check again tomorrow
        schedule = []
        schedule.append((datetime.time(0,1), "reload_schedule"))
        print("No schedule for today. Checking again tomorrow...")


def readSchedule(schedule_input):

    # Parse the configParser section provided in schedule and convert it for
    # later use

    global schedule
    global missingContentWarningList

    schedule = []
    missingContentWarningList = []

    root = os.path.dirname(os.path.abspath(__file__))
    content_path = os.path.join(root, "content")

    for key in schedule_input:
        time = dateutil.parser.parse(key).time()
        content = [s.strip() for s in schedule_input[key].split(",")]
        # Check to make sure that every file in the schedule actually exists.
        # Otherwise, add it to the warning list to be passed to the control server
        for item in content:
            if not os.path.isfile(os.path.join(content_path, item)):
                missingContentWarningList.append(item)
        schedule.append((time, content))

    # Add an event at 12:01 AM to retrieve the new schedule
    schedule.append((datetime.time(0,1), "reload_schedule"))

    queueNextScheduledEvent()

def queueNextScheduledEvent():

    # Cycle through the schedule and queue the next event

    global schedule
    global nextEvent
    global missingContentWarningList

    nextEvent = None

    if schedule is not None:
        sorted_sched = sorted(schedule)
        now = datetime.datetime.now().time()

        root = os.path.dirname(os.path.abspath(__file__))
        content_path = os.path.join(root, "content")

        for event in sorted_sched:
            time, content = event
            # If the content was previously missing, see if it is still missing
            # (the user may have fixed the problem)
            for item in content:
                if item in missingContentWarningList:
                    if  os.path.isfile(os.path.join(content_path, item)):
                        # It now exists; remove it from the warning list
                        missingContentWarningList = [ x for x in missingContentWarningList if x != item]
            if now < time:
                nextEvent = event
                break

def checkEventSchedule():

    # Check the nextEvent and see if it is time. If so, set the content

    global nextEvent

    content_to_retrun = None
    if nextEvent is not None:
        time, content = nextEvent
        #print("Checking for scheduled event:", content)
        #print(f"Now: {datetime.now().time()}, Event time: {time}, Time for event: {datetime.now().time() > time}")
        if datetime.datetime.now().time() > time: # It is time for this event!
            print("Scheduled event occurred:", time, content)
            if content == "reload_schedule":
                retrieveSchedule()
            else:
                performManualContentUpdate(content)
                content_to_retrun = content
            nextEvent = None

    queueNextScheduledEvent()
    return(content_to_retrun)

def readDefaultConfiguration():

    # Read defaults.ini
    config_object = configparser.ConfigParser(delimiters=("="))
    config_object.read('defaults.ini')
    default = config_object["CURRENT"]
    config_dict = dict(default.items())

    if "allow_audio" in config_dict and strToBool(config_dict["allow_audio"]) is True:
        print("Warning: You have enabled audio. Make sure the file is whitelisted in the browser or media will not play.")

    # Make sure we have the appropriate file system set up
    checkDirectoryStructure()

    return(config_object, config_dict)

def quit_handler(sig, frame):
    print('\nKeyboard interrupt detected. Cleaning up and shutting down...')
    sys.exit(0)

def loadDictionary():

    # look for a file called dictionary.ini and load it if it exists

    if "dictionary.ini" in os.listdir():
        parser = configparser.ConfigParser(delimiters=("="))
        parser.optionxform = str # Override the default, which is case-insensitive
        parser.read("dictionary.ini")
        return(parser)
    else:
        return(None)

if __name__ == "__main__":

    signal.signal(signal.SIGINT, quit_handler)

    schedule = None # Will be filled in during readDefaultConfiguration() if needed
    nextEvent = None
    missingContentWarningList = [] # Will hold one entry for every piece of content that is scheduled but not available
    configFile, config = readDefaultConfiguration()

    # If it exists, load the dictionary that maps one value into another
    dictionary = loadDictionary()

    # Look for an availble schedule and load it
    retrieveSchedule()

    # This is hold information about currently loaded media, e.g., for the player
    clipList = {}
    commandList = []

    print(f"Launching server on port {config['helper_port']} to serve {config['id']}.")

    httpd = HTTPServer(("", int(config["helper_port"])), RequestHandler)
    httpd.serve_forever()
