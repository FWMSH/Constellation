from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
import time
from datetime import datetime
import configparser

ADDR = "" # Accept connections from all interfaces
PORT = 8082

class ExhibitComponent:

    # Holds basic data about a component in the exhibit

    def __init__(self, id):

        self.id = id
        self.lastContactDateTime = datetime.now()
        self.lastInteractionDateTime = datetime(2020, 1, 1)

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


class RequestHandler(SimpleHTTPRequestHandler):

    componentList = []
    currentExhibitConfiguration = {}

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.loadCurrentExhibitConfiguration()


    def loadCurrentExhibitConfiguration(self):

        # Read the current exhibit configuration from file and initialize it
        # in self.currentExhibitConfiguration

        config = configparser.ConfigParser()
        config.read('currentExhibitConfiguration.ini')

    def getExhibitComponent(self, id):

        # Return a component with the given id, or None if no such
        # component exists

        component = next((x for x in self.componentList if x.id == id), None)

        return(component)

    def addExhibitComponent(self, id):

        component = ExhibitComponent(id)
        self.componentList.append(component)

        return(component)

    def updateExhibitComponentStatus(self, data):

        id = data["id"]

        component = self.getExhibitComponent(id)
        if component is None: # This is a new id, so make the component
            component = self.addExhibitComponent(id)

        component.updateLastContactDateTime()
        if "currentInteraction" in data:
            if data["currentInteraction"].lower() == "true":
                component.updateLastInteractionDateTime()

    def sendCurrentConfiguration(self):

        # Function to respond to a POST with a string defining the current
        # exhibit configuration

        self.wfile.write(b"POST received")

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
        except:
            return() # No id, so bail out

        self.updateExhibitComponentStatus(data)
        self.sendCurrentConfiguration()


httpd = HTTPServer((ADDR, PORT), RequestHandler)
httpd.serve_forever()
