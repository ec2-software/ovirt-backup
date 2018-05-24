#!/usr/bin/env python3
import yaml
import backup
import backup.backends
import logging
import argparse
import os
import pprint

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
parser.add_argument("--show-config", type=str2bool, dest="show_config", default=False, help="Show the configuration options instead of performing a backup") 
args = parser.parse_args()

defaults_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "defaults.yml")

config = {}
for file in [ defaults_file, "/etc/ovirt-backup/config.yml", args.config_file ]:
    print("Loading config file {}".format(file))
    try:
        with open(file, "r") as c:
            backup.util.dict_merge(config, yaml.safe_load(c))
    except IOError as err:
        print("Failed to load {}. {}".format(file, err))
        pass

if args.show_config:
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(config)
    exit()

logging.basicConfig(level=logging.DEBUG, filename=config['logs']['file'])
#logging.getLogger().addHandler(logging.StreamHandler())

b = backup.Backup(config)
b.search = args.search
b.umount = args.umount

b.add(backup.backends.ResticBackend(config["restic"]))
b.add(backup.backends.ClonezillaBackend(config["clonezilla"]))
b.backup()
