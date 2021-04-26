# Control Server

## Introduction
The control server coordinates communication between **_Constellation_** components and provides a web-based interface for controlling them. The server is implemented in Python 3 and the web console in Javascript.

## Terminology

* `gallery`: A physical space in which `exhibit`s take place.
* `exhibit`: The particular configuration of a `gallery`, including the inclusion or exclusion of specific `component`s and the `content` displayed by each `component`.
* `component`: A single display element within a `gallery`. This could be a projector, a screen, an iPad, or a hands-on mechanical interactive.
* `content`: The information being used by a `component`, such as text, images, video, and local configurations. Content specifies the file(s) on the component machine that should be used.
* `id`: A unique identifier for a given `component`. No two `component`s can have the same `id`.
* `type`: A user-defined grouping of `component`s. For example, if you have multiple screens each displaying similar information, you might assign them all the `type` of "INFO_SCREEN". `type`s allow you to send the same command to multiple devices. Every component must have a `type`.

## Setting up the control server

### Installation

This application requires Python 3.6 or later. To install, follow these steps:

1. Download the files from GitHub and place them somewhere permanent.
2. From a terminal within the directory, run `python3 -m pip install -r requirements.txt` or ensure you have the below requirements satisfied.
3. Edit `currentExhibitConfiguration.ini` to update the required parameters as described [here](#basic-configuration).
4. Run `python3 control_server.py` to start the server
5. To use the web console, open a browser and go to `http://<control_server_ip>:<control_server_port>`.

If you wish to run multiple control servers so you can manage separate galleries independently, you must create a separate directory and instance of the server files for each server you wish to instantiate. Each server will need its own port, but they can all share the same IP address.

#### Required packages

The following packages are required to install the control server. For `pip`, they are listed in `requirements.txt`.

* [`pypjlink2`](https://github.com/benoitlouy/pypjlink)

### Configuration

#### currentExhibitConfiguration.ini

A `currentExhibitConfiguration.ini` file should be placed in the same directory as `control_server.py`. It contains the basic setup parameters for the server. The delimiter for this INI file is the equals sign (=).

##### Basic configuration
The following keywords are required in your `currentExhibitConfiguration.ini`:

* `server_ip_address`: This is the public IP address of the control server. Note that a static IP address needs to be set at the OS or network level—this value merely records what that address is for distribution to remote clients.
* `server_port`: The port you wish the control server to be accessible at. This port must not already be in use. Make sure that this port is not being blocked by a firewall.
* `current_exhibit`: The name of the current exhibit configuration file in the form of `<name>.exhibit`. Once the control server is initialized, it will automatically adjust the value of this keyword as you change exhibits using the web console.

The following keywords are optional:

* `gallery_name`: The name of the physical space this control server corresponds to, such as "The Smith Dinosaur Hall."

##### Scheduling exhibit startup and shutdown

The contorl server can send commands to wake or sleep displays connected to every `component` and `projector` it controls. These are defined in `currentExhibitConfiguration.ini` and the keywords have the form `<day>_on` and `<day>_off`. The value for each keyword should be a time of day. These times can be specified in any common format, such as "2 PM", "2:00 PM", or "14:00". To omit a scheduled action, do not specify the keyword. An example schedule is below:

```
tuesday_on = 9 AM
tuesday_off = 5:00 PM
wednesday_on = 9 am
wednesday_off = 5:00 PM
thursday_on = 9 AM
thursday_off = 5:00 PM
friday_on = 9 AM
friday_off = 8 pm
saturday_on = 9 AM
saturday_off = 17:00
sunday_on = 12 PM
sunday_off = 5 PM
```

The easiest and best way to manage the schedule is through the web console's [Schedule Tab](#schedule-tab).

##### Controlling projectors
The control server can manage projectors over IP using the PJLink protocol. With this method, you can read the state of various internal projector parameters, as well as turn the projector on and off. Since this happens independently of whatever device is actually connected to the projector, projectors are not considered a `component` and do not have `content`.

Projectors are defined in the `[PROJECTORS]` section as such:

```
[PROJECTORS]
myprojector = 10.8.0.177
secureProjector = 10.8.1.235, thePassword
```
Each line defines one projector, in which the keyword becomes the `id`. Note that INI keywords are case insensitive; the `id` will be converted to uppercase when displayed in the web console. If a projector has a password for access to PJLink, specify it with a comma after the IP address. All projectors are assigned the `type` of "PROJECTOR."

#### Exhibit files
An exhibit file defines the content for a particular exhibit. It is in INI format, with the equals sign (=) as the separator. Each component has its own section. The `content` keyword defines the files that component should use. To specify multiple media pieces, separate them by a comma. For example, the content definition for two displays with `id`s of DISPLAY1 and DISPLAY2 would look like:

```
[DISPLAY1]
content = myvideo.mp4

[DISPLAY2]
content = anImage.jpg, myVideo2.MOV
```

Exhibit files should have the extension `.exhibit`, such as `space.exhibit`.

## Using the web console

The web console is the most convenient way of managing your settings and viewing the state of every `component`. It can be accessed through any modern web browser at the address `http://<control_server_ip>:<control_server_port>`.

### Components tab

The components tab lists every managed `component` and `projector`. Each receives its own tile, which is color-coded by the object's current state.

#### States

The following states apply to both `component`s and `projector`s:

* `ONLINE` (green): This object is currently operational.
* `WAITING` (yellow): This object was recently operational but has gone offline. This may be due to a temporary network or other issue. When a `component` is connected to a display that is sleeping, the OS or browser may allow processes to operate only on an interval. This often manifests as alternating between `ONLINE` and `WAITING`.
* `OFFLINE` (red): This object has been offline for an extended period of time. If this is due to a network issue, the `component` or `projector` may still be operating correctly from the perspective of the public, but it will not currently respond to commands.

The following states apply only to a `component`:

* `ACTIVE` (blue): This `component` is currently being interacted with by a person. For example, a touchscreen kiosk in which the touchscreen is being used.

The following states apply only to a `projector`:

* `STANDBY` (teal): The `projector` is accessible via PJLink but is currently powered off.

### Schedule tab

### Settings tab
