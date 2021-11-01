/*jshint esversion: 6 */

function sleepDisplays() {

  // Send a message to the local helper process and ask it to sleep the
  // displays

  // requestString = `action=sleepDisplays`;
  var requestString = JSON.stringify({"action": "sleepDisplays"});

  var xhr = new XMLHttpRequest();
  xhr.open("POST", helperAddress, true);
  xhr.timeout = 2000;
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function () {
    if (this.readyState != 4) return;

    if (this.status == 200) {
    }
  };
  xhr.send(requestString);
}

function wakeDisplays() {

  // Send a message to the local helper process and ask it to sleep the
  // displays

  // requestString = `action=wakeDisplays`;
  var requestString = JSON.stringify({"action": "wakeDisplays"});

  var xhr = new XMLHttpRequest();
  xhr.open("POST", helperAddress, true);
  xhr.timeout = 2000;
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function () {
    if (this.readyState != 4) return;

    if (this.status == 200) {
    }
};
  xhr.send(requestString);
}

function commandProjector(cmd) {

  // Send a message to the local helper process to control the projector

  // requestString = `action=commandProjector&command=${cmd}`;
  var requestString = JSON.stringify({"action": "commandProjector", "command": cmd});

  var xhr = new XMLHttpRequest();
  xhr.open("POST", helperAddress, true);
  xhr.timeout = 10000;
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function () {
    if (this.readyState != 4) return;

    if (this.status == 200) {
    }
};
  xhr.send(requestString);

}

function synchronize(timeToPlay) {

  // Function to set a timeout to begin playing the synchronized video

  setTimeout(function(){console.log("Play"); changeMedia("", false, true);}, Date.parse(timeToPlay) - Date.now());
}

