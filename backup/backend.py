import os
import re

class Backend:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.parent = None

    def backup(self):
        raise NotImplementedError()

    @property
    def enabled_now(self):
        if not "enabled" in self.config:
            return False
        e = self.config["enabled"]
        if type(e) == bool:
            return e
        elif type(e) == str:
            raise NotImplementedError()
        else:
            return False
    
    @property
    def disk_device(self):
        listOfFiles = os.listdir('/dev')
        for entry in listOfFiles:
            if re.search(r"^vd[a-z]+$", entry):
                return "/dev/" + entry
        raise FileNotFoundError("Did not find a matching block device")