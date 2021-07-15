from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import time
import logging
import datetime
import dateutil.parser
import configparser
import json
import os
import pypjlink
import mimetypes
import cgi
import signal
import sys
import shutil
import traceback
import threading, _thread
import wakeonlan

import projector_control # Our file


class Projector:

    # Holds basic data about a projector

    def __init__(self, id, ip, connection_type, mac_address=None, make=None, password=None):

        self.id = id
        self.ip = ip # IP address of the projector
        self.password = password # Password to access PJLink
        self.mac_address = mac_address # For use with Wake on LAN
        self.connection_type = connection_type
        self.make = make

        self.state = {"status": "OFFLINE"}
        self.lastContactDateTime = datetime.datetime(2020,1,1)

        self.update(full=True)

    def secondsSinceLastContact(self):

        diff = datetime.datetime.now() - self.lastContactDateTime
        return(diff.total_seconds())

    def update(self, full=False):

        # Contact the projector to get the latest state
        error = False
        try:
            if self.connection_type == 'pjlink':
                connection = projector_control.pjlink_connect(self.ip, password=self.password)
                if full:
                    self.state["model"] = projector_control.pjlink_send_command(connection, "get_model")
                self.state["power_state"] = projector_control.pjlink_send_command(connection, "power_state")
                self.state["lamp_status"] = projector_control.pjlink_send_command(connection, "lamp_status")
                self.state["error_status"] = projector_control.pjlink_send_command(connection, "error_status")
            elif self.connection_type == "serial":
                connection = projector_control.serial_connect_with_url(self.ip, make=self.make)
                if full:
                    self.state["model"] = projector_control.serial_send_command(connection, "get_model", make=self.make)
                self.state["power_state"] = projector_control.serial_send_command(connection, "power_state", make=self.make)
                self.state["lamp_status"] = projector_control.serial_send_command(connection, "lamp_status", make=self.make)
                self.state["error_status"] = projector_control.serial_send_command(connection, "error_status", make=self.make)

            self.lastContactDateTime = datetime.datetime.now()
        except Exception as e:
            #print(e)
            error = True

        if (error and (self.secondsSinceLastContact() > 60)):
            self.state = {"status": "OFFLINE"}
            #self.state["status"] = "OFFLINE"
        else:
            if self.state["power_state"] == "on":
                self.state["status"] = "ONLINE"
            else:
                self.state["status"] = "STANDBY"

    def queueCommand(self, cmd):

        # Function to spawn a thread that sends a command to the projector.
        # Named "queueCommand" to match what is used for exhibitComponents

        print(f"Queuing command {cmd} for {self.id}")
        th = threading.Thread(target=self.sendCommand, args=[cmd])
        th.daemon = True
        th.start()

    def sendCommand(self, cmd):

        # Function to connect to a PJLink projector and send a command

        # Translate commands for projector_control
        cmd_dict = {
            "sleepDisplay": "power_off",
            "wakeDisplay": "power_on"
        }

        try:
            if self.connection_type == "pjlink":
                connection = projector_control.pjlink_connect(self.ip, password=self.password)
                if cmd in cmd_dict:
                    projector_control.pjlink_send_command(connection, cmd_dict[cmd])
                else:
                    projector_control.pjlink_send_command(connection, cmd)
            elif self.connection_type == "serial":
                connection = projector_control.serial_connect_with_url(self.ip, make=self.make)
                if cmd in cmd_dict:
                    projector_control.serial_send_command(connection, cmd_dict[cmd], make=self.make)
                else:
                    projector_control.serial_send_command(connection, cmd, make=self.make)

        except Exception as e:
            print(e)

class ExhibitComponent:

    # Holds basic data about a component in the exhibit

    def __init__(self, id, type):

        self.id = id
        self.type = type
        self.ip = "" # IP address of client
        self.helperPort = 8000 # port of the localhost helper for this component

        self.lastContactDateTime = datetime.datetime.now()
        self.lastInteractionDateTime = datetime.datetime(2020, 1, 1)

        self.config = {}
        self.config["commands"] = []
        self.updateConfiguration()

    def secondsSinceLastContact(self):

        diff = datetime.datetime.now() - self.lastContactDateTime
        return(diff.total_seconds())

    def secondsSinceLastInteraction(self):

        diff = datetime.datetime.now() - self.lastInteractionDateTime
        return(diff.total_seconds())

    def updateLastContactDateTime(self):

        # We've received a new ping from this component, so update its
        # lastContactDateTime

        self.lastContactDateTime = datetime.datetime.now()

    def updateLastInteractionDateTime(self):

        # We've received a new interaction ping, so update its
        # lastInteractionDateTime

        self.lastInteractionDateTime = datetime.datetime.now()

    def currentStatus(self):

        # Return the current status of the component
        # [OFFLINE, ONLINE, ACTIVE, WAITING]

        status = 'OFFLINE'

        if self.secondsSinceLastContact() < 30:
            if self.secondsSinceLastInteraction() < 10:
                status = "ACTIVE"
            else:
                status = "ONLINE"
        elif self.secondsSinceLastContact() < 300:
            status = "WAITING"

        return(status)

    def updateConfiguration(self):

        # Retreive the latest configuration data from the configParser object
        try:
            fileConfig = dict(currentExhibitConfiguration.items(self.id))
            for key in fileConfig:
                if key == 'content':
                    self.config[key] = [s.strip() for s in fileConfig[key].split(",")]
                else:
                    self.config[key] = fileConfig[key]
        except configparser.NoSectionError:
            print(f"Warning: there is no configuration available for component with id={self.id}")
            with logLock:
                logging.warning(f"there is no configuration available for component with id={self.id}")
        self.config["current_exhibit"] = currentExhibit[0:-8]

    def queueCommand(self, command):

        print(f"{self.id}: command queued: {command}")
        self.config["commands"].append(command)

