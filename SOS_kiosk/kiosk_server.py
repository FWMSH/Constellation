"""This application sets up a small server to communicate with the screen players
and handle interacting with the system (since the browser cannot)
"""

# Standard module imports
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import time
import json
import sys
import os
import signal
import threading
from pathlib import Path
import mimetypes

# Non-standard modules
import requests
from sockio.sio import TCP

# Constellation modules
import helper
import config

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    # Stub which triggers dispatch of requests into individual threads.
    daemon_threads = True

class RequestHandler(SimpleHTTPRequestHandler):

    def log_request(self, code='-', size='-'):

        """Override to suppress the automatic logging"""

        pass

    def do_GET(self):

        # Receive a GET request and respond appropriately

        if debug:
            print("GET received: ", self.path)

        if self.path=="/":
            self.path="/SOS_kiosk.html"

        # Open the static file requested and send it
        try:
            mimetype = mimetypes.guess_type(self.path, strict=False)[0]
            self.send_response(200)
            self.send_header('Content-type', mimetype)
            self.end_headers()
            with open('.' + self.path, 'rb') as f:
                self.wfile.write(f.read())
        except FileNotFoundError:
            print(f"Error: could not find file {self.path}")
        if debug:
            print("GET complete")

    def do_OPTIONS(self):

        if debug:
            print("DO_OPTIONS")

        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

        if debug:
            print("DO_OPTIONS complete")

    def do_POST(self):

        # Receives pings from client devices and respond with any updated
        # information

        if debug:
            print("POST Received", flush=True)

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
        except json.decoder.JSONDecodeError: # not JSON
            data = {}
            split = data_str.split("&")
            for seg in split:
                split2 = seg.split("=")
                data[split2[0]] = split2[1]

        if "action" in data:
            if debug:
                print(f'  {data["action"]}')
            if data["action"] == "getDefaults":
                config_to_send = dict(config.defaults_dict.items())

                if config.dictionary_object is not None:
                    config_to_send["dictionary"] = dict(config.dictionary_object.items("CURRENT"))

                json_string = json.dumps(config_to_send)
                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            elif data["action"] == "updateDefaults":
                if debug:
                    print("    waiting for defaultWriteLock")
                with defaultWriteLock:
                    helper.updateDefaults(data)
                if debug:
                    print("    defaultWriteLock released")
            elif data["action"] == "deleteFile":
                if "file" in data:
                    helper.deleteFile(os.path.join("/", "home", "sos", "sosrc", data["file"]), absolute=True)
                    response = {"success": True}
                else:
                    response = {"success": False,
                                "reason": "Request missing field 'file'"}
                json_string = json.dumps(response)
                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            elif data["action"] == "SOS_getCurrentClipName":
                current_clip = sendSOSCommand("get_clip_number")
                dataset = sendSOSCommand("get_clip_info " + current_clip)

                self.wfile.write(bytes(dataset, encoding="UTF-8"))
            elif data["action"] == "SOS_getClipList":
                # First, get a list of clips
                reply = sendSOSCommand("get_clip_info *", multiline=True)
                split = reply.split('\r\n')
                clip_list = []
                for segment in split:
                    split2 = segment.split(" ")
                    clip_list.append(" ".join(split2[1:]))

                # Then, get other improtant info
                clipDictList = []
                counter = 1
                for clip in clip_list:
                    if clip != '':
                        temp = {'name': clip, 'clipNumber': counter}
                        path = sendSOSCommand(f"get_clip_info {counter} clip_filename")
                        split = path.split('/')
                        if split[-2] == "playlist":
                            icon_root = '/'.join(split[:-2])
                        else:
                            icon_root = '/'.join(split[:-1])

                        icon_path = icon_root + '/media/thumbnail_big.jpg'
                        filename = ''.join(e for e in clip if e.isalnum()) + ".jpg"
                        temp["icon"] = filename
                        # Cache the icon locally for use by the app.
                        os.system(f'cp "{icon_path}" ./thumbnails/{filename}')

                        clipDictList.append(temp)
                    counter += 1
                json_string = json.dumps(clipDictList)
                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            elif data["action"] == "SOS_getPlaylistName":
                reply = sendSOSCommand("get_playlist_name")
                playlist = reply.split("/")[-1]

                self.wfile.write(bytes(playlist, encoding="UTF-8"))
            elif data["action"] == "SOS_openPlaylist":
                if "name" in data:
                    SOS_open_playlist(data["name"])
            elif data["action"] == "SOS_getState":
                reply = sendSOSCommand("get_state 0")

                # Parse the response (with nested braces) and build a dictionary
                state_dict = {}
                segment_list = []

                for char in reply:
                    if char == '{':
                        segment_list.append([])
                    elif char == '}':
                        if len(segment_list) == 1:
                            # Key-value are separated by a space
                            segment = ''.join(segment_list.pop())
                            split = segment.split(" ")
                            state_dict[split[0]] = split[1]
                        elif len(segment_list) == 2:
                            # Key-value are separated into two lists
                            key = ''.join(segment_list[0])
                            value = ''.join(segment_list[1])
                            state_dict[key] = value
                            segment_list = []
                        elif len(segment_list) > 2:
                            print("Error parsing state: too many nested braces")
                    else:
                        if len(segment_list) > 0:
                            segment_list[-1].append(char)

                json_string = json.dumps(state_dict)
                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            elif data["action"] == "SOS_gotoClip":
                if "clipNumber" in data:
                    sendSOSCommand("play " + data["clipNumber"])
            elif data["action"] == "SOS_moveSphere":
                if ("dLat" in data) and ("dLon" in data):
                    tilt = sendSOSCommand("get_tilt")
                    split = tilt.split(' ')
                    tiltX = float(split[0])
                    tiltY = float(split[1])
                    tiltZ = float(split[2])
                    dLat = float(data["dLat"])
                    dLon = float(data["dLon"])

                    sendSOSCommand(f"set_tilt {tiltX} {tiltY + dLat/2} {tiltZ + dLon/2}")
            elif data["action"] == "SOS_rotateX":
                if "increment" in data:
                    tilt = sendSOSCommand("get_tilt")
                    split = tilt.split(' ')
                    tiltX = float(split[0])
                    tiltY = float(split[1])
                    tiltZ = float(split[2])
                    dX = float(data['increment'])

                    sendSOSCommand(f"set_tilt {tiltX + dX} {tiltY} {tiltZ}")
            elif data["action"] == "SOS_rotateY":
                if "increment" in data:
                    tilt = sendSOSCommand("get_tilt")
                    split = tilt.split(' ')
                    tiltX = float(split[0])
                    tiltY = float(split[1])
                    tiltZ = float(split[2])
                    dY = float(data['increment'])

                    sendSOSCommand(f"set_tilt {tiltX} {tiltY + dY} {tiltZ}")
            elif data["action"] == "SOS_rotateZ":
                if "increment" in data:
                    tilt = sendSOSCommand("get_tilt")
                    split = tilt.split(' ')
                    tiltX = float(split[0])
                    tiltY = float(split[1])
                    tiltZ = float(split[2])
                    dZ = float(data['increment'])

                    sendSOSCommand(f"set_tilt {tiltX} {tiltY} {tiltZ + dZ}")
            elif data["action"] == "SOS_startAutorun":
                sendSOSCommand("set_auto_presentation_mode 1")
            elif data["action"] == "SOS_stopAutorun":
                sendSOSCommand("set_auto_presentation_mode 0")
            elif data["action"] == "SOS_readPlaylist":
                if "playlistName" in data:
                    reply = sendSOSCommand(f"playlist_read {data['playlistName']}", multiline=True)

                    self.wfile.write(bytes(reply, encoding="UTF-8"))
            elif data["action"] == 'getAvailableContent':
                active_content = \
                    [s.strip() for s in config.defaults_dict.get("content", "").split(",")]
                all_content = list(Path("/home/sos/sosrc/").rglob("*.[sS][oO][sS]"))
                response = {"all_exhibits": [str(os.path.relpath(x, '/home/sos/sosrc/')) for x in all_content],
                            "active_content": active_content,
                            "system_stats": helper.getSystemStats()}
                json_string = json.dumps(response)
                self.wfile.write(bytes(json_string, encoding="UTF-8"))
            else:
                print(f"Warning: action {data['action']} not recognized!")
        if debug:
            print("POST complete")


