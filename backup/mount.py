from . import Backend
import json
import re
import os
import subprocess
import errno
import logging
import time

# TODO: Mount with UUIDs
# TODO: Filter by filesystem type
# TODO: Write the Filesytem information to the root directory `lsblk -Jpbft /dev/vd*`


class MountBackend(Backend):
    def parse_blocks(self):
        bla = subprocess.check_output(["sudo", "lsblk",
                                    "--json",
                                    "--paths",  # Get full paths to mount with
                                    "--fs",  # Filesystem type
                                    "--bytes",  # Sizes in bytes instead of human readable
                                    *self.disk_devices])
        obj = json.loads(bla.decode("utf-8"))

        return obj["blockdevices"]

    def mount_dir(self, systemname):
        return os.path.join(self.config["mountpoint"], systemname)

    def mount(self, systemname):
        devs = self.parse_blocks()
        mount_dir = self.mount_dir(systemname)

        logging.debug(devs)

        def mount(name, path):
            # We intentionally ignore mount failures. If it doesn't mount, it doesn't back up.
            self.cmd_log(["sudo", "mount", "-r", name, path])
        for dev in devs:
            self.dev_recurse(mount_dir, dev, mount)

    def umount(self, systemname):
        if self.parent and not self.parent.umount:
            logging.info("Skipping unmounting")
            return

        devs = self.parse_blocks()
        mount_dir = self.mount_dir(systemname)

        def umount(name, path):
            # If it didn't mount, umount will fail
            self.cmd_log(["sudo", "umount", path])
            time.sleep(5)
        for dev in devs:
            self.dev_recurse(mount_dir, dev, umount)

    def dev_recurse(self, mount_dir, dev, action):
        if "children" in dev:
            for x in dev["children"]:
                self.dev_recurse(mount_dir, x, action)
        else:
            if dev["fstype"] == None:
                return

            path = os.path.join(mount_dir, dev["uuid"])
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise

            action(dev["name"], path)
