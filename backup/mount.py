from . import Backend
import json
import re
import os
import subprocess
import errno
import logging

# TODO: Mount with UUIDs
# TODO: Filter by filesystem type
# TODO: Write the Filesytem information to the root directory `lsblk -Jpbft /dev/vd*`


class MountBackend(Backend):
    def parse_block(self):
        bla = subprocess.check_output(["sudo", "lsblk",
                                       "--json",
                                       "--paths",  # Get full paths to mount with
                                       "--fs", # Filesystem type
                                       "--bytes", # Sizes in bytes instead of human readable
                                       self.disk_device])
        obj = json.loads(bla.decode("utf-8"))
        return obj["blockdevices"][0]

    def mount_dir(self, systemname):
        return os.path.join(self.config["mountpoint"], systemname)

    def mount(self, systemname):
        dev = self.parse_block()
        mount_dir = self.mount_dir(systemname)

        logging.debug(dev)

        def mount(name, path):
            # We intentionally ignore mount failures. If it doesn't mount, it doesn't back up.
            return ["sudo", "mount", "-r", name, path]
        self.dev_recurse(mount_dir, dev, mount)

    def umount(self, systemname):
        if self.parent and not self.parent.umount:
            logging.info("Skipping unmounting")
            return

        dev = self.parse_block()
        mount_dir = self.mount_dir(systemname)

        def umount(name, path):
            return ["sudo", "umount",  path]
        self.dev_recurse(mount_dir, dev, umount)

    def dev_recurse(self, mount_dir, dev, action):
        name = os.path.basename(dev["name"])
        name = re.sub(r"^vd[a-z]+", "vd", name)
        path = os.path.join(mount_dir, name)
        
        if "children" in dev:
            for x in dev["children"]:
                self.dev_recurse(path, x, action)
        else:
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise

            args = action(dev["name"], path)
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