def sendSOSCommand(cmd, multiline=False):

    """Send a command to Science on a Sphere adn read its response"""

    if debug:
        print("    sendSOSCommand:", cmd)

    global sosSocket

    try:
        if not multiline:
            return sosSocket.write_readline(bytes(cmd + '\n', encoding='UTF-8')).decode('UTF-8').strip()
        else:
            sosSocket.write(bytes(cmd + '\n', encoding='UTF-8'))
            return(sosSocket.read(10000).decode("UTF-8"))
    except Exception as e:
        print(e)
        sosSocket = connectToSOS()

def sendPing():

    """Send a heartbeat message to the control server and process any response"""

    if debug:
        print("Sending ping")

    headers = {'Content-type': 'application/json'}
    request_dict = {"class": "exhibitComponent",
                   "id": config.defaults_dict["id"],
                   "type": config.defaults_dict["type"]}

    server_full_address = f"http://{str(config.defaults_dict['server_ip_address'])}:{str(config.defaults_dict['server_port'])}"

    try:
        response = requests.post(server_full_address, headers=headers, json=request_dict, timeout=1)
    except:
        type, value, traceback = sys.exc_info()
        print("Error sending request", type, value)
        return()

    updates = response.json()

    if "content" in updates:
        content = (updates["content"])[0] # No support for multiple files
        updates["content"] = [content]
        if content != config.defaults_dict.get("content", ""):
            print("new content detected:", content)
            SOS_open_playlist(content)

    if debug:
        print("    waiting for defaultWriteLock")
    with defaultWriteLock:
        helper.updateDefaults(updates)
    if debug:
        print("    defaultWriteLock released")
        print("Ping complete")

