from . import Backend,MountBackend
import subprocess
import os

class ResticBackend(MountBackend):
    def backup(self, vm_name):
        repo = self.config["repository"]
        password = self.config["password"]

        self.mount(vm_name)
        subprocess.run(["/opt/restic",
                        "-r", repo,
                        "backup",
                        "/media/{}/vd".format(vm_name)
                        ], env=dict(os.environ, RESTIC_PASSWORD=password))
        self.umount(vm_name)