class WakeOnLANDevice:

    # Hold basic information about a wake on LAN device and facilitate waking it

    def __init__(self, id, macAddress):

        self.id = id
        self.type = "WAKE_ON_LAN"
        self.macAddress = macAddress
        self.broadcastAddress = "255.255.255.255"
        self.port = 9
        self.ip = None
        self.state = {"status": "STANDBY"}

    def queueCommand(self, cmd):

        # Wrapper function to match other exhibit components

        if cmd in ["power_on", "wakeDisplay"]:
            self.wake()

    def wake(self):

        # Function to send a magic packet waking the device

        print(f"Sending wake on LAN packet to {self.id}")
        with logLock:
            logging.info(f"Sending wake on LAN packet to {self.id}")
        try:
            wakeonlan.send_magic_packet(self.macAddress,
                                        ip_address=self.broadcastAddress,
                                        port=self.port)
        except ValueError as e:
            print(f"Wake on LAN error for component {self.id}: {str(e)}")
            with logLock:
                logging.error(f"Wake on LAN error for component {self.id}: {str(e)}")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    # Stub which triggers dispatch of requests into individual threads.
    daemon_threads = True

class RequestHandler(SimpleHTTPRequestHandler):

    def sendCurrentConfiguration(self, id):

        # Function to respond to a POST with a string defining the current
        # exhibit configuration

        json_string = json.dumps(getExhibitComponent(id).config)
        getExhibitComponent(id).config["commands"] = [] # Clear the command list now that we have sent

        self.wfile.write(bytes(json_string, encoding="UTF-8"))

    def sendWebpageUpdate(self):

        # Function to collect the current exhibit status, format it, and send it
        # back to the web client to update the page

        componentDictList = []
        for item in componentList:
            temp = {}
            temp["id"] = item.id
            temp["type"] = item.type
            if "content" in item.config:
                temp["content"] = item.config["content"]
            if "error" in item.config:
                temp["error"] = item.config["error"]
            temp["class"] = "exhibitComponent"
            temp["status"] = item.currentStatus()
            temp["ip_address"] = item.ip
            temp["helperPort"] = item.helperPort
            componentDictList.append(temp)

        for item in projectorList:
            temp = {}
            temp["id"] = item.id
            temp["type"] = 'PROJECTOR'
            temp["ip_address"] = item.ip

            temp["class"] = "exhibitComponent"
            temp["status"] = item.state["status"]
            componentDictList.append(temp)

        for item in wakeOnLANList:
            temp = {}
            temp["id"] = item.id
            temp["type"] = 'WAKE_ON_LAN'
            temp["ip_address"] = item.ip

            temp["class"] = "exhibitComponent"
            temp["status"] = item.state["status"]
            componentDictList.append(temp)

        # Also include an object with the status of the overall gallery
        temp = {}
        temp["class"] = "gallery"
        temp["currentExhibit"] = currentExhibit
        temp["availableExhibits"] = exhibitList
        temp["galleryName"] = gallery_name

        componentDictList.append(temp)

        # Also include an object containing the current schedule
        with scheduleLock:
            temp = {}
            temp["class"] = "schedule"
            temp["updateTime"] = scheduleUpdateTime
            temp["schedule"] = scheduleList
            temp["nextEvent"] = nextEvent
            componentDictList.append(temp)

        json_string = json.dumps(componentDictList, default=str)

        self.wfile.write(bytes(json_string, encoding="UTF-8"))

    def log_request(code='-', size='-'):

        # Override to suppress the automatic logging

        pass

    def do_GET(self):

        # Receive a GET request and respond with a console webpage

        # print("+++++++++++++++")
        # print("BEGIN GET")
        print(f"Active threads: {threading.active_count()}       ", end="\r", flush=True)

        # print(f"  path = {self.path}")

        if self.path.lower().endswith("html") or self.path == "/":
            if self.path == "/":
                f = open("webpage.html","r")
            else:
                f = open("." + self.path, "r")

            page = str(f.read())

            # Build the address that the webpage should contact to reach this server
            address_to_insert = "'http://"+str(ip_address)+":"+str(serverPort)+"'"
            # Then, insert that into the document
            page = page.replace("INSERT_SERVERIP_HERE", address_to_insert)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(page, encoding="UTF-8"))

            f.close()
            # print("END GET")
            # print("+++++++++++++++")
            return

        else:

            # Open the file requested and send it
            mimetype = mimetypes.guess_type(self.path, strict=False)[0]
            try:
                f = open('.' + self.path, 'rb')
                self.send_response(200)
                self.send_header('Content-type', mimetype)
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
                # print("END GET")
                # print("+++++++++++++++")
                return
            except IOError:
                self.send_error(404, "File Not Found: %s" % self.path)
                with logLock:
                    logging.error(f"GET for unexpected file {self.path}")

        # print("END GET")
        # print("+++++++++++++++")


    def do_OPTIONS(self):

        # print("---------------")
        # print("BEGIN OPTIONS")

        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

        # print("END OPTIONS")
        # print("---------------")


    def do_POST(self):

        # Receives pings from client devices and respond with any updated
        # information

        # print("===============")
        # print("BEGIN POST")

        print(f"Active threads: {threading.active_count()}      ", end="\r", flush=True)

        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

        # Get the data from the request
        try:
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
        except:
            print("DO_POST: Error: Are we missing the Content-Type header?")
            with logLock:
                logging.warning("POST received without content-type header")
            print(self.headers)

        if (ctype == "application/json"):
            # print("  application/json")

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
                    data[split2[0]] = split2[1]

            try:
                pingClass = data["class"]
            except:
                print("Error: ping received without class field")
                return() # No id or type, so bail out

            # print(f"  class = {pingClass}")

            if pingClass == "webpage":
                try:
                    action = data["action"]
                except:
                    print("Error: webpage ping received without action field")
                    # print("END POST")
                    # print("===============")
                    return() # No id or type, so bail out
                # print(f"    action = {action}")
                if action == "fetchUpdate":
                    self.sendWebpageUpdate()
                elif action == "fetchProjectorUpdate":
                    if "id" in data:
                        proj = getProjector(data["id"])
                        if proj != None:
                            #proj.update()
                            json_string = json.dumps(proj.state)
                            self.wfile.write(bytes(json_string, encoding="UTF-8"))
                        else:
                            json_string = json.dumps({"status": "DELETE"})
                            self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif action == "reloadConfiguration":
                    loadDefaultConfiguration()

                    json_string = json.dumps({"result": "success"})
                    self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif action == "queueCommand":
                    getExhibitComponent(data["id"]).queueCommand(data["command"])
                elif action == "queueProjectorCommand":
                    getProjector(data["id"]).queueCommand(data["command"])
                    self.wfile.write(bytes("", encoding="UTF-8"))
                elif action == "queueWOLCommand":
                    getWakeOnLanComponent(data["id"]).queueCommand(data["command"])
                    self.wfile.write(bytes("", encoding="UTF-8"))
                elif action == "updateSchedule":
                    # This command handles both adding a new scheduled action
                    # and editing an existing action
                    error = False
                    error_message = ""

                    if "name" in data and "timeToSet" in data and "actionToSet" in data and "targetToSet" in data and "isAddition" in data:
                        line_to_set = f"{data['timeToSet']} = {data['actionToSet']}"
                        if data["targetToSet"] is None:
                            line_to_set += "\n"
                        else:
                            line_to_set += f", {data['targetToSet']}\n"

                        if (data["isAddition"]):
                            with scheduleLock:
                                root = os.path.dirname(os.path.abspath(__file__))
                                sched_dir = os.path.join(root, "schedules")

                                # Iterate through the existing schedule to make sure that we aren't
                                # adding a time that already exists
                                time_to_set = dateutil.parser.parse(data['timeToSet']).time()
                                with open(os.path.join(sched_dir, data["name"] + ".ini"), 'r') as f:
                                    for line in f.readlines():
                                        split = line.split("=")
                                        if len(split) == 2:
                                            # We have a valid ini line
                                            time = dateutil.parser.parse(split[0]).time()
                                            if time == time_to_set:
                                                error = True
                                                error_message = "An action with this time already exists"
                                if not error:
                                    with open(os.path.join(sched_dir, data["name"] + ".ini"), 'a') as f:
                                        f.write(line_to_set)
                        else:
                            if "timeToReplace" in data:
                                with scheduleLock:
                                    root = os.path.dirname(os.path.abspath(__file__))
                                    sched_dir = os.path.join(root, "schedules")
                                    outputText = ""
                                    time_to_replace = dateutil.parser.parse(data['timeToReplace']).time()

                                    with open(os.path.join(sched_dir, data["name"] + ".ini"), 'r') as f:
                                        for line in f.readlines():
                                            split = line.split("=")
                                            if len(split) == 2:
                                                # We have a valid ini line
                                                time = dateutil.parser.parse(split[0]).time()
                                                if time != time_to_replace:
                                                    # This line doesn't match, so add it for writing
                                                    outputText += line
                                                else:
                                                    outputText += line_to_set
                                            else:
                                                outputText += line

                                    with open(os.path.join(sched_dir, data["name"] + ".ini"), 'w') as f:
                                        f.write(outputText)

                    else:
                        error = True
                        error_message = "Missing one or more required keys"

                    if not error:
                        # Reload the schedule from disk
                        retrieveSchedule()

                        # Send the updated schedule back
                        with scheduleLock:
                            response_dict = {}
                            response_dict["class"] = "schedule"
                            response_dict["updateTime"] = scheduleUpdateTime
                            response_dict["schedule"] = scheduleList
                            response_dict["nextEvent"] = nextEvent
                            response_dict["success"] = True

                        json_string = json.dumps(response_dict, default=str)
                        self.wfile.write(bytes(json_string, encoding="UTF-8"))
                    else:
                        response_dict = {"success": False,
                                "reason": error_message}
                        json_string = json.dumps(response_dict, default=str)
                        self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif action == 'refreshSchedule':
                    # This command reloads the schedule from disk. Normal schedule
                    # changes are passed during fetchUpdate
                    retrieveSchedule()

                    # Send the updated schedule back
                    with scheduleLock:
                        response_dict = {}
                        response_dict["class"] = "schedule"
                        response_dict["updateTime"] = scheduleUpdateTime
                        response_dict["schedule"] = scheduleList
                        response_dict["nextEvent"] = nextEvent

                    json_string = json.dumps(response_dict, default=str)
                    self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif action == "convertSchedule":
                    if "date" in data and "from" in data:
                        with scheduleLock:
                            root = os.path.dirname(os.path.abspath(__file__))
                            sched_dir = os.path.join(root, "schedules")
                            shutil.copy(os.path.join(sched_dir, data["from"].lower() + ".ini"),
                                        os.path.join(sched_dir, data["date"] + ".ini"))

                        # Reload the schedule from disk
                        retrieveSchedule()

                        # Send the updated schedule back
                        with scheduleLock:
                            response_dict = {}
                            response_dict["class"] = "schedule"
                            response_dict["updateTime"] = scheduleUpdateTime
                            response_dict["schedule"] = scheduleList
                            response_dict["nextEvent"] = nextEvent

                        json_string = json.dumps(response_dict, default=str)
                        self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif action == "deleteSchedule":
                    if "name" in data:
                        with scheduleLock:
                            root = os.path.dirname(os.path.abspath(__file__))
                            sched_dir = os.path.join(root, "schedules")
                            os.remove(os.path.join(sched_dir, data["name"] + ".ini"))

                        # Reload the schedule from disk
                        retrieveSchedule()

                        # Send the updated schedule back
                        with scheduleLock:
                            response_dict = {}
                            response_dict["class"] = "schedule"
                            response_dict["updateTime"] = scheduleUpdateTime
                            response_dict["schedule"] = scheduleList
                            response_dict["nextEvent"] = nextEvent

                        json_string = json.dumps(response_dict, default=str)
                        self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif action == "deleteScheduleAction":
                    if "from" in data and "time" in data:
                        with scheduleLock:
                            root = os.path.dirname(os.path.abspath(__file__))
                            sched_dir = os.path.join(root, "schedules")
                            outputText = ""
                            time_to_delete = dateutil.parser.parse(data['time']).time()

                            with open(os.path.join(sched_dir, data["from"] + ".ini"), 'r') as f:
                                for line in f.readlines():
                                    split = line.split("=")
                                    if len(split) == 2:
                                        # We have a valid ini line
                                        time = dateutil.parser.parse(split[0]).time()
                                        if time != time_to_delete:
                                            # This line doesn't match, so add it for writing
                                            outputText += line
                                    else:
                                        outputText += line

                            with open(os.path.join(sched_dir, data["from"] + ".ini"), 'w') as f:
                                f.write(outputText)

                    # Reload the schedule from disk
                    retrieveSchedule()

                    # Send the updated schedule back
                    with scheduleLock:
                        response_dict = {}
                        response_dict["class"] = "schedule"
                        response_dict["updateTime"] = scheduleUpdateTime
                        response_dict["schedule"] = scheduleList
                        response_dict["nextEvent"] = nextEvent

                    json_string = json.dumps(response_dict, default=str)
                    self.wfile.write(bytes(json_string, encoding="UTF-8"))
                elif action == "setExhibit":
                    print("Changing exhibit to:", data["name"])

                    readExhibitConfiguration(data["name"], updateDefault=True)

                    # Update the components that the configuration has changed
                    for component in componentList:
                        component.updateConfiguration()
                elif action == "setComponentContent":
                    if ("id" in data) and ("content" in data):
                        print(f"Changing content for {data['id']}:", data['content'])
                        setComponentContent(data['id'], data['content'])
                elif action == "getHelpText":
                    try:
                        with open("README.md", 'r') as f:
                            text = f.read()
                            self.wfile.write(bytes(text, encoding="UTF-8"))
                    except:
                        with logLock:
                            logging.error("Unable to read README.md")
                else:
                    print(f"Error: Unknown webpage command received: {action}")
                    with logLock:
                        logging.error(f"Unknown webpage command received: {action}")

            elif pingClass == "exhibitComponent":
                if "action" in data: # not a ping
                    action = data["action"]
                    # if "id" in data:
                    #     print(f"    id = {data['id']}")
                    # print(f"    action = {action}")
                    if action == "getUploadedFile":
                        if "id" in data:
                            component = getExhibitComponent(data["id"])
                            if len(component.dataToUpload) > 0:
                                upload = component.dataToUpload.pop(0)
                                #json_string = json.dumps(upload)
                                #self.wfile.write(bytes(json_string, encoding="UTF-8"))
                                self.wfile.write(upload)
                    elif action == "beginSynchronization":
                        if "synchronizeWith" in data:
                            updateSynchronizationList(data["id"], data["synchronizeWith"])
                else: # it's a ping
                    try:
                        id = data["id"]
                        type = data["type"]
                        if id == "UNKNOWN":
                            #print(f"Warning: exhibitComponent ping with id=UNKNOWN coming from {self.address_string()}")
                            # print("END POST")
                            # print("===============")
                            return()
                    except:
                        print("Error: exhibitComponent ping received without id or type field")
                        # print("END POST")
                        # print("===============")
                        return() # No id or type, so bail out

                    # print(f"    id = {id}")
                    # print("    action = ping")

                    # self.checkEventSchedule()
                    updateExhibitComponentStatus(data, self.address_string())
                    self.sendCurrentConfiguration(id)
            elif pingClass == "tracker":
                if "action" in data:
                    action = data["action"]
                    if action == "getLayoutDefinition":
                        if "name" in data:
                            layout = configparser.ConfigParser(delimiters=("="))
                            layout.read("flexible-tracker/templates/" + data["name"] + ".ini")
                            layoutDefinition = {s:dict(layout.items(s)) for s in layout.sections()}
                            json_string = json.dumps(layoutDefinition)
                            self.wfile.write(bytes(json_string, encoding="UTF-8"))
                    elif action == "submitData":
                        if "data" in data and "name" in data:
                            with trackingDataWriteLock:
                                with open(os.path.join("flexible-tracker", "data", data["name"]+".txt"), "a") as f:
                                    try:
                                        json_str = json.dumps(data["data"])
                                        f.write(json_str + "\n")
                                        self.wfile.write(bytes(json.dumps({"success": True}), encoding="UTF-8"))
                                    except:
                                        print("flexible-tracker: submitData: error: Not valid JSON")
                                        self.wfile.write(bytes(json.dumps({"success": False}), encoding="UTF-8"))
                    elif action == "getAvailableDefinitions":
                        definitionList = []

                        for file in os.listdir(os.path.join("flexible-tracker", "templates")):
                            if file.endswith(".ini"):
                                definitionList.append(file)

                        self.wfile.write(bytes(json.dumps(definitionList), encoding="UTF-8"))
                    elif action == "checkConnection":
                        self.wfile.write(bytes(json.dumps({"success": True}), encoding="UTF-8"))
            else:
                print(f"Error: ping with unknown class '{pingClass}' received")
                # print("END POST")
                # print("===============")
                return() # Bail out
        # print("END POST")
        # print("===============")

