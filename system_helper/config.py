# This file defined configuration variables that can be shared across various
# modules that use the helper.py module

clipList = {} # Dict of currently-loaded content. E.g., for the media player
commandList = [] # List of queued commands to send to the client
defaults_dict = {} # Dictionary holding default parameters from defaults.ini
defaults_object = None # configparser object holding the parsed input from defaults.ini
dictionary_object = None # Optionally-loaded configparser object from dictionary.ini
missingContentWarningList = [] # Holds a list of warning about missing content
nextEvent = None # A tuple with the next event to occur and the time is happens
schedule = [] # List of upcoming actions and their datetimes
