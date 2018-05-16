import os
import re
import logging
import subprocess
import calendar
from datetime import date

class Backend:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.parent = None

    def backup(self, vm_name):
        raise NotImplementedError()

    @property
    def enabled_now(self):
        if not "enabled" in self.config:
            return False
        return self.config["enabled"]
    
    @property
    def disk_devices(self):
        files = os.listdir('/dev')
        devices = []
        for f in files:
            regexVirtualDrive = r"^vd[a-z]+$"
            if not re.search(regexVirtualDrive, f):
                continue
            logging.debug("Found virtual disk %s", f)
            regexHasPartitions = r"^" + re.escape(f) + r"[1-9][0-9]*$"
            if not any(re.match(regexHasPartitions, e) for e in files):
                logging.warn("Virtual disk %s has no partitions and is being excluded", f)
                continue
            devices.append("/dev/" + f)
        if len(devices) == 0:
            raise FileNotFoundError("Did not find a matching block device")
        return devices

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