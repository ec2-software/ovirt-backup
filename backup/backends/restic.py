from .. import Backend, MountBackend
import subprocess
import os
import logging


class ResticBackend(MountBackend):
    def __init__(self, config):
        super().__init__("restic", config)

    def backup(self, vm_name: str):
        repo = self.config["repository"]
        password = self.config["password"]
        base_dir = self.config["mountpoint"]

        try:
            self.mount(vm_name)
            subprocess.run(["/opt/restic",
                            "-r", repo,
                            "--hostname", vm_name,
                            "backup",
                            os.path.join(base_dir, vm_name)
                            ],
                           env=dict(os.environ, RESTIC_PASSWORD=password),
                           check=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
        except Exception as err:
            logging.info("Restic backup failed %s", err)
            raise
        else:
            logging.info("Restic backup completed successfully")
        finally:
            self.umount(vm_name)
