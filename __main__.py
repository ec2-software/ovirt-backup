#!/usr/bin/env python3
import yaml
import backup
import backup.backends
import logging
import argparse
import os

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description="Backup Ovirt VMs")
parser.add_argument("--config", dest="config_file", default="config.yml", help="set config file path")
parser.add_argument("--search", dest="search", default=None, help="search for specific VM name")
parser.add_argument("--umount", type=str2bool, dest="umount", default=True, help="Unmount the drives and detach the disks")
args = parser.parse_args()

#defaults_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "defaults.yml")

#for file in [ defaults_file, "/etc/ovirt-backup/config.yml", args.config_file ]:


with open(args.config_file) as c:
    config = yaml.safe_load(c)

logging.basicConfig(level=logging.DEBUG, filename='/var/log/ovirt-backup.log')
#logging.getLogger().addHandler(logging.StreamHandler())

b = backup.Backup(config)
b.search = args.search
b.umount = args.umount

b.add(backup.backends.ResticBackend(config["restic"]))
b.add(backup.backends.ClonezillaBackend(config["clonezilla"]))
b.backup()
