#!/usr/bin/env python3
import yaml
import backup
import backup.backends
import logging

with open("config.yml") as c:
    config = yaml.safe_load(c)

logging.basicConfig(level=logging.DEBUG, filename='example.log')
b = backup.Backup(config)
b.add(backup.backends.ResticBackend(config["restic"]))
b.backup()
