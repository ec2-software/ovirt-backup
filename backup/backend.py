import os
import re
import logging
import subprocess

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

    def cmd_log(self, args, allow_fail=True):
        res = subprocess.run(args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        if res.returncode:
            logging.info("Command %s failed with status code %s",
                            " ".join(res.args), res.returncode)
        else:
            logging.info("Command %s succeded", " ".join(res.args))
        if res.stdout:
            logging.info(res.stdout.decode("utf-8"))