from http.server import HTTPServer, SimpleHTTPRequestHandler
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
import traceback


class Projector:

    # Holds basic data about a projector

    def __init__(self, id, ip):

        self.id = id
        self.ip = ip # IP address of the projector

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
            projector = pypjlink.Projector.from_address(self.ip, timeout=2)
            projector.authenticate()

            if full:
                self.state["model"] = projector.get_manufacturer() + " " + projector.get_product_name()

            self.state["power_state"] = projector.get_power()
            self.state["lamp_status"] = projector.get_lamps()
            self.state["error_status"] = projector.get_errors()

            self.lastContactDateTime = datetime.datetime.now()
        except Exception as e:
            error = True

        if (error and (self.secondsSinceLastContact() > 60)):
            self.state["status"] = "OFFLINE"
        else:
            if self.state["power_state"] == "on":
                self.state["status"] = "ONLINE"
            else:
                self.state["status"] = "STANDBY"

    def queueCommand(self, cmd):

        # Function to send command to projector. Named "queueCommand" to match
        # what is used for exhibitComponents

        try:
            with pypjlink.Projector.from_address(self.ip, timeout=2) as projector:
                projector.authenticate()

                if cmd == "wakeDisplay":
                    projector.set_power("on")
                    self.state["power_state"] = "on"
                elif cmd == "sleepDisplay":
                    projector.set_power("off")
                    self.state["power_state"] = "off"
        except:
            pass

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
            logging.warning(f"there is no configuration available for component with id={self.id}")
        self.config["current_exhibit"] = currentExhibit[0:-8]

    def queueCommand(self, command):

        print(f"{self.id}: command queued: {command}")
        self.config["commands"].append(command)

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
            dict = {}
            dict["id"] = item.id
            dict["type"] = item.type
            if "content" in item.config:
                dict["content"] = item.config["content"]
            dict["class"] = "exhibitComponent"
            dict["status"] = item.currentStatus()
            dict["ip_address"] = item.ip
            dict["helperPort"] = item.helperPort
            componentDictList.append(dict)

        for item in projectorList:
            dict = {}
            dict["id"] = item.id
            dict["type"] = 'PROJECTOR'

            dict["class"] = "exhibitComponent"
            dict["status"] = item.state["status"]
            componentDictList.append(dict)

        # Also include an object with the status of the overall gallery
        dict = {}
        dict["class"] = "gallery"
        dict["currentExhibit"] = currentExhibit
        dict["availableExhibits"] = exhibitList
        dict["galleryName"] = gallery_name

        componentDictList.append(dict)

        # Also include an object containing the current schedule
        dict = {}
        dict["class"] = "schedule"
        for key in schedule_dict:
            if key != "Next event":
                dict[key] = schedule_dict[key].strftime("%I:%M %p").lstrip("0")
            else:
                nextTime, nextAction = schedule_dict[key]
                if nextTime is not None:
                    dict["Next time"] = nextTime.strftime("%A, %I:%M %p").replace(" 0", " ")
                    dict["Next action"] = nextAction
                else:
                    dict["Next time"] = "None"
                    dict["Next action"] = "None"
        componentDictList.append(dict)


        json_string = json.dumps(componentDictList)

        self.wfile.write(bytes(json_string, encoding="UTF-8"))

    def checkEventSchedule(self):

        # Read the "Next event" tuple in schedule_dict and take action if necessary

        global schedule_dict

        nextEventDateTime, nextAction = schedule_dict["Next event"]

        if nextEventDateTime is not None:
            if datetime.datetime.now() > nextEventDateTime:
                commandAllExhibitComponents(nextAction)
                queueNextOnOffEvent()

    def log_request(code='-', size='-'):

        # Override to suppress the automatic logging

        pass

    def do_GET(self):

        # Receive a GET request and respond with a console webpage

        if self.path == "/":

            f = open("webpage.html","r")
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
                return
            except IOError:
                self.send_error(404, "File Not Found: %s" % self.path)
                logging.error(f"GET for unexpected file {self.path}")


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
            logging.warning("POST received without content-type header")
            print(self.headers)

        if (ctype == "application/json"):

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
            if pingClass == "webpage":
                try:
                    action = data["action"]
                except:
                    print("Error: webpage ping received without action field")
                    return() # No id or type, so bail out
                if action == "fetchUpdate":
                    self.sendWebpageUpdate()
                elif action == "fetchProjectorUpdate":
                    if "id" in data:
                        proj = getProjector(data["id"])
                        if proj != None:
                            proj.update()
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
                elif action == "updateSchedule":
                    print("Schedule update received:", data["day"], data["onTime"], data["offTime"])

                    schedule = {}
                    schedule[data["day"].lower()+'_on'] = data["onTime"]
                    schedule[data["day"].lower()+'_off'] = data["offTime"]

                    updateSchedule(schedule)
                elif action == "setExhibit":
                    print("Changing exhibit to:", data["name"])

                    readExhibitConfiguration(data["name"], updateDefault=True)
                    loadDefaultConfiguration()
                elif action == "setComponentContent":
                    if ("id" in data) and ("content" in data):
                        print(f"Changing content for {data['id']}:", data['content'])
                        setComponentContent(data['id'], data['content'])

            elif pingClass == "exhibitComponent":
                if "action" in data: # not a ping
                    action = data["action"]
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
                            return()
                    except:
                        print("Error: exhibitComponent ping received without id or type field")
                        return() # No id or type, so bail out

                    self.checkEventSchedule()
                    updateExhibitComponentStatus(data, self.address_string())
                    self.sendCurrentConfiguration(id)
            else:
                print(f"Error: ping with unknown class '{pingClass}' received")
                return() # Bail out