def sendPingAtInterval():

    """Send a ping, then spawn a thread that will call this function again"""

    global pingThread

    sendPing()
    pingThread = threading.Timer(5, sendPingAtInterval)
    pingThread.start()

def SOS_open_playlist(content):

    """Send an SOS command to change to the specified playlist"""

    sendSOSCommand("open_playlist " + content)
    sendSOSCommand("play 1")

def quit_handler(sig, frame):

    """Stop threads, shutdown connections, etc."""

    print('\nKeyboard interrupt detected. Cleaning up and shutting down...')

    if pingThread is not None:
        pingThread.cancel()
    if sosSocket != None:
        sosSocket.write(b'exit\n')
    sys.exit(0)

def connectToSOS():

    """Establish a connection with the Science on a Sphere application"""

    while True:
        # Sleep for 5 seconds so that we don't spam the connection
        print("Connecting in 5 seconds...")
        time.sleep(5)

        try:
            # Send Science on a Sphere command to begin communication
            sosSocket = TCP(config.defaults_dict["sos_ip_address"], 2468)
            sosSocket.write_readline(b'enable\n')
            print("Connected!")
            return sosSocket
        except:
            print("Error: Connection with Science on a Sphere failed to initialize. Make sure you have specificed sos_ip_address in defaults.ini, both computers are on the same network (or are the same machine), and port 2468 is accessible.")
            sosSocket = None

signal.signal(signal.SIGINT, quit_handler)

debug = False

# Threading resources
pingThread = None
defaultWriteLock = threading.Lock()

helper.readDefaultConfiguration(checkDirectories=False)
helper.loadDictionary()

sosSocket = connectToSOS()
sendPingAtInterval()

httpd = ThreadedHTTPServer(("", int(config.defaults_dict["helper_port"])), RequestHandler)
httpd.serve_forever()
