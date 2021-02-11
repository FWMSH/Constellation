from http.server import HTTPServer, SimpleHTTPRequestHandler
import time
import datetime
import dateutil.parser
import configparser
import json

ADDR = "" # Accept connections from all interfaces
# PORT = 8082

class ExhibitComponent:

    # Holds basic data about a component in the exhibit

    def __init__(self, id, type):

        self.id = id
        self.type = type
        self.ip = "" # IP address of client

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
                self.config[key] = fileConfig[key]
        except configparser.NoSectionError:
            print(f"Warning: there is no configuration available for component with id={self.id}")

    def queueCommand(self, command):

        print(f"{self.id}: command queued: {command}")
        self.config["commands"].append(command)

class RequestHandler(SimpleHTTPRequestHandler):

    def sendCurrentConfiguration(self, id):

        # Function to respond to a POST with a string defining the current
        # exhibit configuration

        json_string = json.dumps(getExhibitComponent(id).config)
        getExhibitComponent(id).config["commands"] = [] # Clear the command list now that we have sent them

        self.wfile.write(bytes(json_string, encoding="UTF-8"))

    def sendWebpageUpdate(self):

        # Function to collect the current exhibit status, format it, and send it
        # back to the web client to update the page

        componentDictList = []
        for item in componentList:
            dict = {}
            dict["id"] = item.id
            dict["type"] = item.type
            dict["class"] = "exhibitComponent"
            dict["status"] = item.currentStatus()
            componentDictList.append(dict)

        # Also include an object with the status of the overall gallery
        dict = {}
        dict["class"] = "gallery"
        dict["currentExhibit"] = currentExhibit
        componentDictList.append(dict)

        # Also include an object containing the current schedule
        dict = {}
        dict["class"] = "schedule"
        for key in schedule_dict:
            if key != "Next event":
                dict[key] = schedule_dict[key].strftime("%I:%M %p")
            else:
                nextTime, nextAction = schedule_dict[key]
                dict["Next time"] = nextTime.strftime("%A, %I:%M %p")
                dict["Next action"] = nextAction
        componentDictList.append(dict)


        json_string = json.dumps(componentDictList)

        self.wfile.write(bytes(json_string, encoding="UTF-8"))

    def checkEventSchedule(self):

        # Read the "Next event" tuple in schedule_dict and take action if necessary

        global schedule_dict

        nextEventDateTime, nextAction = schedule_dict["Next event"]

        if datetime.datetime.now() > nextEventDateTime:
            commandAllExhibitComponents(nextAction)
            queueNextOnOffEvent()

    def log_request(code='-', size='-'):

        # Override to suppress the automatic logging

        pass

    def do_GET(self):

        # Receive a GET request and respond with a console webpage

        try:
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
        except IOError:
            self.send_error(404, "File Not Found: %s" % self.path)

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
        length = int(self.headers['Content-length'])
        data_str = self.rfile.read(length).decode("utf-8")

        # Unpack the data string into a dict
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
            elif action == "reloadConfiguration":
                loadCurrentExhibitConfiguration()
                for component in componentList:
                    component.updateConfiguration()

                json_string = json.dumps({"result": "success"})
                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            elif action == "queueCommand":
                getExhibitComponent(data["id"]).queueCommand(data["command"])

        elif pingClass == "exhibitComponent":
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

def readSchedule(schedule):

    # Take the schedule as a configparser section and parse it to build
    # the dictionary used to turn the components on/off

    global schedule_dict

    for key in schedule:
        # Convert the time, e.g. "9 AM" into a datetime time
        schedule_dict[key] = dateutil.parser.parse(schedule[key]).time()

def queueNextOnOffEvent():

    # Function to consult schedule_dict and set the next datetime that we should
    # send an on or off command

    global schedule_dict

    now = datetime.datetime.now() # Right now
    eventDate = datetime.datetime.now().date() # When the event is (start now and we will advance it)
    nextEventDateTime = None

    while nextEventDateTime is None:
        day_str = eventDate.strftime('%A').lower() # e.g., "monday"

        if day_str+"_on" in schedule_dict:
            on_time = datetime.datetime.combine(eventDate, schedule_dict[day_str+"_on"])
            if now < on_time: # We are before today's on time
                nextEventDateTime = on_time
                nextAction = "wakeDisplay"
            elif day_str+"_off" in schedule_dict:
                off_time = datetime.datetime.combine(eventDate, schedule_dict[day_str+"_off"])
                if now < off_time: # We are before today's off time
                    nextEventDateTime = off_time
                    nextAction = "sleepDisplay"

        # If we are neither before the on time or the off time, go to tomorrow and loop again
        eventDate += datetime.timedelta(days=1)

    schedule_dict["Next event"] = (nextEventDateTime, nextAction)
    print(f"New event queued: {nextAction}, {nextEventDateTime}")

def loadCurrentExhibitConfiguration():

    # Read the current exhibit configuration from file and initialize it
    # in self.currentExhibitConfiguration

    global currentExhibitConfiguration
    global currentExhibit
    global serverPort
    global ip_address

    # First, retrieve the config filename that defines the desired exhibit
    config = configparser.ConfigParser()
    config.read('currentExhibitConfiguration.ini')
    current = config["CURRENT"]
    currentExhibit = current["currentConfigFile"]
    serverPort = current.getint("server_port", 8080)
    ip_address = current.get("server_ip_address", "localhost")

    schedule = config["SCHEDULE"]
    readSchedule(schedule)

    # Then, load the configuration for that exhibit
    currentExhibitConfiguration = configparser.ConfigParser()
    currentExhibitConfiguration.read(currentExhibit)

def getExhibitComponent(id):

    # Return a component with the given id, or None if no such
    # component exists

    component = next((x for x in componentList if x.id == id), None)

    return(component)

def addExhibitComponent(id, type):

    component = ExhibitComponent(id, type)
    componentList.append(component)

    return(component)

def commandAllExhibitComponents(cmd):

    # Queue a command for every exhibit component

    for component in componentList:
        component.queueCommand(cmd)

def updateExhibitComponentStatus(data, ip):

    id = data["id"]
    type = data["type"]

    component = getExhibitComponent(id)
    if component is None: # This is a new id, so make the component
        component = addExhibitComponent(id, type)

    component.ip = ip
    component.updateLastContactDateTime()
    if "currentInteraction" in data:
        if data["currentInteraction"].lower() == "true":
            component.updateLastInteractionDateTime()

serverPort = 8080 # Default; should be set in exhibit INI file
ip_address = "localhost" # Default; should be set in exhibit INI file
componentList = []
currentExhibit = None # The INI file defining the current exhibit "name.exhibit"
currentExhibitConfiguration = None # the configParser object holding the current config
schedule_dict = {} # Will hold a list of on/off times for every day of the week

loadCurrentExhibitConfiguration()
queueNextOnOffEvent()

httpd = HTTPServer((ADDR, serverPort), RequestHandler)
httpd.serve_forever()