def setComponentContent(id, contentList):

    global currentExhibitConfiguration
    global currentExhibit

    # Loop the content list and build a string to write to the config file
    content = ""
    for i in range(len(contentList)):
        if i != 0:
            content += ', '
        content += contentList[i]

    try:
        currentExhibitConfiguration.set(id, "content", content)
    except configparser.NoSectionError: # This exhibit does not have content for this component
        currentExhibitConfiguration.add_section(id)
        currentExhibitConfiguration.set(id, "content", content)

    # Update the component
    getExhibitComponent(id).updateConfiguration()

    # Write new configuration to file
    with open(currentExhibit, 'w') as f:
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


def updateSchedule(schedule):

    # Take a dictionary of schedule changes, update the schedule_dict, and
    # write the changes to file in currentExhibitConfiguration.ini

    readSchedule(schedule)
    queueNextOnOffEvent()

    config = configparser.ConfigParser()
    config.read('currentExhibitConfiguration.ini')
    config.remove_section("SCHEDULE")
    config.add_section("SCHEDULE")
    for key in schedule_dict:
        if key != "Next event":
            config.set("SCHEDULE", key, schedule_dict[key].strftime("%I:%M %p").lstrip("0"))

    # Write ini file back to disk
    with open('currentExhibitConfiguration.ini', "w") as f:
        config.write(f)

def readSchedule(schedule):

    # Take the schedule as a configparser section or dictionary and parse it to build
    # the dictionary used to turn the components on/off

    global schedule_dict

    for key in schedule:
        # Convert the time, e.g. "9 AM" into a datetime time
        try:
            schedule_dict[key] = dateutil.parser.parse(schedule[key]).time()
        except ValueError:
            if schedule[key] == "":
                try:
                    del schedule_dict[key]
                except:
                    pass
            else:
                print("readSchedule: error: unable to parse time:", schedule[key])
                logging.error(f'"readSchedule is unable to parse time: {schedule[key]}"')


def queueNextOnOffEvent():

    # Function to consult schedule_dict and set the next datetime that we should
    # send an on or off command

    global schedule_dict

    now = datetime.datetime.now() # Right now
    eventDate = datetime.datetime.now().date() # When the event is (start now and we will advance it)
    nextEventDateTime = None
    nextAction = None
    counter = 0

    while nextEventDateTime is None:

        if counter > 7: # There are going to be no matching dates
            break

        day_str = eventDate.strftime('%A').lower() # e.g., "monday"

        if day_str+"_on" in schedule_dict:
            on_time = datetime.datetime.combine(eventDate, schedule_dict[day_str+"_on"])
            if now < on_time: # We are before today's on time
                nextEventDateTime = on_time
                nextAction = "wakeDisplay"
                break
        if day_str+"_off" in schedule_dict:
            off_time = datetime.datetime.combine(eventDate, schedule_dict[day_str+"_off"])
            if now < off_time: # We are before today's off time
                nextEventDateTime = off_time
                nextAction = "sleepDisplay"
                break

        # If we are neither before the on time or the off time, go to tomorrow and loop again
        eventDate += datetime.timedelta(days=1)
        counter += 1

    schedule_dict["Next event"] = (nextEventDateTime, nextAction)
    if nextEventDateTime is not None:
        print(f"New event queued: {nextAction}, {nextEventDateTime}")
    else:
        print("No events to queue right now")