def setComponentContent(id, contentList):

    global currentExhibitConfiguration
    global currentExhibit

    # Loop the content list and build a string to write to the config file
    content = ""
    for i in range(len(contentList)):
        if i != 0:
            content += ', '
        content += contentList[i]

    with currentExhibitConfigurationLock:
        try:
            currentExhibitConfiguration.set(id, "content", content)
        except configparser.NoSectionError: # This exhibit does not have content for this component
            currentExhibitConfiguration.add_section(id)
            currentExhibitConfiguration.set(id, "content", content)

    # Update the component
    getExhibitComponent(id).updateConfiguration()

    # Write new configuration to file
    with currentExhibitConfigurationLock:
        with open(os.path.join("exhibits", currentExhibit), 'w') as f:
            currentExhibitConfiguration.write(f)

def updateSynchronizationList(id, other_ids):

    # Function to manage synchronization. synchronizationList is a list of
    # dictionaries, with one dictionary for every set of synchronized displays.

    global synchronizationList
    print("received sync request:", id)
    print(synchronizationList)
    id_known = False
    index = 0
    match_index = -1
    for item in synchronizationList:
        if id in item["ids"]:
            id_known = True
            match_index = index
        index += 1

    if id_known == False:
        # Create a new dictionary
        temp = {}
        temp["ids"] = [id] + other_ids
        temp["checked_in"] = [False for i in temp["ids"]]
        (temp["checked_in"])[0] = True # Check in the current id
        synchronizationList.append(temp)
    else:
        index = (synchronizationList[match_index])["ids"].index(id)
        ((synchronizationList[match_index])["checked_in"])[index] = True
        if (all((synchronizationList[match_index])["checked_in"])):
            print("All components have checked in. Dispatching sync command")
            time_to_start = (datetime.datetime.now() + datetime.timedelta(seconds=10)).strftime("%m/%d/%Y %H:%M:%S.%f")
            for item in (synchronizationList[match_index])["ids"]:
                getExhibitComponent(item).queueCommand(f"beginSynchronization_{time_to_start}")
            # Remove this sync from the list in case it happens again later.
            synchronizationList.pop(match_index)

