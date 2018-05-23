from .. import Backend
import subprocess
import shutil
import os
import logging

class ClonezillaBackend(Backend):
    def __init__(self,config):
        super().__init__("clonezilla", config)


    def backup(self, vm_name):
        prefix = "/dev/"
        devices = []
        for dev in self.disk_devices:
            if dev.startswith(prefix):
                devices.append(dev[len(prefix):])
            else:
                raise Exception("Device name doesn't start with /dev/")

        clonezillaDest = "/home/partimag"
        dest = os.path.join(clonezillaDest, vm_name)
        tmp = os.path.join(clonezillaDest, "{}.tmp".format(vm_name))
        
        try:
            logging.info("Moving %s to %s", dest, tmp)
            shutil.move(dest, tmp)
        except:
            pass

        for dev in devices:
            subprocess.run(["sudo", "ocs-sr",
                        "--batch",
                        "--force-to-use-dd",
                        "--clone-hidden-data",
                        "--nogui",
                        "--smp-gzip-compress",
                        "--image-size", "2000",
                        "--postaction", "true",  # We run the true command to do nothing
                        "savedisk",
                        vm_name,  # Image name
                        dev
                        ], check=True)
        
        logging.info("Removing tmp directory %s", tmp)
        try:
            shutil.rmtree(tmp)
        except:
            pass