import subprocess
import signal
import sys

def quit_handler(sig, frame):

    sys.exit(0)

signal.signal(signal.SIGINT, quit_handler)

filename = 'control_server.py'
while True:
    p = subprocess.run(["python3", filename])

    # p = 0 if we pressed ctrl-c to quit. Scheduled reboots have p = 1
    if p != 0:
        continue
    else:
        break
