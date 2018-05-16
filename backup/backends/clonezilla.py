from .. import Backend
import subprocess


class ClonezillaBackend(Backend):
    def __init__(self,config):
        super().__init__("clonezilla", config)


    def backup(self, vm_name):
        dev = self.disk_device
        if dev.startswith("/dev/"):
            dev = dev[len("/dev/"):]
        else:
            raise Exception("Device name doesn't start with /dev/")

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