def pollEventSchedule():

    global pollingThreadDict

    checkEventSchedule()
    pollingThreadDict["eventSchedule"] = threading.Timer(10, pollEventSchedule)
    pollingThreadDict["eventSchedule"].start()

def pollProjectors():

    global pollingThreadDict

    #print("Polling projectors...")

    for projector in projectorList:
        th = threading.Thread(target=projector.update)
        th.daemon = True # So it dies if we exit
        th.start()

    pollingThreadDict["pollProjectors"] = threading.Timer(30, pollProjectors)
    pollingThreadDict["pollProjectors"].start()

def checkEventSchedule():

    # Read the "Next event" tuple in schedule_dict and take action if necessary
    # Also check if it's time to reboot the server

    global nextEvent
    global config
    global rebooting

    if nextEvent["date"] is not None:
        if datetime.datetime.now() > nextEvent["date"]:
            action = nextEvent["action"]
            target = None
            if isinstance(action, list):
                if len(action) == 1:
                    action = action[0]
                elif len(action) == 2:
                    target = action[1]
                    action = action[0]
                else:
                    print(f"Error: unrecofnized event format: {action}")
                    with logLock:
                        logging.error(f"Unrecofnized event format: {action}")
                    queueNextOnOffEvent()
                    return
            if action == 'reload_schedule':
                retrieveSchedule()
            elif action == 'set_exhibit' and target is not None:
                print("Changing exhibit to:", target)
                readExhibitConfiguration(target, updateDefault=True)

                # Update the components that the configuration has changed
                for component in componentList:
                    component.updateConfiguration()
            else:
                commandAllExhibitComponents(action)
                #print(f"DEBUG: Event executed: {nextEvent['action']} -- THIS EVENT WAS NOT RUN")
            queueNextOnOffEvent()

    # Check for server reboot time
    if serverRebootTime is not None:
        if datetime.datetime.now() > serverRebootTime:
            rebooting = True
            _thread.interrupt_main()

