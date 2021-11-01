/*jshint esversion: 6 */

  class ExhibitComponent {

    constructor(id, type) {
      this.id = id;
      this.type = type;
      this.content = null;
      this.ip = ""; // Default; will be replaced when component pings in
      this.helperPort = 8000; // Default; will be replaced when component pings in
      this.state = {};
      this.status = "OFFLINE";
      this.allowed_actions = [];

      if (this.type == "PROJECTOR") {
        this.checkProjector();
        var thisInstance = this;
        this.pollingFunction = setInterval(function() {thisInstance.checkProjector();}, 5000);
      }
    }

    remove() {

      // Remove the component from its ComponentGroup
      getExhibitComponentGroup(this.type).removeComponent(this.id);
      // Remove the component from the exhibitComponents list
      var thisInstance = this;
      exhibitComponents = $.grep(exhibitComponents, function(el, idx) {return el.id == thisInstance.id;}, true);
      // Cancel the pollingFunction
      clearInterval(this.pollingFunction);
      // Rebuild the interface
      rebuildComponentInterface();
    }

    checkProjector() {

      // Function to ask the server to ping the projector
      var thisInstance = this;
      var requestDict = {"class": "webpage",
                         "action": "fetchProjectorUpdate",
                         "id": this.id};

      var xhr = new XMLHttpRequest();
      xhr.timeout = 2000;
      xhr.open("POST", serverIP, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.onreadystatechange = function () {
        if (this.readyState != 4) return;

        if (this.status == 200) {
          var response = JSON.parse(this.responseText);
          if ("status" in response) {
            if (response.status != "DELETE") {
                thisInstance.setStatus(response.status);
            } else {
              thisInstance.remove();
            }
            if ("model" in response) {
              thisInstance.state.model = response.model;
            }
            if ("power_state" in response) {
              thisInstance.state.power_state = response.power_state;
            }
            if ("lamp_status" in response) {
              thisInstance.state.lamp_status = response.lamp_status;
            }
            if ("error_status" in response) {
              thisInstance.state.error_status = response.error_status;
              Object.keys(response.error_status).forEach((item, i) => {
                if ((response.error_status)[item] != "ok") {
                  errorDict[thisInstance.id.toUpperCase() + ": " + item] = (response.error_status)[item]
                  rebuildErrorList();
                } else {
                  delete errorDict[thisInstance.id.toUpperCase() + ": " + item];
                }
              });
            }
          }
        }
      };
      xhr.send(JSON.stringify(requestDict));
    }

    setStatus(status) {

      this.status = status;
      $("#" + this.id + "StatusField").html(status);

      var btnClass = this.getButtonColorClass();
      // Strip all existing classes, then add the new one
      $("#" + this.id + "MainButton").removeClass("btn-primary btn-warning btn-danger btn-success btn-info").addClass(btnClass);
      $("#" + this.id + "DropdownButton").removeClass("btn-primary btn-warning btn-danger btn-success btn-info").addClass(btnClass);
    }

    getButtonColorClass() {

      // Get the Bootstrap class based on the current status

      switch (this.status) {
        case 'ACTIVE':
          return 'btn-primary';
        case 'ONLINE':
          return 'btn-success';
        case 'WAITING':
          return 'btn-warning';
        case 'UNKNOWN':
          return 'btn-warning';
        case 'STANDBY':
          return 'btn-info';
        case 'SYSTEM ON':
          return 'btn-info';
        default:
          return 'btn-danger';
      }
    }

    buildHTML() {

      // Function to build the HTML representation of this component
      // and add it to the row of the parent group

      var onCmdName = "";
      var offCmdName = "";
      var displayName = this.id;
      switch (this.type) {
        case "PROJECTOR":
          onCmdName = "Wake projector";
          offCmdName = "Sleep projector";
          break;
        case "WAKE_ON_LAN":
          onCmdName = "Wake component";
          offCmdName = "Sleep component";
          break;
        default:
          onCmdName = "Wake component";
          offCmdName = "Shutdown component";
      }

      var optionList = "";
      if (this.allowed_actions.includes("refresh")) {
        optionList += `<a class="dropdown-item handCursor" onclick="queueCommand('${this.id}', 'refresh_page')">Refresh component</a>`;
      }
      if (this.allowed_actions.includes("restart")) {
        optionList += `<a class="dropdown-item handCursor" onclick="queueCommand('${this.id}', 'restart')">Restart component</a>`;
      }
      if (this.allowed_actions.includes("shutdown") || this.allowed_actions.includes("power_off")) {
        optionList += `<a class="dropdown-item handCursor" onclick="queueCommand('${this.id}', 'shutdown')">${offCmdName}</a>`;
      }
      if (this.allowed_actions.includes("power_on")) {
        optionList += `<a class="dropdown-item handCursor" onclick="queueCommand('${this.id}', 'power_on')">${onCmdName}</a>`;
      }
      if (this.allowed_actions.includes("wake")) {
        optionList += `<a class="dropdown-item handCursor" onclick="queueCommand('${this.id}', 'wakeDisplay')">$Wake display</a>`;
      }
      if (this.allowed_actions.includes("sleep")) {
        optionList += `<a class="dropdown-item handCursor" onclick="queueCommand('${this.id}', 'sleepDisplay')">Sleep display</a>`;
      }
      if (optionList.length == 0) {
        optionList += `<span class="dropdown-item">No available actions</span>`;
      }

      // Change the amount of the Bootstrap grid being used depending on the
      // number of components in this group. Larger groups get more horizontal
      // space, so each component needs a smaller amount of grid.
      var classString;
      if (getExhibitComponentGroup(this.type).components.length > 7) {
        classString = 'col-12 col-sm-6 col-md-3 mt-1';
      } else {
        classString = 'col-12 col-sm-6 mt-1';
      }

      var html = `
        <div class='${classString}'>
          <div class="btn-group btn-block">
            <button type="button" class="btn ${this.getButtonColorClass()} btn-block" id="${this.id}MainButton" onclick="showExhibitComponentInfo('${this.id}')"><H5>${displayName}</H5><div id="${this.id}StatusField">${this.status}</div></button>
            <button type="button" id="${this.id}DropdownButton" class="btn ${this.getButtonColorClass()} dropdown-toggle dropdown-toggle-split"  data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
              <span class="sr-only">Toggle Dropdown</span>
            </button>
            <div class="dropdown-menu">
              ${optionList}
            </div>
          </div>
        </div>
      `;

      $('#'+this.type+'ComponentList').append(html);
    }
  }

  class ExhibitComponentGroup {

    constructor(type) {
      this.type = type;
      this.components = [];
      this.buildHTML();
    }

    addComponent(component) {
      this.components.push(component);
      this.sortComponentList();

      // When we reach 8 components, rebuild the interface so that this group
      // expands to double width
      if (this.components.length == 8) {
        rebuildComponentInterface();
      }

    }

    sortComponentList() {

      // Sort the component list by ID and then rebuild the HTML
      // representation in order

      if (this.components.length > 1) {
        // This line does the sorting
        this.components.sort((a,b) => (a.id > b.id) ? 1 : ((b.id > a.id) ? -1 : 0));

        document.getElementById(this.type + "ComponentList").innerHTML = "";
        for (var i=0; i<this.components.length; i++) {
          this.components[i].buildHTML();
        }
      }
    }

    removeComponent(id) {
      // Remove a component based on its id

      this.components = $.grep(this.components, function(el, idx) {return el.id == id;}, true);

      // If the group now has seven components, make sure we're using the small
      // size rendering now by rebuilding the interface
      if (this.components.length == 7) {
        rebuildComponentInterface();
      }
    }

    buildHTML() {

      // Function to build the HTML representation of this group
      // and add it to the componentGroupsRow

      var onCmdName = "";
      var offCmdName = "";
      if (this.type == "PROJECTOR") {
        onCmdName = "Wake all projectors";
        offCmdName = "Sleep all projectors";
      } else {
        onCmdName = "Wake all displays";
        offCmdName = "Sleep all displays";
      }

      // Allow groups with lots of components to display with double width
      var classString;
      if(this.components.length > 7) {
        classString = 'col-12 col-xl-8 mt-4';
      } else {
        classString = 'col-md-6 col-lg-5 col-xl-4 mt-4';
      }

      var html = `
        <div class= "${classString}">
          <div class="btn-group btn-block">
            <button type="button" class="btn btn-secondary btn-block btn-lg">${this.type}</button>
            <button type="button" class="btn btn-secondary dropdown-toggle dropdown-toggle-split" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
              <span class="sr-only">Toggle Dropdown</span>
            </button>
            <div class="dropdown-menu">
              <a class="dropdown-item handCursor" onclick="sendGroupCommand('${this.type}', 'wakeDisplay')">${onCmdName}</a>
              <a class="dropdown-item handCursor" onclick="sendGroupCommand('${this.type}', 'sleepDisplay')">${offCmdName}</a>
            </div>
          </div>
          <div class="row" id='${this.type}ComponentList'>
          </div>
        </div>
      `;

      $('#componentGroupsRow').append(html);
    }
  }

  function showExhibitComponentInfo(id) {

    // This sets up the componentInfoModal with the info from the selected
    // component and shows it on the screen.

    if (id == "") {
      id = $("#componentInfoModalTitle").html();
    }

    var obj = getExhibitComponent(id);

    if (obj.type == "PROJECTOR") {

      // First, reset all the cell shadings
      $("#projectorInfoLampState").parent().removeClass();
      $("#projectorInfoFanState").parent().removeClass();
      $("#projectorInfoFilterState").parent().removeClass();
      $("#projectorInfoCoverState").parent().removeClass();
      $("#projectorInfoOtherState").parent().removeClass();
      $("#projectorInfoTempState").parent().removeClass();

      // Set the title to the ID
      $("#projectorInfoModalTitle").html(id);
      $("#projectorInfoModalIPAddress").html(obj.ip);
      if (obj.description == "") {
        $("#projectorInfoModalDescription").hide();
      } else {
        $("#projectorInfoModalDescription").html(obj.description);
        $("#projectorInfoModalDescription").show();
      }

      // Then, go through and populate all the cells with as much information
      // as we have. Shade cells red if an error is reported.
      if ("power_state" in obj.state && obj.state.power_state != "") {
        $("#projectorInfoPowerState").html(obj.state.power_state);
      } else {
        $("#projectorInfoPowerState").html("-");
      }
      if (("error_status" in obj.state) && (obj.state.error_status.constructor == Object)) {
        if ("lamp" in obj.state.error_status) {
          // Populate cell
          $("#projectorInfoLampState").html(obj.state.error_status.lamp);
          // Shade if error
          if (obj.state.error_status.lamp == "error") {
            $("#projectorInfoLampState").parent().addClass("table-danger");
          }
        } else {
          $("#projectorInfoLampState").html("-");
        }
        if ("fan" in obj.state.error_status) {
          // Populate cell
          $("#projectorInfoFanState").html(obj.state.error_status.fan);
          // Shade if error
          if (obj.state.error_status.fan == "error") {
            $("#projectorInfoFanState").parent().addClass("table-danger");
          }
        } else {
          $("#projectorInfoFanState").html("-");
        }
        if ("filter" in obj.state.error_status) {
          // Populate cell
          $("#projectorInfoFilterState").html(obj.state.error_status.filter);
          // Shade if error
          if (obj.state.error_status.filter == "error") {
            $("#projectorInfoFilterState").parent().addClass("table-danger");
          }
        } else {
          $("#projectorInfoFilterState").html("-");
        }
        if ("cover" in obj.state.error_status) {
          // Populate cell
          $("#projectorInfoCoverState").html(obj.state.error_status.cover);
          // Shade if error
          if (obj.state.error_status.cover == "error") {
            $("#projectorInfoCoverState").parent().addClass("table-danger");
          }
        } else {
          $("#projectorInfoCoverState").html("-");
        }
        if ("other" in obj.state.error_status) {
          // Populate cell
          $("#projectorInfoOtherState").html(obj.state.error_status.other);
          // Shade if error
          if (obj.state.error_status.other == "error") {
            $("#projectorInfoOtherState").parent().addClass("table-danger");
          }
        } else {
          $("#projectorInfoOtherState").html("-");
        }
        if ("temperature" in obj.state.error_status) {
          // Populate cell
          $("#projectorInfoTempState").html(obj.state.error_status.temperature);
          // Shade if error
          if (obj.state.error_status == "error") {
            $("#projectorInfoTempState").parent().addClass("table-danger");
          }
        } else {
          $("#projectorInfoTempState").html("-");
        }
      } else {
        $("#projectorInfoLampState").html("-");
        $("#projectorInfoFanState").html("-");
        $("#projectorInfoFilterState").html("-");
        $("#projectorInfoCoverState").html("-");
        $("#projectorInfoOtherState").html("-");
        $("#projectorInfoTempState").html("-");
      }
      if ("model" in obj.state) {
        $("#projectorInfoModel").html(obj.state.model);
      } else {
        $("#projectorInfoModel").html("-");
      }

      if ("lamp_status" in obj.state && obj.state.lamp_status != "") {
        var lampList = obj.state.lamp_status;
        var lamp_html = "";
        for (var i=0; i<lampList.length; i++) {
          lamp = lampList[i];
          var statusStr = "";
          if (lamp[1] == false) {
            statusStr = "(off)";
          } else if (lamp[1] == true) {
            statusStr = "(on)";
          } else {
            statusStr = "";
          }
          lamp_html += `Lamp ${i+1} ${statusStr}: ${lamp[0]} hours<br>`;
        }
      } else {
        lamp_html = "-";
      }
      $("#projectorInfoLampHours").html(lamp_html);

      // Make the modal visible
      $("#projectorInfoModal").modal("show");

    } else { // This is a normal ExhibitComponent

      $("#componentInfoModalTitle").html(id);
      $("#componentInfoModalIPAddress").html(obj.ip);
      if (obj.description == "") {
        $("#componentInfoModalDescription").hide();
      } else {
        $("#componentInfoModalDescription").html(obj.description);
        $("#componentInfoModalDescription").show();
      }
      $("#componentAvailableContentList").empty();
      $("#contentUploadSubmitButton").prop("disabled", false);
      $("#contentUploadSubmitButton").html("Upload");
      $("#componentContentUploadfilename").html("Choose file");
      $("#componentContentUpload").val(null);
      $("#contentUploadSubmitButton").hide();
      $("#contentUploadEqualSignWarning").hide();
      $("#uploadOverwriteWarning").hide();
      $("#contentUploadProgressBarContainer").hide();
      $("#contentUploadSystemStatsView").hide();
      $("#componentInfoConnectingNotice").show();
      $("#componentInfoConnectionStatusFailed").hide();
      $("#componentInfoConnectionStatusInPrograss").show();
      $("#componentSaveConfirmationButton").hide();
      $("#componentAvailableContentRow").hide();
      $("#componentcontentUploadInterface").hide();

      var showFailureMessage = function() {
        $("#componentInfoConnectionStatusFailed").show();
        $("#componentInfoConnectionStatusInPrograss").hide();
      };

      var requestString = JSON.stringify({"action": "getAvailableContent"});

      var xhr = new XMLHttpRequest();
      xhr.open("POST", `http://${obj.ip}:${obj.helperPort}`, true);
      xhr.timeout = 10000; // 10 seconds
      xhr.ontimeout = showFailureMessage;
      xhr.onerror = showFailureMessage;
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.onreadystatechange = function () {
        if (this.readyState != 4) return;

        if (this.status == 200) {

          // Good connection, so show the interface elements
          $("#componentAvailableContentRow").show();
          $("#componentcontentUploadInterface").show();
          $("#componentInfoConnectingNotice").hide();

          var availableContent = JSON.parse(this.response);

          // If it is provided, show the system stats
          if ("system_stats" in availableContent) {
            var stats = availableContent.system_stats;

            // Disk
            $("#contentUploadDiskSpaceUsedBar").attr("ariaValueNow", 100 - stats.disk_pct_free);
            $("#contentUploadDiskSpaceUsedBar").width(String(100 - stats.disk_pct_free)+"%");
            $("#contentUploadDiskSpaceFreeBar").attr("ariaValueNow", stats.disk_pct_free);
            $("#contentUploadDiskSpaceFreeBar").width(String(stats.disk_pct_free)+"%");
            $("#contentUploadDiskSpaceFree").html(`Disk: ${String(Math.round(stats.disK_free_GB))} GB`);
            if (stats.disk_pct_free > 20) {
              $("#contentUploadDiskSpaceUsedBar").removeClass("bg-warning bg-danger").addClass("bg-success");
            } else if (stats.disk_pct_free > 10) {
              $("#contentUploadDiskSpaceUsedBar").removeClass("bg-success bg-danger").addClass("bg-warning");
            } else {
              $("#contentUploadDiskSpaceUsedBar").removeClass("bg-success bg-warning").addClass("bg-danger");
            }

            // CPU
            $("#contentUploadCPUUsedBar").attr("ariaValueNow", stats.cpu_load_pct);
            $("#contentUploadCPUUsedBar").width(String(stats.cpu_load_pct)+"%");
            $("#contentUploadCPUFreeBar").attr("ariaValueNow", 100 - stats.cpu_load_pct);
            $("#contentUploadCPUFreeBar").width(String(100 - stats.cpu_load_pct)+"%");
            $("#contentUploadCPUUsed").html(`CPU: ${String(Math.round(stats.cpu_load_pct))}%`);
            if (stats.cpu_load_pct < 80) {
              $("#contentUploadCPUUsedBar").removeClass("bg-warning bg-danger").addClass("bg-success");
            } else if (stats.cpu_load_pct < 90) {
              $("#contentUploadCPUUsedBar").removeClass("bg-success bg-danger").addClass("bg-warning");
            } else {
              $("#contentUploadCPUUsedBar").removeClass("bg-success bg-warning").addClass("bg-danger");
            }

            // RAM
            $("#contentUploadRAMUsedBar").attr("ariaValueNow", stats.ram_used_pct);
            $("#contentUploadRAMUsedBar").width(String(stats.ram_used_pct)+"%");
            $("#contentUploadRAMFreeBar").attr("ariaValueNow", 100 - stats.ram_used_pct);
            $("#contentUploadRAMFreeBar").width(String(100 - stats.ram_used_pct)+"%");
            $("#contentUploadRAMUsed").html(`RAM: ${String(Math.round(stats.ram_used_pct))}%`);
            if (stats.ram_used_pct < 80) {
              $("#contentUploadRAMUsedBar").removeClass("bg-warning bg-danger").addClass("bg-success");
            } else if (stats.ram_used_pct < 90) {
              $("#contentUploadRAMUsedBar").removeClass("bg-success bg-danger").addClass("bg-warning");
            } else {
              $("#contentUploadCPUUsedBar").removeClass("bg-success bg-warning").addClass("bg-danger");
            }

            $("#contentUploadSystemStatsView").show();
          } else {
            $("#contentUploadSystemStatsView").hide();
          }

          var populateContent = function(key, id, div) {

            // Get filenames listed under key in availableContent and add
            // the resulting buttons to the div given by div

            var activeContent = availableContent.active_content;
            var contentList = availableContent[key].sort(function(a,b) {return a.localeCompare(b);});
            var active;

            for (var i=0; i<contentList.length; i++) {
              if (activeContent.includes(contentList[i])) {
                active = "btn-primary";
              } else {
                active = "btn-secondary";
              }
              var html = `
              <div class="col-6 mt-1">
                <div class="btn-group w-100 h-100">
                  <button type="button" id="${contentList[i].split('.').join("").split(")").join("").split("(").join("").split(/[\\\/]/).join("")}Button" class="btn componentContentButton ${active}">${contentList[i]}</button>
                  <button type="button" id="${contentList[i].split('.').join("").split(")").join("").split("(").join("").split(/[\\\/]/).join("")}ButtonDropdown" class="btn dropdown-toggle dropdown-toggle-split componentContentDropdownButton ${active}" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    <span class="sr-only">Toggle Dropdown</span>
                  </button>
                  <div class="dropdown-menu">
                    <a class="dropdown-item disabled text-secondary">Rename</a>
                    <a class="dropdown-item disabled"></a>
                    <div class="dropdown-divider"></div>
                    <a class="dropdown-item text-danger" onclick="deleteRemoteFile('${id}', '${contentList[i]}')">Delete</a>
                  </div>
                </div>
              </div>
              `;
              $("#"+div).append(html);
            }
          };

          // Build buttons for each file in the current exhibit
          //populateContent('current_exhibit', id, "componentAvailableContentList-thisExhibit")

          // Build buttons for each file in all exhibits
          populateContent('all_exhibits', id, "componentAvailableContentList");

          // Attach an event handler to change the button's color when clicked
          $(".componentContentButton").on("click", function(e){
            var id = $(this).attr("id");
            // $('.componentContentButton').not($(this)).removeClass("btn-primary").addClass("btn-secondary");
            $(this).toggleClass("btn-primary").toggleClass("btn-secondary");

            // $('.componentContentDropdownButton').not($("#"+id+"Dropdown")).removeClass("btn-primary").addClass("btn-secondary");
            $("#"+id+"Dropdown").toggleClass("btn-secondary").toggleClass("btn-primary");

            if ($(".componentContentButton.btn-primary").length == 0) {
              $("#componentSaveConfirmationButton").hide(); // Can't save a state with no selected content.
            } else {
              $("#componentSaveConfirmationButton").show();
            }
          });
        }
      };
      xhr.send(requestString);

      // Make the modal visible
      $("#componentInfoModal").modal("show");
    }

  }

  function deleteRemoteFile(id, file, warn=true) {

    // If called with warn=True, show a modal asking to delete the file.
    // Otherwise, send the command to delete.

    var model = $("#fileDeleteModal");

    if (warn == true) {
      $("#fileDeleteModalText").html(`Delete ${file} from ${id}?`);
      // Remove any previous event handler and then add one to actually do the deletion.
      $("#fileDeleteConfirmationButton").show();
      $("#fileDeleteConfirmationButton").off();
      $("#fileDeleteConfirmationButton").on("click", function(){
        deleteRemoteFile(id, file, warn=false);
      });
      model.modal("show");
    } else {

      $("#fileDeleteModalText").html(`Deleting ${file}...`);
      $("#fileDeleteConfirmationButton").hide();

      var file_split = file.split(/[\\\/]/); // regex to split on forward and back slashes
      var exhibit;
      var file_to_delete;
      if (file_split.length > 1) {
        // our file is of form "exhibit/file"
        exhibit = file_split[0];
        file_to_delete = file_split[1];
      } else {
        exhibit = currentExhibit.split(".")[0];
        file_to_delete = file;
      }
      var obj = getExhibitComponent(id);
      var requestString = JSON.stringify({"action": "deleteFile",
                                          "file": file_to_delete,
                                          "fromExhibit": exhibit});

      var xhr = new XMLHttpRequest();
      xhr.timeout = 2000;
      xhr.open("POST", `http://${obj.ip}:${obj.helperPort}`, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(requestString);
      xhr.onreadystatechange = function () {
        if (this.readyState != 4) return;
        if (this.status == 200) {

          var response = JSON.parse(this.responseText);

          if ("success" in response) {
            if (response.success == true) {
              model.modal("hide");
              showExhibitComponentInfo(id);
            }
          }
        }
      };
    }

  }

  function onUploadContentChange() {

    // When we select a file for uploading, check against the existing files
    // (as defined by their buttons) and warn if we will overwrite. Also
    // check if the filename contains an =, which is not allowed

    $("#contentUploadSubmitButton").show();
    // Show the upload button (we may hide it later)
    var fileInput = $("#componentContentUpload")[0];
    // Check for filename collision
    var currentFiles = $(".componentContentButton").map(function(){return $(this).html();}).toArray();
    $("#componentContentUploadfilename").html("File: " + fileInput.files[0].name);
    if(currentFiles.includes(fileInput.files[0].name)) {
      $("#uploadOverwriteWarning").show();
    } else {
      $("#uploadOverwriteWarning").hide();
    }
    // Check for = in filename
    if (fileInput.files[0].name.includes("=")) {
      $("#contentUploadEqualSignWarning").show();
      $("#contentUploadSubmitButton").hide();
    } else {
      $("#contentUploadEqualSignWarning").hide();
    }
  }

  function uploadComponentContentFile() {

    var fileInput = $("#componentContentUpload")[0];
    if (fileInput.files[0] != null){
      var id = $("#componentInfoModalTitle").html().trim();

      var component = getExhibitComponent(id);

      $("#contentUploadSubmitButton").prop("disabled", true);
      $("#contentUploadSubmitButton").html("Working...");

      var file = fileInput.files[0];
      var formData = new FormData();
      formData.append("exhibit", getCurrentExhibitName());
      formData.append("filename", file.name);
      formData.append("mimetype", file.type);
      formData.append("file", file);

      var xhr = new XMLHttpRequest();
      xhr.open("POST", `http://${component.ip}:${component.helperPort}`, true);
      xhr.onreadystatechange = function () {
        if (this.readyState != 4) return;
        if (this.status == 200) {
          var response = JSON.parse(this.responseText);

          if ("success" in response) {
            queueCommand(id, 'reloadDefaults');
            showExhibitComponentInfo("");
          }
        }
      };

      xhr.upload.addEventListener("progress", function(evt) {
        if (evt.lengthComputable) {
          var percentComplete = evt.loaded / evt.total;
          percentComplete = parseInt(percentComplete * 100);
          $("#contentUploadProgressBar").width(String(percentComplete) + "%");
          if (percentComplete > 0) {
            $("#contentUploadProgressBarContainer").show();
          }
          else if (percentComplete == 100) {
            $("#contentUploadProgressBarContainer").hide();
          }
        }
      }, false);

      xhr.send(formData);
    }

  }

  function submitComponentContentChange() {

    // Collect the new information from the componentInfoModal and pass it
    // back to the server to be changed.

    var id = $("#componentInfoModalTitle").html().trim();
    var selectedButtons = $('.componentContentButton.btn-primary');
    var component = getExhibitComponent(id);
    var contentList = [];
    for (var i=0; i<selectedButtons.length; i++) {
      content = selectedButtons[i].innerHTML.trim();
      contentList.push(content);
    }
    sendComponentContentChangeRequest(id, contentList);
    askForUpdate();

    // Hide the modal
    $("#componentInfoModal").modal("hide");
  }

  function sendComponentContentChangeRequest(id, content) {

    // Send a request to the server to initiate a content change

    requestString = JSON.stringify({
      "class": "webpage",
      "action": "setComponentContent",
      "id": id,
      "content": content
    });
    var xhr = new XMLHttpRequest();
    xhr.timeout = 2000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(requestString);
  }

  function getExhibitComponent(id) {

    // Function to search the exhibitComponents list for a given id

    var result = exhibitComponents.find(obj => {
      return obj.id === id;
    });

    return result;
  }

  function getExhibitComponentGroup(type) {

    // Function to search the exhibitComponents list for a given id

    var result = componentGroups.find(obj => {
      return obj.type === type;
    });
    return result;
  }

  function updateComponentFromServer(component) {

    // Read the dictionary of component information from the control server
    // and use it to set up the component

    obj = getExhibitComponent(component.id);
    if (obj != null) {
      // Update the object with the latest info from the server
      obj.setStatus(component.status);
      if ("content" in component) {
        obj.content = component.content;
      }
      if ("ip_address" in component) {
        obj.ip = component.ip_address;
      }
      if ("helperPort" in component) {
        obj.helperPort = component.helperPort;
      }
      if ("allowed_actions" in component) {
        obj.allowed_actions = component.allowed_actions;
      }
      if ("description" in component) {
        obj.description = component.description;
      }
      if ("error" in component) {
        errorDict[obj.id + ": "] = component.error;
        rebuildErrorList();
      } else if (obj.id + ": " in errorDict) {
        delete errorDict[obj.id + ": "];
        rebuildErrorList();
      }
    } else {

      // First, make sure the group matching this type exists
      var group = getExhibitComponentGroup(component.type);
      if (group == null) {
        group = new ExhibitComponentGroup(component.type);
        componentGroups.push(group);
      }

      // Then create a new component
      var newComponent = new ExhibitComponent(component.id, component.type);
      newComponent.setStatus(component.status);
      if ("allowed_actions" in component) {
        newComponent.allowed_actions = component.allowed_actions;
      }
      newComponent.buildHTML();
      exhibitComponents.push(newComponent);

      // Add the component to the right group
      group.addComponent(newComponent);

      // Finally, call this function again to populate the information
      updateComponentFromServer(component);
    }
  }

  function setCurrentExhibitName(name) {
    currentExhibit = name;
    document.getElementById("exhibitNameField").innerHTML = name;
    updateAvailableExhibits([name]);
    // Don't change the value of the exhibit selector if we're currently
    // looking at the change confirmation modal, as this will result in
    // submitting the incorrect value
    if ($('#changeExhibitModal').hasClass('show') == false) {
      $("#exhibitSelect").val(name);
    }
  }

  function getCurrentExhibitName() {
    return(document.getElementById("exhibitNameField").innerHTML);
  }

  function updateAvailableExhibits(exhibitList) {

    for (var i=0; i<exhibitList.length; i++) {
      // Check if exhibit already exists as an option. If not, add it
      if ($(`#exhibitSelect option[value='${exhibitList[i]}']`).length == 0) {
        $("#exhibitSelect").append(new Option(exhibitList[i], exhibitList[i]));
      }
    }
  }

  function changeExhibit(warningShown) {

    // Send a command to the control server to change the current exhibit

    if (warningShown == false) {
      $("#changeExhibitModal").modal("show");
    }
    else {
      $("#changeExhibitModal").modal("hide");

      var requestDict = {"class": "webpage",
                         "action": "setExhibit",
                         "name": $("#exhibitSelect").val()};
      var xhr = new XMLHttpRequest();
      xhr.timeout = 2000;
      xhr.open("POST", serverIP, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify(requestDict));

      askForUpdate();
    }
  }

  function reloadConfiguration() {

    // This function will send a message to the server asking it to reload
    // the current exhibit configuration file and update all the components

    //requestString = "class=webpage&action=reloadConfiguration";
    var requestDict = {"class": "webpage",
                       "action": "reloadConfiguration"};

    var xhr = new XMLHttpRequest();
    xhr.timeout = 2000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
      if (this.readyState != 4) return;

      if (this.status == 200) {
        var response = JSON.parse(this.responseText);

        if ("result" in response) {
          if (response.result == "success") {
            $("#reloadConfigurationButton").html("Success!");
            setTimeout(function() { $("#reloadConfigurationButton").html("Reload Config"); }, 2000);
          }
        }
      }
    };
    xhr.send(JSON.stringify(requestDict));
  }

  function queueCommand(id, cmd) {

    // Function to send a command to the control server that will then
    // be sent to the component the next time it pings the server

    var obj = getExhibitComponent(id);
    if (["shutdown", "restart"].includes(cmd)) {
      // We send these commands directly to the helper
      var requestDict = {"action": cmd};

      var xhr = new XMLHttpRequest();
      xhr.timeout = 2000;
      console.log(`http://${obj.ip}:${obj.helperPort}`);
      xhr.open("POST", `http://${obj.ip}:${obj.helperPort}`, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify(requestDict));

    } else {
      // We send these commands to the server to pass to the component itself
      var cmdType = "";
      switch (obj.type) {
        case "PROJECTOR":
          cmdType = "queueProjectorCommand";
          break;
        case "WAKE_ON_LAN":
          cmdType = "queueWOLCommand";
          break;
        default:
          cmdType = "queueCommand";
      }

      var requestDict = {"class": "webpage",
                         "id": id,
                         "command": cmd,
                         "action": cmdType};

      var xhr = new XMLHttpRequest();
      xhr.timeout = 2000;
      xhr.open("POST", serverIP, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify(requestDict));
    }

  }

  function sendGroupCommand(group, cmd) {

    // Iterate through the components in the given group and queue the command
    // for each

    group = getExhibitComponentGroup(group);

    for (var i=0; i<group.components.length; i++) {
      queueCommand(group.components[i].id, cmd);
    }
  }

  function deleteSchedule(name) {

    // Send a message to the control server asking to delete the schedule
    // file with the given name. The name should not include ".ini"

    var requestDict = {"class": "webpage",
                       "action": "deleteSchedule",
                       "name": name};

    requestString = JSON.stringify(requestDict);

    var xhr = new XMLHttpRequest();
    xhr.timeout = 3000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.ontimeout = function() {
    };
    xhr.onreadystatechange = function () {

      if (this.readyState != 4) return;

      if (this.status == 200) {
        if (this.responseText != "") {
          var update = JSON.parse(this.responseText);
          if (update["class"] == "schedule") {
            populateSchedule(update);
          }
        }
      }
    };
    xhr.send(requestString);

  }

  function scheduleConvertToDateSpecific(date, dayName) {

    // Send a message to the control server, asking to create a date-specific
    // schedule out of the given day name

    var requestDict = {"class": "webpage",
                       "action": "convertSchedule",
                       "date": date,
                       "from": dayName};

    requestString = JSON.stringify(requestDict);

    var xhr = new XMLHttpRequest();
    xhr.timeout = 3000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.ontimeout = function() {
    };
    xhr.onreadystatechange = function () {

      if (this.readyState != 4) return;

      if (this.status == 200) {
        if (this.responseText != "") {
          var update = JSON.parse(this.responseText);
          if (update["class"] == "schedule") {
            populateSchedule(update);
          }
        }
      }
    };
    xhr.send(requestString);
  }

  function populateSchedule(schedule) {

    document.getElementById('scheduleContainer').innerHTML = "";
    $("#dateSpecificScheduleAlert").hide();

    // Record the timestamp when this schedule was generated
    scheduleUpdateTime = schedule.updateTime;
    var sched = schedule.schedule;

    sched.forEach((day) => {
      // Apply a background color to date-specific schedules so that we
      // know that they are special
      var scheduleClass;
      var addItemText;
      var convertState;
      var deleteState;
      var scheduleName;
      if (day.source == 'date-specific') {
        scheduleClass = 'schedule-date-specific';
        addItemText = 'Add date-specific action';
        $("#dateSpecificScheduleAlert").show();
        convertState = "none";
        deleteState = "block";
        scheduleName = day.date;
      } else {
        scheduleClass = '';
        addItemText = 'Add recurring action';
        convertState = "block";
        deleteState = "none";
        scheduleName = day.dayName.toLowerCase();
      }
        var html = `<div class="col-12 col-sm-6 col-lg-4 mt-3 pt-3 pb-3 ${scheduleClass}">`;
        html += `
                        <div class="row">
                          <div class="col-6 col-sm-12 col-md-6">
                            <span style="font-size: 35px;">${day.dayName}</span>
                          </div>
                          <div class="col-6 col-sm-12 col-md-6 my-auto" style="text-align: right;">
                            <strong>${day.date}</strong>
                          </div>
                          <div class="col-12 col-lg-6 mt-2">
                              <button class="btn btn-primary w-100" type="button" onclick="scheduleConfigureEditModal('${scheduleName}', '${day.source}')">${addItemText}</button>
                          </div>
                          <div class="col-12 col-lg-6 mt-2" style="display: ${convertState};">
                              <button class="btn btn-warning w-100" type="button" onclick="scheduleConvertToDateSpecific('${day.date}', '${day.dayName}')">Convert to date-specific schedule</button>
                          </div>
                          <div class="col-12 col-lg-6 mt-2" style="display: ${deleteState};">
                              <button class="btn btn-danger w-100" type="button" onclick="deleteSchedule('${day.date}')">Delete date-specific schedule</button>
                          </div>
                        </div>
                      `;

        // Loop through the schedule elements and had a row for each
        day.schedule.forEach((item) => {

          var description = null;
          var action = null;
          if (item[2].length == 1) {
            action = (item[2])[0];
            target = null;
            if (action == "power_off") {
              description = "Power off";
            } else if (action == "power_on") {
              description = "Power on";
            }
          } else if (item[2].length == 2) {
            action = (item[2])[0];
            target = (item[2])[1];
            if (action == "set_exhibit") {
              description = `Set exhibit: ${target}`;
            }
          }

          if (description != null) {
            html += `
                        <div class="row mt-2">
                            <div class='col-4 mr-0 pr-0'>
                              <div class="rounded-left text-light bg-secondary w-100 h-100 justify-content-center d-flex py-1 pl-1"><div class="align-self-center justify-content-center">${item[1]}</div></div>
                            </div>
                            <div class="col-5 mx-0 px-0">
                              <div class="text-light bg-secondary w-100 h-100 justify-content-center d-flex py-1 pr-1"><div class="align-self-center justify-content-center text-wrap"><center>${description}</center></div></div>
                            </div>
                            <div class="col-3 ml-0 pl-0">
                              <button type="button" class="btn-info w-100 h-100 rounded-right" style="border-style: solid; border: 0px;" onclick="scheduleConfigureEditModal('${scheduleName}', '${day.source}', false, '${item[1]}', '${action}', '${target}')">Edit</button>
                            </div>
                        </div>
            `;
          }

        });
        html += "</div>";
        $("#scheduleContainer").append(html);
    });

    var nextEvent = schedule.nextEvent;
    var html = '';
    if (nextEvent.action.length == 1) {
      var action = (nextEvent.action)[0];
      if (action == "reload_schedule") {
        html = "No more actions today";
      } else if (action == "power_on") {
        html = `Power on at ${nextEvent.time}`;
      } else if (action == "power_off") {
        html = `Power off at ${nextEvent.time}`;
      }
    } else if (nextEvent.action.length == 2) {
      var action = nextEvent.action[0];
      var target = nextEvent.action[1];
      if (action == 'set_exhibit') {
        html = `Set exhibit to ${target} at ${nextEvent.time}`;
      }
    }
    $("#Schedule_next_event").html(html);
  }

  function toggleScheduleActionTargetSelector() {

    // Helper function to show/hide the select element for picking the target
    // of an action when appropriate

    if ($("#scheduleActionSelector").val() == "set_exhibit") {
      $("#scheduleTargetSelector").show();
      $("#scheduleTargetSelectorLabel").show();
    } else {
      $("#scheduleTargetSelector").hide();
      $("#scheduleTargetSelectorLabel").hide();
      $("#scheduleTargetSelector").val(null);
    }
  }

  function scheduleConfigureEditModal(scheduleName,
                                      type,
                                      isAddition=true,
                                      currentTime=null,
                                      currentAction=null,
                                      currentTarget=null) {

    // Function to set up and then show the modal that enables editing a
    // scheduled action or adding a new one

    // Hide elements that aren't always visible
    $("#scheduleTargetSelector").hide();
    $("#scheduleTargetSelectorLabel").hide();
    $("#scheduleEditErrorAlert").hide();

    // Tag the modal with a bunch of data that we can read if needed when
    // submitting the change
    $("#scheduleEditModal").data("scheduleName", scheduleName);
    $("#scheduleEditModal").data("isAddition", isAddition);
    $("#scheduleEditModal").data("currentTime", currentTime);
    $("#scheduleEditModal").data("currentAction", currentAction);
    $("#scheduleEditModal").data("currentTarget", currentTarget);

    // Set the modal title
    if (isAddition) {
      $("#scheduleEditModalTitle").html("Add action");
    } else {
      $("#scheduleEditModalTitle").html("Edit action");
    }

    // Set the scope notice so that users know what their change will affect
    switch (type) {
      case "date-specific":
        $("#scheduleEditScopeAlert").html(`This change will only affect ${scheduleName}`);
        break;
      case "day-specific":
        $("#scheduleEditScopeAlert").html(`This change will affect all ${scheduleName.charAt(0).toUpperCase() + scheduleName.slice(1)}s`);
        break;
      default:
        break;
    }

    // Fill the target selector with a list of available exhiits
    $("#scheduleTargetSelector").empty();
    var availableExhibits = $.makeArray($("#exhibitSelect option"));
    availableExhibits.forEach((item) => {
      $("#scheduleTargetSelector").append(new Option(item.value, item.value));
    });


    // If we're editing an existing action, pre-fill the current options
    if (isAddition == false) {
      $("#scheduleActionTimeInput").val(currentTime);
      $("#scheduleActionSelector").val(currentAction);
      $("#scheduleTargetSelector").val(currentTarget);

      if (currentAction == 'set_exhibit') {
        $("#scheduleTargetSelector").show();
        $("#scheduleTargetSelectorLabel").show();
      }
    } else {
      $("#scheduleActionTimeInput").val(null);
      $("#scheduleActionSelector").val(null);
      $("#scheduleTargetSelector").val(null);
    }

    $("#scheduleEditModal").modal("show");
  }

  function sendScheduleUpdateFromModal() {

    // Gather necessary info from the schedule editing modal and send a
    // message to the control server asking to add the given action

    var scheduleName = $("#scheduleEditModal").data("scheduleName");
    var time = $("#scheduleActionTimeInput").val().trim();
    var action = $("#scheduleActionSelector").val();
    var target = $("#scheduleTargetSelector").val();
    var isAddition = $("#scheduleEditModal").data("isAddition");

    if (time == "" || time == null) {
      $("#scheduleEditErrorAlert").html("You must specifiy a time for the action").show();
      return;
    } else if (action == null) {
      $("#scheduleEditErrorAlert").html("You must specifiy an action").show();
      return;
    } else if (action == "set_exhibit" && target == null) {
      $("#scheduleEditErrorAlert").html("You must specifiy an exhibit to set").show();
      return;
    }

    console.log("Update action:", scheduleName, isAddition, time, action, target);

    var requestDict;
    if (isAddition) {
      requestDict = {"class": "webpage",
                         "action": "updateSchedule",
                         "name": scheduleName,
                         "timeToSet": time,
                         "actionToSet": action,
                         "targetToSet": target,
                         "isAddition": true};
    } else {
      requestDict = {"class": "webpage",
                     "action": "updateSchedule",
                     "name": scheduleName,
                     "timeToSet": time,
                     "actionToSet": action,
                     "targetToSet": target,
                     "isAddition": false,
                     "timeToReplace": $("#scheduleEditModal").data("currentTime")};
    }

    requestString = JSON.stringify(requestDict);

    var xhr = new XMLHttpRequest();
    xhr.timeout = 3000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.ontimeout = function() {
    };
    xhr.onreadystatechange = function () {

      if (this.readyState != 4) return;

      if (this.status == 200) {
        if (this.responseText != "") {
          var update = JSON.parse(this.responseText);
          if ("success" in update) {
            if (update.success == true) {
              if (update.class == "schedule") {
                $("#scheduleEditModal").modal("hide");
                populateSchedule(update);
              }
            } else {
              $("#scheduleEditErrorAlert").html(update.reason).show();
              return;
            }
          }
        }
      }
    };
    xhr.send(requestString);
  }

  function scheduleDeleteActionFromModal() {

    // Gather necessary info from the schedule editing modal and send a
    // message to the control server asking to delete the given action

    var scheduleName = $("#scheduleEditModal").data("scheduleName");
    var time = $("#scheduleActionTimeInput").val();

    console.log("Delete:", scheduleName, time);

    var requestDict = {"class": "webpage",
                       "action": "deleteScheduleAction",
                       "from": scheduleName,
                       "time": time};

    requestString = JSON.stringify(requestDict);

    var xhr = new XMLHttpRequest();
    xhr.timeout = 3000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.ontimeout = function() {
    };
    xhr.onreadystatechange = function () {

      if (this.readyState != 4) return;

      if (this.status == 200) {
        if (this.responseText != "") {
          var update = JSON.parse(this.responseText);
          if (update["class"] == "schedule") {
            $("#scheduleEditModal").modal("hide");
            populateSchedule(update);
          }
        }
      }
    };
    xhr.send(requestString);
  }

  function rebuildErrorList() {

    // Function to use the errorDict to build a set of buttons indicating
    // that there is a problem with a component.

    // Clear the existing buttons
    $("#errorDisplayRow").empty();

    Object.keys(errorDict).forEach((item, i) => {
      var html = `
        <div class="col-auto mt-3">
          <button class='btn btn-danger btn-block'>${item + " " + errorDict[item]}</btn>
        </div>
      `;
      $("#errorDisplayRow").append(html);
    });

  }

  function askForScheduleRefresh() {

    // Send a message to the control server asking it to reload the schedule
    // from disk

    $("#refreshScheduleButton").html("Refreshing...");

    var requestDict = {"class": "webpage",
                       "action": "refreshSchedule"};

    requestString = JSON.stringify(requestDict);

    var xhr = new XMLHttpRequest();
    xhr.timeout = 3000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.ontimeout = function() {
      $("#refreshScheduleButton").html("Timed out!");
      var temp = function() {
        $("#refreshScheduleButton").html("Refresh schedule");
      };
      setTimeout(temp, 2000);
    };
    xhr.onreadystatechange = function () {

      if (this.readyState != 4) return;

      if (this.status == 200) {
        if (this.responseText != "") {
          var update = JSON.parse(this.responseText);
          if (update["class"] == "schedule") {
            populateSchedule(update);
          }
          $("#refreshScheduleButton").html("Success!");
          var temp = function() {
            $("#refreshScheduleButton").html("Refresh schedule");
          };
          setTimeout(temp, 2000);
        }
      }
    };
    xhr.send(requestString);
  }

  function askForUpdate() {

    // Send a message to the control server asking for the latest component
    // updates

    requestDict = {"class": "webpage",
                   "action": "fetchUpdate"};

    var xhr = new XMLHttpRequest();
    xhr.timeout = 2000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.ontimeout = function() {console.log("Website update timed out");};
    xhr.onreadystatechange = function () {
      if (this.readyState != 4) return;

      if (this.status == 200) {
        if (this.responseText != "") {
          var update = JSON.parse(this.responseText);
          var n_comps = 0;
          var n_online = 0;
          for (var i=0; i<update.length; i++) {
            var component = update[String(i)];
            if ("class" in component) {
              if (component["class"] == "exhibitComponent") {
                n_comps += 1;
                if ((component.status == "ONLINE") || (component.status == "STANDBY") || (component.status == "SYSTEM ON")) {
                  n_online += 1;
                }
                updateComponentFromServer(component);
              } else if (component.class == "gallery") {
                setCurrentExhibitName(component.currentExhibit);
                updateAvailableExhibits(component.availableExhibits);
                if ("galleryName" in component) {
                  $("#galleryNameField").html(component.galleryName);
                  document.title = component.galleryName;
                }
              } else if (component.class == "schedule") {
                if (scheduleUpdateTime != component.updateTime) {
                  populateSchedule(component);
                }
              }
            }
          }
          // Set the favicon to reflect the aggregate status
          if (n_online == n_comps) {
            $("link[rel='icon']").attr("href", "icon/green.ico");
          } else if (n_online == 0) {
            $("link[rel='icon']").attr("href", "icon/red.ico");
          } else {
            $("link[rel='icon']").attr("href", "icon/yellow.ico");
          }
        }
      }
    };
    xhr.send(JSON.stringify(requestDict));
  }

  function rebuildComponentInterface() {

    // Clear the componentGroupsRow and rebuild it

    document.getElementById('componentGroupsRow').innerHTML = "";
    for (var i=0; i<componentGroups.length; i++) {
      componentGroups[i].buildHTML();
    }
    for (var i=0; i<exhibitComponents.length; i++) {
      exhibitComponents[i].buildHTML();
    }
  }

  function populateHelpTab() {

    // Ask the server to send the latest README, convert the Markdown to
    // HTML, and add it to the Help tab.

    var requestDict = {"class": "webpage",
                       "action": "getHelpText"};

    requestString = JSON.stringify(requestDict);

    var xhr = new XMLHttpRequest();
    xhr.timeout = 2000;
    xhr.open("POST", serverIP, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {

      if (this.readyState != 4) return;

      if (this.status == 200) {
        if (this.responseText != "") {
          var formatted_text = markdownConverter.makeHtml(this.responseText);
          $("#helpTextDiv").html(formatted_text);
        } else {
          $("#helpTextDiv").html("Help text not available.");
        }
      }
    };
    xhr.send(requestString);
  }

  function parseQueryString() {

    // Read the query string to determine what options to set

    var queryString = decodeURIComponent(window.location.search);

    var searchParams = new URLSearchParams(queryString);

    if (searchParams.has("hideSchedule")) {
      $("#nav-schedule-tab").hide();
    }
    if (searchParams.has("hideSettings")) {
      $("#nav-settings-tab").hide();
    }
    if (searchParams.has("hideHelp")) {
      $("#nav-help-tab").hide();
    }
  }