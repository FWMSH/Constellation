import serial
import pypjlink
import platform

def serial_connect_with_url(ip, baudrate=9600, make=None, port=None, protocol='socket', timeout=2):

    # Function to establish a serial connection over TCP/IP


    if (port is None) and (make is None):
        raise Exception("Must specifiy either a port or a make")
    elif port is None:

        port_dict = {"barco": 1025}

        if make.lower() in port_dict:
            port = port_dict[make.lower()]

    connection = serial.serial_for_url(protocol + "://" + ip + ":" + str(port),
                                baudrate=baudrate,
                                timeout=timeout)

    return(connection)

def serial_connect(baudrate=9600,
                   bytesize=serial.EIGHTBITS,
                   parity=serial.PARITY_NONE,
                   port=None,
                   stopbit=serial.STOPBITS_ONE,
                   timeout=2):

    # Connect to a serial device connected to the machine

    if port is None:
        # Assume we're using the default USB port for our platform

        system = platform.system()
        if system == "Linux":
            port = "/dev/ttyUSB0"
        elif system == "Darwin": # MacOS
            port = "/dev/ttyUSB0"
        elif system == "Windows":
            port = "COM1"
        else:
            raise Exception(f"Platform {system} is unknown: you must specify port=")

    connection = serial.Serial(port, baudrate, timeout=timeout, parity=parity, stopbits=stopbits, bytesize=bytesize)
    return(connection)


def serial_send_command(connection, command, debug=False, make=None):

    # Function to send a command to a projector, wait for a response and
    # return that response

    command_dict = {
        "get_source": {
            "barco": serial_barco_get_source,
        },
        "lamp_status": {
            "barco": serial_barco_lamp_status,
        },
        "power_off": {
            "barco": ":POWR0\r",
            "optoma": "~0000 0\r"
        },
        "power_on": {
            "barco": ":POWR1\r",
            "optoma": "~0000 1\r"
        },
        "power_state": {
            "barco": ":POST?\r",
            "optoma": "~00124 1\r"
        },
        "set_dvi_1": {
            "barco": ":IDVI1\r",
        },
        "set_dvi_2": {
            "barco": ":IDVI2\r",
        },
        "set_hdmi_1": {
            "barco": ":IHDM1\r",
        },
        "set_hdmi_2": {
            "barco": ":IHDM2\r",
        },
        "set_vga_1": {
            "barco": ":IVGA1\r",
        },
        "set_vga_2": {
            "barco": ":IVGA2\r",
        },
    }

    response_dict = {
        "power_state": {
            "barco": {
                "%001 POST 000000": "off",
                "%001 POST 000001": "off",
                "%001 POST 000002": "powering_on",
                "%001 POST 000003": "on",
                "%001 POST 000004": "powering_off",
                "%001 POST 000008": "powering_off"
            }
        }
    }

    if (command.lower() in command_dict) and (make is None):
        raise Exception("You must specify a projector make to use a command alias")

    command_to_send = None
    if debug: print(command)
    if command.lower() in command_dict:
        if debug: print("Command in command_dict")
        # First look up the command alias
        cmd_alias = command_dict[command.lower()]
        # Then, find the make-specific command
        if make.lower() in cmd_alias:
            if debug: print(f"Make {make} in cmd_alias")
            command_to_send = cmd_alias[make.lower()]
            if debug: print(f"command_to_send: {command_to_send}")
            # If this command is a function, call it instead of continuing
            if callable(command_to_send):
                response = command_to_send(connection)
                return(response)
    else:
        # We've been given a custom command
        command_to_send = command

    if command_to_send is not None:
        connection.write(bytes(command_to_send, 'UTF-8'))
        response = connection.readline().decode("UTF-8").strip()

        if make is not None:
            if command.lower() in response_dict:
                responses_by_make = response_dict[command.lower()]
                if make.lower() in responses_by_make:
                    responses = responses_by_make[make.lower()]
                    if response in responses:
                        response = responses[response]
    else:
        print(f"Command alias {command} not found for make {make}")
        return("")

    return(response)


def serial_barco_lamp_status(connection):

    # Function to build the lamp status list for a Barco projector
    # This list has format [(lamp1_hours, lamp1_on), (lamp2_hours, lamp2_on)]

    # True means lamp is on (or warming up)
    lamp_status_codes = {
    "0": False,
    "1": True,
    "2": True,
    "3": False,
    "4": False,
    }

    lamp_status = []

    l1_hours_response = serial_send_command(connection, ":LTR1?\r")
    l1_hours = int(l1_hours_response[10:])
    l1_state_response = serial_send_command(connection, ":LST1?\r")
    l1_state = l1_state_response[-1]
    l2_hours_response = serial_send_command(connection, ":LTR2?\r")
    l2_hours = int(l2_hours_response[10:])
    l2_state_response = serial_send_command(connection, ":LST2?\r")
    l2_state = l2_state_response[-1]

    if l1_state != '5':
        lamp_status.append((l1_hours, lamp_status_codes[l1_state]))
    if l2_state != '5':
        lamp_status.append((l2_hours, lamp_status_codes[l2_state]))

    return(lamp_status)

def serial_barco_get_source(connection):

    # Iterate through the Barco inputs to find the one that is active

    # (Barco name, English name, number)
    inputs = [("IDVI", "DVI"),("IHDM", "HDMI"), ("IVGA", "VGA"),("IDHD", "Dual Head DVI"),
                ("IDHH", "Dual Head HDMI"),("IDHX", "Dual Head XP2"), ("IXP2", "XP2"),
                ("IYPP", "Component")]

    for input in inputs:
        code, name = input
        #print(":"+code+"?\r")
        response = serial_send_command(connection, ":"+code+"?\r")
        if len(response) > 0:
            num = response[-1]
            if num != "0":
                return(name + " " + num)

    return("")


def pjlink_connect(ip, password=None, timeout=2):

    # Function to connect to a PJLink projector using pypjlink

    projector = pypjlink.Projector.from_address(ip, timeout=timeout)
    projector.authenticate(password=password)

    return(projector)


def pjlink_send_command(connection, command):

    if command == "error_status":
        return(connection.get_errors())
    elif command == "get_model":
        return(connection.get_manufacturer() + " " + connection.get_product_name())
    elif command == "lamp_status":
        return(connection.get_lamps())
    elif command == "power_off":
        connection.set_power("off")
        return("off")
    elif command == "power_on":
        connectino.set_power("on")
        return("on")
    elif command == "power_state":
        return(connection.get_power())
    else:
        print(f"Command alias {command} not found for PJLink")
