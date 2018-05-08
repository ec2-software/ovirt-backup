from . import Backend
import json
import re
import os
import subprocess
import errno

# TODO: Mount with UUIDs
# TODO: Filter by filesystem type
# TODO: Write the Filesytem information to the root directory `lsblk -Jpbft /dev/vd*`

class MountBackend(Backend):
    def parse_block(self):
        bla = subprocess.check_output(["sudo", "lsblk",
                                       "--json",
                                       "--paths",  # Get full paths to mount with
                                       #"--fs", # Return the UUIDs to mount with and the filesystem type
                                       #"--bytes" # Print size in bytes instead of human readable
                                       self.disk_device])
        obj = json.loads(bla.decode("utf-8"))
        return obj["blockdevices"][0]

    def mount_dir(self, systemname):
        return os.path.join(self.config["mountpoint"], systemname)

    def mount(self, systemname):
        dev = self.parse_block()
        mount_dir = self.mount_dir(systemname)

        def mount(name, path):
            print("mount", path, name)
            # We intentionally ignore mount failures. If it doesn't mount, it doesn't back up.
            subprocess.run(["sudo", "mount", "-r", name, path])
        self.dev_recurse(mount_dir, dev, mount)

    def umount(self, systemname):
        dev = self.parse_block()
        mount_dir = self.mount_dir(systemname)

        def umount(name, path):
            subprocess.run(["sudo", "umount",  path])
        self.dev_recurse(mount_dir, dev, umount)

    def dev_recurse(self, mount_dir, dev, action):
        path = os.path.join(mount_dir, os.path.basename(dev["name"]))
        if "children" in dev:
            for x in dev["children"]:
                self.dev_recurse(path, x, action)
        else:
            path = re.sub(r"vd[a-z]", "vd", path)
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise
            action(dev["name"], path)
