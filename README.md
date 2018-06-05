# Ovirt Backup System

This is a modular backup system that allows you to backup all the VMs in an Ovirt instance regularly without any configuration in the VMs.

These are the available backup mechanisms.

- [x] Ovirt OVF file - Backs up only the configuration of the VM, useful if you need to recreate it from a Clonezilla, etc. backup.
- [x] [Restic](https://restic.net/) - Mounts drives and backs up files.
- [x] [Clonezilla](http://www.clonezilla.org/) - Backs up entire disk as a restorable image.

It works by sitting in a VM in your Ovirt cluster and automatically snapshotting, attaching, and mounting each drive from each other VM and running one of the backup mechanisms.

## Install

Set up Virtual Machine with Ubuntu 16.04 LTS in your Ovirt cluster. This is the VM where you will run the script. [Install the Ovirt guest agent.](https://www.ovirt.org/documentation/how-to/guest-agent/install-the-guest-agent-in-ubuntu/) The following specifications worked well in our instance:

| Disk Space | RAM | CPUs |
| ---------- | --- | ---- |
| 50 GB      | 8 GB| 4    |

> It is best to NOT use LVM when setting up the hard disk. It's possible to run the script with it, but it requires extra configuration.

Mount your backup drive into your newly created VM. Make sure this mount is in your `/etc/fstab` for long-term use. You'll need to install whatever dependencies you need for the type of mount.

```
# Gluster mount
add-apt-repository ppa:gluster/glusterfs-3.12
apt-get update
apt-get install glusterfs-client

# NFS Mount
apt-get install nfs-common
```

> Clonezilla only backs up to the `/home/partimag` directory, so it's recommended you make this where you mount your backup to.

### Install Script

```bash
apt-get install \
    autoconf \
    gcc \
    git \
    libtool \
    libxml2-dev \
    make \
    pep8 \
    pkg-config \
    python-ethtool \
    python3-yaml \
    python3-dev \
    python3-pip \
    usermode
pip3 install ovirt-engine-sdk-python
```

Git clone the project into a directory. You can then run the script by running `python3 $DIRECTORY_CLONED --help`. To see the arguments.

### Clonezilla

To use clonezilla, you will need to install the command-line tool. Clonezilla is usually a boot disk, but the script installed on the disk can be installed on Ubuntu through a PPA.

```bash
echo 'deb http://us.archive.ubuntu.com/ubuntu xenial main universe' >> /etc/apt/sources.list
apt-get update
apt-get install \
    clonezilla \
    bc  # For some reason, clonzilla doesn't require this in it's package.
```

### Restic

There are packages for restic, but they tend to be old. You can [download the lastest release from the project's GitHub page](https://github.com/restic/restic/releases). Don't forget to initialize the repository once you've downloaded it.

```bash
wget https://github.com/restic/restic/releases/download/v0.9.0/restic_0.9.0_linux_amd64.bz2
bzip2 -d restic_0.9.0_linux_amd64.bz2
mv restic_0.9.0_linux_amd64 /opt/restic
chmod +x /opt/restic
/opt/restic init --repo /home/partimag/restic
```

## Configuration

Ovirt-Backups reads configurations from 3 locations, each successive location overwritting the previous values. This is usefull because you can set up a base config in `/etc/ovirt-backup/config.yml`, then run the script with a config file that enables the specific backup types you want for your schedule.

- `defaults.yml` in the project directory. Do not modify this file.
- `/etc/ovirt-backup/config.yml` Create this file by copying `defaults.yml` to this location.
- `config.yml` in the current working directory. This can be replaced with the `--config` command line parameter.

```yaml
ovirt:
  url: https://ovirt.example.com     # The API URL of your Ovirt instance
  username: admin@internal           # Username and password for authentication
  password: ''                       #   should have permission for all VMs
  ca_file: ca.pem                    # Cert for HTTPs
  application_name: OvirtBackup      # Name displayed inside of Ovirt for your backups
  ovf_dest: '{name}-{id}.ovf'        # Python `.format` pattern for OVF filename
  vm_name: ''                        # Name of the Ovirt VM that this script runs on
  attach_wait_seconds: 10            # How many seconds to wait after attaching a disk to make sure it's connected fully.
restic:
  enabled: false
  repository: ''                     # Path to restic repository
  password: ''
  mountpoint: /media                 # Directory to mount disks that are attached. This should not be a network share. It unmounts after the backup is complete.
clonezilla:
  enabled: false
  destination: /home/partimag/{name} # Pattern `.format` pattern with VM name being backed up. Needs to be an immediate subdirectory of `/home/partimag`
lvm:
  mapper: /dev/mapper
  whitelist: []                      # If you use LVM, you need to add your device names found in the mapper directory to prevent the script from unmounting them.
logs:
  file: /var/log/ovirt-backup.log    # Currently does not support logging to stdout, pull requests welcome ;)
retries:
  attempts: 3                        # If a backup randomly fails, how many attempts to retry it. For example, it will occur 4 times total if you retry 3 times.
  wait_seconds: 10                   # How many seconds to wait between retries.
blacklist: []                        # A list of VMs to not backup. You may begin and end a string with `/` to indicate a regular expression to match many VMs
```

## Known Issues

Sometimes, having other snapshots on the VM will prevent Ovirt from being able to create a new one. You should ensure you don't have snapshosts on the VMs you are backing up.

## Credits

- Thanks to the Ovirt team for a great open source virtual machine management system.
- The basis for this project comes from an SDK example https://github.com/oVirt/ovirt-engine-sdk/blob/master/sdk/examples/vm_backup.py
- https://github.com/wefixit-AT/oVirtBackup