def retrieveSchedule():

    # Function to build a schedule for the next seven days based on the available
    # schedule files

    global scheduleList
    global scheduleUpdateTime

    with scheduleLock:
        scheduleUpdateTime = (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).total_seconds()
        scheduleList = [] # Each entry is a dict for a day, in calendar order

        today = datetime.datetime.today().date()
        this_week = [today + datetime.timedelta(days=x) for x in range(7)]

        for day in this_week:
            day_dict = {}
            day_dict["date"] = day.isoformat()
            day_dict["dayName"] = day.strftime("%A")
            day_dict["source"] = "none"
            reload_datetime = datetime.datetime.combine(day, datetime.time(0,1))
            day_schedule = [[reload_datetime, reload_datetime.strftime("%-I:%M %p"), ["reload_schedule"]]]

            date_specific_filename = day.isoformat() + ".ini" # e.g., 2021-04-14.ini
            day_specific_filename = day.strftime("%A").lower() + ".ini" # e.g., monday.ini

            root = os.path.dirname(os.path.abspath(__file__))
            sources_to_try = [date_specific_filename, day_specific_filename, 'default.ini']
            source_dir = os.listdir(os.path.join(root, "schedules"))
            schedule_to_read = None

            for source in sources_to_try:
                sched_path = os.path.join(root, "schedules", source)
                if source in source_dir:
                    schedule_to_read = os.path.join(root, "schedules", source)
                    if source == date_specific_filename:
                        day_dict["source"] = 'date-specific'
                    elif source == day_specific_filename:
                        day_dict["source"] = 'day-specific'
                    elif source == "default.ini":
                        day_dict["source"] = 'default'
                    break

            if schedule_to_read is not None:
                    parser = configparser.ConfigParser(delimiters=("="))
                    try:
                        parser.read(schedule_to_read)
                    except configparser.DuplicateOptionError:
                        print("Error: Schedule cannot contain two actions with identical times!")
                    if "SCHEDULE" in parser:
                        sched = parser["SCHEDULE"]
                        for key in sched:
                            time = dateutil.parser.parse(key).time()
                            eventTime = datetime.datetime.combine(day, time)
                            action = [s.strip() for s in sched[key].split(",")]
                            day_schedule.append([eventTime, eventTime.strftime("%-I:%M %p"), action])
                    else:
                        print("retrieveSchedule: error: no INI section 'SCHEDULE' found!")
            day_dict["schedule"] = sorted(day_schedule)
            scheduleList.append(day_dict)
    queueNextOnOffEvent()

