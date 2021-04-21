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

#### Required packages

### Configuration

#### currentExhibitConfiguration.ini

##### Basic configuration

##### Scheduling exhibit startup and shutdown

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

### Components tab

The components tab lists

### Schedule tab

### Settings tab
