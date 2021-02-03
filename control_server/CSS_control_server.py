from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
import time
from datetime import datetime

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

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.componentList = []

    def getExhibitComponent(self, id):

        # Return a component with the given id, or None if no such
        # component exists

        component = next((x for x in self.componentList if x.id == id), None)

        return(component)

    def addExhibitComponent(self, id):

        component = ExhibitComponent(id)
        self.componentList.append(component)

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

httpd = HTTPServer((ADDR, PORT), RequestHandler)
httpd.serve_forever()
