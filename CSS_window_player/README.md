# Media Player

## Introduction
The media player displays images and videos using the browser as its rendering engine. The player and its optional kiosk are implemented in JavaScript

## Terminology
* `collateral`: Material other than the `content`, such as thumbnails, label text, etc.
* `content`: A single media file to be displayed by the player, such as one image or one video.

## Setting up the media player

### Installation

Every instance of the media player requires an instance of the `system helper`. The `system helper`'s files should be placed in the same directory as the media player.

The media player is based on HTML 5 and JavaScript, so it should work on any modern browser; however, it has only been tested significantly on Chromium.

## Using the kiosk

The media player includes an optional kiosk, `player_kiosk.html`, that allows a user to control the media player from an external device. The kiosk can also provide a label for each piece of `content`.

### Displaying the kiosk
From a remote device, use a web browser to connect to the `system helper` with `player_kiosk.html` as the pathname. For example, `http://10.8.0.125:8082/player_kiosk.html`.

### Configuring collateral
Properly displaying the kiosk requires adding several pieces of `collateral`, which are described below.

#### Thumbnails
Each piece of `content` may have a single thumbnail, regardless of how many `exhibits` it belongs to. That thumbnail should be a square PNG of any resolution, although resolutions over 768x768 are unnecessarily large. The thumbnail must have the same file name as the `content`, with an extension of `.png`. Thumbnails should be placed in the directory called `thumbnails`.

For example, the media file `myVideo.mp4` should have thumbnail `myVideo.png`. Depending on your browser and operating system, matching the case of the extension may be necessary. If a suitable thumbnail is not found, the default image of a magnifying glass is used. Thumbnails may have transparency.

#### Labels
Each piece of `content` should have a label for both English and Spanish. This label is a plain text file with the same filename as the media, but using the extension `.txt`. The label may be richly formatted using [Markdown](https://www.markdownguide.org/basic-syntax/).

For example, the media file `myImage.JPG` should have a label `myImage.txt`. If a suitable label cannot be found, the label display panel on the kiosk will display blank. Labels should be placed in nesting subfolders, with the first folder being `labels`, followed by the name of each `exhibit`, followed by `en` and `es`.

#### Titles
Each piece of `content` can have a display name, which appears on its button in the kiosk interface. The kiosk itself can also have a title, which appears in both the attractor and at the top of the interface.

These titles are specified in the file `dictionary.ini`, which should be placed in the root of the media player directory. The INI file should have a section `[EN]` for English and `[ES]` for Spanish, as such:

```
[EN]
myVideo.mp4 = Centripetal Force Example
myImage.JPG = A Geometric Design
mySecondImage.png = A Beautiful Sunset

[ES]
myVideo.mp4 = Ejemplo de fuerza centrípeta
myImage.JPG = Un diseño geométrico
mySecondImage.png = Una hermosa puesta de sol
```

Because of the format of an INI file, titles may not have an equals sign (`=`) in them.

## Sample directory structure
The following code snippet shows the directory structure for a complete media player and kiosk.

```
media_player/
    content/
        exhibit1/
            myVideo.mp4
            myImage.JPG
        exhibit2/
            myVideo.mp4
            mySecondImage.png
    css/
        ...
    js/
        ...
    labels/
        exhibit1/
            en/
                myVideo.txt
                myImage.txt
            es/
                myVideo.txt
                myImage.txt
        exhibit2/
            en/
                myVideo.txt
                mySecondImage.txt
            es/
                myVideo.txt
                mySecondImage.txt
    thumbnails/
        myVideo.png
        myImage.png
        mySecondImage.png

    config.js
    dictionary.ini

    helper.py
    media_player.html
    player_kiosk.html
```