def checkAvailableExhibits():

    # Get a list of available "*.exhibit" configuration files

    global exhibitList

    for file in os.listdir("."):
        if file.endswith(".exhibit"):
            exhibitList.append(file)

def loadDefaultConfiguration():

    # Read the current exhibit configuration from file and initialize it
    # in self.currentExhibitConfiguration

    global serverPort
    global ip_address
    global gallery_name
    global projectorList

    # First, retrieve the config filename that defines the desired exhibit
    config = configparser.ConfigParser()
    config.read('currentExhibitConfiguration.ini')
    current = config["CURRENT"]
    serverPort = current.getint("server_port", 8080)
    ip_address = current.get("server_ip_address", "localhost")
    gallery_name =  current.get("gallery_name", "Constellation")

    try:
        schedule = config["SCHEDULE"]
        readSchedule(schedule)
    except KeyError:
        print("No on/off schedule to read")

    try:
        projectors = config["PROJECTORS"]
        projectorList = []
    except:
        print("No standalone projectors specified")
        projectors = []

    for key in projectors:
        if getProjector(key) is None:
            newProj = Projector(key, projectors[key])
            newProj.update()
            projectorList.append(newProj)

    # Then, load the configuration for that exhibit
    readExhibitConfiguration(current["current_exhibit"])

    # Queue the next on/off event
    queueNextOnOffEvent()

    # Update the components that the configuration has changed
    for component in componentList:
        component.updateConfiguration()

def readExhibitConfiguration(name, updateDefault=False):

    global currentExhibitConfiguration
    global currentExhibit

    currentExhibit = name
    currentExhibitConfiguration = configparser.ConfigParser()
    currentExhibitConfiguration.read(name)

    if updateDefault:
        config = configparser.ConfigParser()
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

    # Return a component with the given id, or None if no such
    # component exists

    projector = next((x for x in projectorList if x.id == id), None)

    return(projector)

def addExhibitComponent(id, type):

    component = ExhibitComponent(id, type)
    componentList.append(component)

    return(component)

def commandAllExhibitComponents(cmd):

    # Queue a command for every exhibit component

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

def quit_handler(sig, frame):
    print('\nKeyboard interrupt detected. Cleaning up and shutting down...')
    logging.info("Server shutdown")
    sys.exit(0)

def error_handler(*exc_info):

    # Catch errors and log them to file

    text = "".join(traceback.format_exception(*exc_info)).replace('"', "'").replace("\n", "<newline>")
    logging.error(f'"{text}"')
    print(f"Error: see control_server.log for more details ({datetime.datetime.now()})")


serverPort = 8080 # Default; should be set in exhibit INI file
ip_address = "localhost" # Default; should be set in exhibit INI file
ADDR = "" # Accept connections from all interfaces
gallery_name = ""
componentList = []
projectorList = []
synchronizationList = [] # Holds sets of displays that are being synchronized
currentExhibit = None # The INI file defining the current exhibit "name.exhibit"
exhibitList = []
currentExhibitConfiguration = None # the configParser object holding the current config
schedule_dict = {} # Will hold a list of on/off times for every day of the week

# Set up log file
logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S', filename='control_server.log', format='%(levelname)s, %(asctime)s, %(message)s', level=logging.DEBUG)
signal.signal(signal.SIGINT, quit_handler)
sys.excepthook = error_handler

logging.info("Server started")

checkAvailableExhibits()
loadDefaultConfiguration()

httpd = HTTPServer((ADDR, serverPort), RequestHandler)
httpd.serve_forever()