def queueNextOnOffEvent():

    # Function to consult schedule_dict and set the next datetime that we should
    # send an on or off command

    global scheduleList
    global nextEvent

    now = datetime.datetime.now() # Right now
    eventDate = datetime.datetime.now().date() # When the event is (start now and we will advance it)
    nextEventDateTime = None
    nextAction = None
    counter = 0

    for day in scheduleList:
        sched = day["schedule"]
        for item in sched:
            if item[0] > now:
                nextEventDateTime = item[0]
                nextAction = item[2]
                break
        if nextEventDateTime is not None:
            break

    if nextEventDateTime is not None:
        nextEvent["date"] = nextEventDateTime
        nextEvent["time"] = nextEventDateTime.strftime("%-I:%M %p")
        nextEvent["action"] = nextAction
        print(f"New event queued: {nextAction}, {nextEventDateTime}")
    else:
        print("No events to queue right now")

def checkAvailableExhibits():

    # Get a list of available "*.exhibit" configuration files

    global exhibitList

    for file in os.listdir("exhibits"):
        if file.endswith(".exhibit"):
            exhibitList.append(file)

def loadDefaultConfiguration():

    # Read the current exhibit configuration from file and initialize it
    # in self.currentExhibitConfiguration

    global serverPort
    global ip_address
    global gallery_name
    global projectorList
    global wakeOnLANList
    global serverRebootTime

    # First, retrieve the config filename that defines the desired exhibit
    config = configparser.ConfigParser()
    with currentExhibitConfigurationLock:
        config.read('currentExhibitConfiguration.ini')
    current = config["CURRENT"]
    serverPort = current.getint("server_port", 8080)
    ip_address = current.get("server_ip_address", "localhost")
    gallery_name =  current.get("gallery_name", "Constellation")

    # try:
    #     schedule = config["SCHEDULE"]
    #     readSchedule(schedule)
    # except KeyError:
    #     print("No on/off schedule to read")
    retrieveSchedule()

    projectorList = []

    # Parse list of PJLink projectors
    try:
        pjlink_projectors = config["PJLINK_PROJECTORS"]
        print("Connecting to PJLink projectors...", end="\r", flush=True)
    except:
        print("No PJLink projectors specified")
        pjlink_projectors = []

    n_proj = len(pjlink_projectors)
    cur_proj = 0
    for key in pjlink_projectors:
        cur_proj += 1
        print(f"Connecting to PJLink projectors... {cur_proj}/{n_proj}", end="\r", flush=True)
        if getProjector(key) is None:
            # Try to split on a comma. If we get two elements back, that means
            # we have the form "ip, passwprd"
            split = pjlink_projectors[key].split(",")
            if len(split) == 2:
                # We have an IP address and a password
                ip = split[0].strip()
                password = split[1].strip()
                if password == "":
                    password = None
                newProj = Projector(key, ip, "pjlink", password=password)
            elif len(split) == 1:
                # We have an IP address only
                newProj = Projector(key, pjlink_projectors[key], "pjlink")
            else:
                print("Invalid PJLink projector entry:", pjlink_projectors[key])
                break
            projectorList.append(newProj)
    print("Connecting to PJLink projectors... done                      ")

    # Parse list of serial proejctors
    try:
        serial_projectors = config["SERIAL_PROJECTORS"]
        print("Connecting to serial projectors...", end="\r", flush=True)
    except:
        print("No serial projectors specified")
        serial_projectors = []

    n_proj = len(serial_projectors)
    cur_proj = 0
    for key in serial_projectors:
        cur_proj += 1
        print(f"Connecting to serial projectors... {cur_proj}/{n_proj}", end="\r", flush=True)
        if getProjector(key) is None:
            # Try to split on a comma. If we get two elements back, that means
            # we have the form "ip, passwprd"
            split = serial_projectors[key].split(",")
            if len(split) == 2:
                # We have an IP address and a make
                ip = split[0].strip()
                make = split[1].strip()
                if make == "":
                    make = None
                newProj = Projector(key, ip, "serial", make=make)
            elif len(split) == 1:
                # We have an IP address only
                newProj = Projector(key, serial_projectors[key], "serial")
            else:
                print("Invalid serial projector entry:", serial_projectors[key])
                break
            projectorList.append(newProj)
    print("Connecting to serial projectors... done                      ")

    # Parse list of serial proejctors
    try:
        wol = config["WAKE_ON_LAN"]
        print("Collecting wake on LAN devices...", end="", flush=True)

        for key in wol:
            wakeOnLANList.append(WakeOnLANDevice(key, wol[key]))
        print(" done")
    except:
        print("No wake on LAN devices specified")
        wakeOnLANList = []



    # Parse the reboot_time if necessary
    if "reboot_time" in current:
        reboot_time = dateutil.parser.parse(current["reboot_time"])
        if reboot_time < datetime.datetime.now():
            reboot_time += datetime.timedelta(days=1)
        serverRebootTime = reboot_time
        print("Server will reboot at:", serverRebootTime.isoformat())

    # Then, load the configuration for that exhibit
    readExhibitConfiguration(current["current_exhibit"])

    # Update the components that the configuration has changed
    for component in componentList:
        component.updateConfiguration()

