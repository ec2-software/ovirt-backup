import yaml
from lib import Backup,ResticBackend

with open("config.yml") as c:
    config = yaml.safe_load(c)

b = Backup(config)
b.add(ResticBackend(config["restic"]))
b.backup()