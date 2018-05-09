#!/usr/bin/env python3
import yaml
import backup
import backup.backends

with open("config.yml") as c:
    config = yaml.safe_load(c)

b = backup.Backup(config)
b.add(backup.backends.ResticBackend(config["restic"]))
#b.backup()
