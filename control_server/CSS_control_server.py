from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
import time
from datetime import datetime
import configparser

ADDR = "" # Accept connections from all interfaces
PORT = 8082

class ExhibitComponent:

    # Holds basic data about a component in the exhibit

    def __init__(self, id, type):

        self.id = id
        self.type = type

        self.lastContactDateTime = datetime.now()
        self.lastInteractionDateTime = datetime(2020, 1, 1)

        self.config = {}
        self.updateConfiguration()

    def secondsSinceLastContact(self):

        diff = datetime.now() - self.lastContactDateTime
        return(diff.total_seconds())

    def secondsSinceLastInteraction(self):

        diff = datetime.now() - self.lastInteractionDateTime
        return(diff.total_seconds())

    def updateLastContactDateTime(self):

        # We've received a new ping from this component, so update its
        # lastContactDateTime

        self.lastContactDateTime = datetime.now()

    def updateLastInteractionDateTime(self):

        # We've received a new interaction ping, so update its
        # lastInteractionDateTime

        self.lastInteractionDateTime = datetime.now()

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
            self.config = dict(currentExhibitConfiguration.items(self.id))
        except configparser.NoSectionError:
            print(f"Error: there is no configuration available for component with id={self.id}")

class RequestHandler(SimpleHTTPRequestHandler):


    def sendCurrentConfiguration(self, id):

        # Function to respond to a POST with a string defining the current
        # exhibit configuration

        config = getExhibitComponent(id).config

        config_str = ""
        for key in config:
            config_str += key + "=" + config[key] + "__"

        self.wfile.write(bytes(config_str, encoding="UTF-8"))

    def log_request(code='-', size='-'):

        # Override to suppress the automatic logging

        pass

    def do_GET(self):

        # Receive a GET request and respond with a console webpage

        print('GET received... ')

    def do_POST(self):

        # Receives pings from client devices and respond with any updated
        # information

        print('POST received... ')
        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
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
            id = data["id"]
            type = data["type"]
        except:
            print("Error: ping received without id or type field")
            return() # No id or type, so bail out

        updateExhibitComponentStatus(data)
        self.sendCurrentConfiguration(id)

def loadCurrentExhibitConfiguration():

    # Read the current exhibit configuration from file and initialize it
    # in self.currentExhibitConfiguration

    global currentExhibitConfiguration

    # First, retrieve the config filename that defines the desired exhibit
    config = configparser.ConfigParser()
    config.read('currentExhibitConfiguration.ini')
    current = config["CURRENT"]
    currentExhibit = current["currentConfigFile"]
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

def updateExhibitComponentStatus(data):

    id = data["id"]
    type = data["type"]

    component = getExhibitComponent(id)
    if component is None: # This is a new id, so make the component
        component = addExhibitComponent(id, type)

    component.updateLastContactDateTime()
    if "currentInteraction" in data:
        if data["currentInteraction"].lower() == "true":
            component.updateLastInteractionDateTime()


componentList = []
currentExhibit = None # The INI file defining the current exhibit "name.exhibit"
currentExhibitConfiguration = None # the configParser object holding the current config

loadCurrentExhibitConfiguration()

httpd = HTTPServer((ADDR, PORT), RequestHandler)
httpd.serve_forever()