def readExhibitConfiguration(name, updateDefault=False):

    global currentExhibitConfiguration
    global currentExhibit

    # We want the format of name to be "XXXX.exhibit", but it might be
    # "exhibits/XXXX.exhibit"
    error = False
    split_path = os.path.split(name)
    if len(split_path) == 2:
        if split_path[0] == "exhibits":
            name = split_path[1]
        elif split_path[0] == "":
            pass
        else:
            error = True
    else:
        error = True

    if error:
        # Something bad has happened. Display an error and bail out
        print(f"Error: exhibit definition with name {name} does not appear to be properly formatted. This file should be located in the exhibits directory.")
        with logLock:
            logging.error(f'Bad exhibit definition fileanme: {name}')
        return()

    currentExhibit = name
    currentExhibitConfiguration = configparser.ConfigParser()
    currentExhibitConfiguration.read(os.path.join("exhibits", name))

    if updateDefault:
        config = configparser.ConfigParser()
        with currentExhibitConfigurationLock:
            config.read('currentExhibitConfiguration.ini')
            config.set("CURRENT", "current_exhibit", name)
            with open('currentExhibitConfiguration.ini', "w") as f:
                config.write(f)

def getExhibitComponent(id):

    # Return a component with the given id, or None if no such
    # component exists

    component = next((x for x in componentList if x.id == id), None)

    return(component)