function askToSynchronize(other_ids) {

  // Function to communicate with the control server and indicate that we
  // are ready to begin synchronization.

  console.log("Asking to synchronize with", other_ids);

  requestString = JSON.stringify({"class": "exhibitComponent",
                                  "id": id,
                                  "type": type,
                                  "action": "beginSynchronization",
                                  "synchronizeWith": other_ids.split(",")});

  var xhr = new XMLHttpRequest();
  xhr.timeout = 1000;
  xhr.open("POST", serverAddress, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(requestString);

}

function readUpdate(responseText) {

  // Function to read a message from the server and take action based
  // on the contents

  var update = JSON.parse(responseText);
  sendConfigUpdate(update); // Send to helper to update the default config

  if ('commands' in update) {
    for (var i=0; i<update.commands.length; i++) {
      var cmd = (update.commands)[i];

      if (cmd == "restart") {
        askForRestart();
      } else if (cmd == "shutdown") {
        askForShutdown();
      } else if (cmd == "sleepDisplays") {
          sleepDisplays();
      } else if (cmd == "wakeDisplays") {
          wakeDisplays();
      } else if (cmd == "refresh_page") {
          location.reload();
      } else if (cmd == "reloadDefaults"){
          askForDefaults();
      } else if (cmd.startsWith("beginSynchronization")){
          var timeToPlay = cmd.split("_")[1];
          synchronize(timeToPlay);
      } else if (cmd == "sendClipList") {
        updateClipList(sourceList);
      } else if (cmd.startsWith("gotoClip")) {
          var clipNumber = cmd.split("_")[1];
          gotoSource(clipNumber);
      } else if (cmd.startsWith("seekVideo")) {
          var seek = cmd.split("_");
          seekVideoByFraction(seek[1], parseFloat(seek[2]));
      } else if (cmd == "playVideo") {
          document.getElementById("fullscreenVideo").play();
      } else if (cmd == "pauseVideo") {
          document.getElementById("fullscreenVideo").pause();
      } else if (cmd == "disableAutoplay") {
          autoplayEnabled = false;
      } else if (cmd == "enableAutoplay") {
          autoplayEnabled = true;
      } else if (cmd == "toggleAutoplay") {
          autoplayEnabled = !autoplayEnabled;
      } else {
          console.log(`Command not recognized: ${cmd}`);
      }
    }
  }
  if ("id" in update) {
    id = update.id;
  }
  if ("type" in update) {
    type = update.type;
  }
  if (("server_ip_address" in update) && ("server_port" in update)) {
    serverAddress = "http://" + update.server_ip_address + ":" + update.server_port;
  }
  if ("contentPath" in update) {
    contentPath = update.contentPath;
  }
  if ("current_exhibit" in update) {
    currentExhibit = update.current_exhibit;
  }
  if ("synchornize_with" in update) {
    askToSynchronize(update.synchornize_with);
    waitingForSynchronization = true;
  }
  if ("missingContentWarnings" in update) {
    errorDict.missingContentWarnings = update.missingContentWarnings;
  }
  if ("allow_audio" in update) {
    // If desired, unmute the video
    // Note that the file will need to be whitelisted by the browser; otherwise,
    // it will not autoplay

    if (update.allow_audio.toLowerCase() === "true") {
      document.getElementById("fullscreenVideo").muted = false;
    } else {
      document.getElementById("fullscreenVideo").muted = true;
    }
  }
  if ("image_duration" in update) {
      if (isFinite(parseInt(update.image_duration))) {
        // Image duration is specified in seconds in defaults.ini
        // but needs to be converted to milliseconds
        image_duration = update.image_duration*1000;
        console.log(`Setting image duration: ${update.image_duration} seconds`);
      }
  }
  if ("allow_restart" in update) {
    allowedActionsDict.restart = update.allow_restart;
  }
  if ("allow_shutdown" in update) {
    allowedActionsDict.shutdown = update.allow_shutdown;
  }

  // This should be last to make sure the path has been updated
  if ("content" in update) {
    if (arraysEqual(sourceList, update.content) == false) {
      updateClipList(update.content);
      sourceList = update.content;
      gotoSource(0);
    }
  }
}

function seekVideoByFraction(direction, fraction) {

  // Seek to a point in the video given by the options.

  var video = document.getElementById("fullscreenVideo");

  var timeToGoTo;
  if (direction == "back") {
    timeToGoTo = video.currentTime - fraction*video.duration;
  } else if (direction == "forward") {
    timeToGoTo = video.currentTime + fraction*video.duration;
  }
  // Handle boundaries
  if (timeToGoTo < 0) {
    timeToGoTo += video.duration;
  } else if (timeToGoTo > video.duration) {
    timeToGoTo -= video.duration;
  }
  video.currentTime = timeToGoTo;
}

function updateClipList(list) {

  // Function that takes a list of filenames and passes it to the helper
  // to hold for potentially sharing with a player_kiosk instance.

  var requestString = JSON.stringify({"action": "updateClipList",
                                      "clipList": list});

  var xhr = new XMLHttpRequest();
  xhr.timeout = 2000;
  xhr.open("POST", helperAddress, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(requestString);
}

function updateActiveClip(index) {

  // Function that takes a list of filenames and passes it to the helper
  // to hold for potentially sharing with a player_kiosk instance.

  var requestString = JSON.stringify({"action": "updateActiveClip",
                                      "index": index});

  var xhr = new XMLHttpRequest();
  xhr.timeout = 2000;
  xhr.open("POST", helperAddress, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(requestString);
}

function arraysEqual(arr1, arr2) {

  // Function to check if two arrays have the same elements in the same order

  if (arr1.length != arr2.length) {
    return false;
  } else {
    for (var i=0; i<arr1.length; i++) {
      if (arr1[i] != arr2[i]) {
        return false;
      }
    }
    return true;
  }
}

function gotoSource(index) {

  // Load the media file from the sourceList with the given index

  // Make sure the index is an integer
  index = parseInt(index);

  if (debug) {
    console.log("gotoSource", index);
  }

  if (index < sourceList.length) {
    activeIndex = index;
    updateActiveClip(activeIndex);
    changeMedia(contentPath + '/'  + sourceList[index], waitingForSynchronization, false);
  }
}

function gotoNextSource() {

  // Display the next file in sourceList, looping to the beginning if
  // necessary

  if (debug) {
    console.log("gotoNextSource");
  }

  if (activeIndex + 1 >= sourceList.length) {
    activeIndex = 0;
  } else {
    activeIndex += 1;
  }

  gotoSource(activeIndex);
}

function changeMedia(source, delayPlay, playOnly) {

  // Load and play a media file given in source
  // delayPlay and playOnly are used when synchronizing multiple displays

  if (debug) {
    console.log("changeMedia", source, delayPlay, playOnly);
  }

  var video = document.getElementById("fullscreenVideo");
  var videoContainer = document.getElementById("videoOverlay");
  var image = document.getElementById("fullscreenImage");
  var imageContainer = document.getElementById("imageOverlay");

  if (playOnly == false) { // We are going to load the media before we play it
    // Split off the extension
    var split = source.split(".");
    var ext = split[split.length-1];

    if (["mp4", "mpeg", "m4v", "webm", "mov", "ogg", "mpg"].includes(ext.toLowerCase())) {
      clearTimeout(sourceAdvanceTimer); // Only used for pictures
      if (video.src != source) {
        video.pause();
        video.src = source;
        video.load();

      }
      if (sourceList.length > 1) { // Don't loop or onended will never fire
        video.loop = false;
        video.onended = function() {
          if (autoplayEnabled == true) {
            gotoNextSource();
          } else {
            video.play();
          }
        };
      } else {
        video.loop = true;
      }
      if (delayPlay == false) {
        video.play();
        videoContainer.style.opacity = 1;
        imageContainer.style.opacity = 0;
      }
    } else if (["png", "jpg", "jpeg", "tiff", "bmp", "heic", "webp"].includes(ext.toLowerCase())) {
      video.pause();
      videoContainer.style.opacity = 0;
      image.src = source;
      imageContainer.style.opacity = 1;
      sourceAdvanceTimer = setTimeout(gotoNextSource, image_duration);
    }
  } else {
    video.play();
    videoContainer.style.opacity = 1;
    imageContainer.style.opacity = 0;
  }
}

function askForRestart() {

  // Send a message to the local helper and ask for it to restart the PC

  var requestString = JSON.stringify({"action": "restart"});

  var xhr = new XMLHttpRequest();
  xhr.open("POST", helperAddress, true);
  xhr.timeout = 2000;
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(requestString);
}

function askForShutdown() {

  // Send a message to the local helper and ask for it to restart the PC

  var requestString = JSON.stringify({"action": "shutdown"});

  var xhr = new XMLHttpRequest();
  xhr.open("POST", helperAddress, true);
  xhr.timeout = 2000;
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(requestString);
}

function askForDefaults() {

  // Send a message to the local helper and ask for the latest configuration
  // defaults, then use them.

  var requestString = JSON.stringify({"action": "getDefaults"});

  var xhr = new XMLHttpRequest();
  xhr.open("POST", helperAddress, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function () {

    if (this.readyState != 4) return;

    if (this.status == 200) {
      readUpdate(this.responseText);
    }
  };
  xhr.send(requestString);
}

function sendPing() {

  // Contact the control server and ask for any updates

  if (serverAddress != "") {
    requestDict = {"class": "exhibitComponent",
                   "id": id,
                   "type": type,
                   "helperPort": helperAddress.split(":")[2],
                   "allowed_actions": allowedActionsDict};
    // See if there is an error to report
    var errorKeys = Object.keys(errorDict);
    var errorString = "";
    for (i=0; i< errorKeys.length; i++) {
      if (errorDict[errorKeys[i]].length > 0) {
        errorString += `${errorKeys[i]}: ${errorDict[errorKeys[i]]}`;
      }
    }
    if (errorString != "") {
      requestDict.error = errorString;
    }
    requestString = JSON.stringify(requestDict);

    var xhr = new XMLHttpRequest();
    xhr.open("POST", serverAddress, true);
    xhr.timeout = 2000;
    xhr.setRequestHeader('Content-Type', 'application/json');

    xhr.onreadystatechange = function () {

      if (this.readyState != 4) return;

      if (this.status == 200) {
        readUpdate(this.responseText);
      }
  };
    xhr.send(requestString);
  }
}

function checkForHelperUpdates() {

  // Function to ask the helper for any new updates, like switching between
  // media clips

  var requestString = JSON.stringify({"action": "getUpdate"});

  var xhr = new XMLHttpRequest();
  xhr.timeout = 50;
  xhr.open("POST", helperAddress, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function () {

    if (this.readyState != 4) return;

    if (this.status == 200) {
      readUpdate(this.responseText);
    }
};
  xhr.send(requestString);

}

function sendConfigUpdate(update) {

  // Send a message to the helper with the latest configuration to set as
  // the default

  var requestDict = {"action": "updateDefaults"};

  if ("content" in update) {
    requestDict.content = update.content;
  }
  if ("current_exhibit" in update) {
    requestDict.current_exhibit = update.current_exhibit;
  }

  var xhr = new XMLHttpRequest();
  xhr.timeout = 1000;
  xhr.open("POST", helperAddress, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(JSON.stringify(requestDict));
}