def getProjector(id):

    # Return a projector with the given id, or None if no such
    # component exists

    projector = next((x for x in projectorList if x.id == id), None)

    return(projector)

def getWakeOnLanComponent(id):

    # Return a projector with the given id, or None if no such
    # component exists

    component = next((x for x in wakeOnLANList if x.id == id), None)

    return(component)

def addExhibitComponent(id, type):

    component = ExhibitComponent(id, type)
    componentList.append(component)

    return(component)

def commandAllExhibitComponents(cmd):

    # Queue a command for every exhibit component

    print("Sending command to all components:", cmd)
    with logLock:
        logging.info(f"commandAllExhibitComponents: {cmd}")

    for component in componentList:
        component.queueCommand(cmd)

    for projector in projectorList:
        projector.queueCommand(cmd)

def updateExhibitComponentStatus(data, ip):

    id = data["id"]
    type = data["type"]

    component = getExhibitComponent(id)
    if component is None: # This is a new id, so make the component
        component = addExhibitComponent(id, type)

    component.ip = ip
    if "helperPort" in data:
        component.helperPort = data["helperPort"]
    component.updateLastContactDateTime()
    if "currentInteraction" in data:
        if data["currentInteraction"].lower() == "true":
            component.updateLastInteractionDateTime()
    if "error" in data:
        component.config["error"] = data["error"]
    else:
        if "error" in component.config:
            component.config.pop("error")

def checkFileStructure():

    # Check to make sure we have the appropriate file structure set up

    root = os.path.dirname(os.path.abspath(__file__))
    schedules_dir = os.path.join(root, "schedules")
    exhibits_dir = os.path.join(root, "exhibits")

    try:
        os.listdir(schedules_dir)
    except FileNotFoundError:
        print("Missing schedules directory. Creating now...")
        try:
            os.mkdir(schedules_dir)
            default_schedule_list = ["monday.ini", "tuesday.ini", "wednesday.ini", "thursday.ini", "friday.ini", "saturday.ini", "sunday.ini"]

            for file in default_schedule_list:
                with open(os.path.join(schedules_dir, file), 'w') as f:
                    f.write("[SCHEDULE]\n")
        except:
            print("Error: unable to create 'schedules' directory. Do you have write permission?")

    try:
        os.listdir(exhibits_dir)
    except FileNotFoundError:
        print("Missing exhibits directory. Creating now...")
        try:
            os.mkdir(exhibits_dir)
            with open(os.path.join(exhibits_dir, "default.exhibit"), 'w') as f:
                f.write("")
        except:
            print("Error: unable to create 'exhibits' directory. Do you have write permission?")

def quit_handler(sig, frame):

    # Function to handle cleaning shutting down the server

    if rebooting == True:
        print("\nRebooting server...")
        exit_code = 1
    else:
        print('\nKeyboard interrupt detected. Cleaning up and shutting down...')
        exit_code = 0

    for key in pollingThreadDict:
        pollingThreadDict[key].cancel()
    with logLock:
        logging.info("Server shutdown")
    with currentExhibitConfigurationLock:
        with scheduleLock:
            sys.exit(exit_code)

def error_handler(*exc_info):

    # Catch errors and log them to file

    text = "".join(traceback.format_exception(*exc_info)).replace('"', "'").replace("\n", "<newline>")
    with logLock:
        logging.error(f'"{text}"')
    print(f"Error: see control_server.log for more details ({datetime.datetime.now()})")


serverPort = 8080 # Default; should be set in exhibit INI file
ip_address = "localhost" # Default; should be set in exhibit INI file
ADDR = "" # Accept connections from all interfaces
gallery_name = ""
componentList = []
projectorList = []
wakeOnLANList = []
synchronizationList = [] # Holds sets of displays that are being synchronized
currentExhibit = None # The INI file defining the current exhibit "name.exhibit"
exhibitList = []
currentExhibitConfiguration = None # the configParser object holding the current config
nextEvent = {} # Will hold the datetime and action of the upcoming event
scheduleList = [] # Will hold a list of scheduled actions in the next week
scheduleUpdateTime = 0
serverRebootTime = None
rebooting = False # This will be set to True from a background thread when it is time to reboot
pollingThreadDict = {} # Holds references to the threads starting by various polling procedures

# threading resources
logLock = threading.Lock()
currentExhibitConfigurationLock = threading.Lock()
trackingDataWriteLock = threading.Lock()
scheduleLock = threading.Lock()

# Set up log file
logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S', filename='control_server.log', format='%(levelname)s, %(asctime)s, %(message)s', level=logging.DEBUG)
signal.signal(signal.SIGINT, quit_handler)
sys.excepthook = error_handler

with logLock:
    logging.info("Server started")

checkFileStructure()
checkAvailableExhibits()
loadDefaultConfiguration()
pollEventSchedule()
pollProjectors()

#httpd = HTTPServer((ADDR, serverPort), RequestHandler)
httpd = ThreadedHTTPServer((ADDR, serverPort), RequestHandler)
httpd.serve_forever()
