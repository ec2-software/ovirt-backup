from . import Backend

import logging
import os
import re
import time
import uuid
import ovirtsdk4 as sdk
import ovirtsdk4.types as types


class Backup:
    def __init__(self, config):
        self.config = config["ovirt"]
        self.blacklist = config["blacklist"]
        self.backends = []
        self.search = None
        self.umount = True

        # Use timestamp as a unique ID
        self.event_id = int(time.time())

    def add(self, backend: Backend):
        self.backends.append(backend)
        backend.parent = self

    def connect(self):
        logging.info(
            'Logging into %s@%s with \'%s\'.',
            self.config["username"], self.config["url"], self.config["ca_file"]
        )

        self.connection = connection = sdk.Connection(
            url=self.config["url"],
            username=self.config["username"],
            password=self.config["password"],
            ca_file=self.config["ca_file"],
            debug=True,
            log=logging.getLogger()
        )

        # Get the reference to the root of the services tree:
        system_service = connection.system_service()

        # Get the reference to the service that we will use to send events to
        # the audit log:
        self.events_service = system_service.events_service()

        # Get the reference to the service that manages the virtual machines:
        self.vms_service = vms_service = system_service.vms_service()

        # Find the virtual machine were we will attach the disks in order to do
        # the backup:
        agent_vm_name = self.config["vm_name"]
        agent_vm = vms_service.list(search='name={}'.format(agent_vm_name))[0]
        logging.info(
            'Found  mount agent virtual machine \'%s\', the id is \'%s\'.',
            agent_vm.name, agent_vm.id,
        )
        self.agent_vm_service = vms_service.vm_service(agent_vm.id)

    def event(self, vm, severity, description):
        self.events_service.add(
            event=types.Event(
                vm=types.Vm(
                    id=vm.id,
                ),
                origin=self.config["application_name"],
                severity=severity,
                custom_id=self.event_id,
                description=description,
            ),
        )
        self.event_id += 1

    def attach_disk(self, data_vm):
        # Find the services that manage the data and agent virtual machines:
        data_vm_service = self.vms_service.vm_service(data_vm.id)

        snap_description = '%s-bk-%s' % (data_vm.name, uuid.uuid4())
        self.event(data_vm, types.LogSeverity.NORMAL,
                   'Backup of virtual machine \'{}\' using snapshot \'{}\' is '
                   'starting.'.format(data_vm.name, snap_description))

        # Send the request to create the snapshot. Note that this will return
        # before the snapshot is completely created, so we will later need to
        # wait till the snapshot is completely created.
        # The snapshot will not include memory. Change to True the parameter
        # persist_memorystate to get it (in that case the VM will be paused for a while).
        snaps_service = data_vm_service.snapshots_service()
        snap = snaps_service.add(
            snapshot=types.Snapshot(
                description=snap_description,
                persist_memorystate=True,
            ),
        )
        logging.info(
            'Sent request to create snapshot \'%s\', the id is \'%s\'.',
            snap.description, snap.id,
        )

        # Poll and wait till the status of the snapshot is 'ok', which means
        # that it is completely created:
        snap_service = snaps_service.snapshot_service(snap.id)
        while snap.snapshot_status != types.SnapshotStatus.OK:
            time.sleep(1)
            snap = snap_service.get()
        logging.info('The snapshot is now complete.')

        # Retrieve the descriptions of the disks of the snapshot:
        snap_disks_service = snap_service.disks_service()
        snap_disks = snap_disks_service.list()

        # Attach all the disks of the snapshot to the agent virtual machine, and
        # save the resulting disk attachments in a list so that we can later
        # detach them easily:
        attachments_service = self.agent_vm_service.disk_attachments_service()
        attachments = []
        for snap_disk in snap_disks:
            attachment = attachments_service.add(
                attachment=types.DiskAttachment(
                    disk=types.Disk(
                        id=snap_disk.id,
                        snapshot=types.Snapshot(
                            id=snap.id,
                        ),
                    ),
                    active=True,
                    bootable=False,
                    interface=types.DiskInterface.VIRTIO,
                ),
            )
            attachments.append(attachment)
            logging.info(
                'Attached disk \'%s\' to the agent virtual machine.',
                attachment.disk.id,
            )

        # Now the disks are attached to the virtual agent virtual machine, we
        # can then ask that virtual machine to perform the backup. Doing that
        # requires a mechanism to talk to the backup software that runs inside the
        # agent virtual machine. That is outside of the scope of the SDK. But if
        # the guest agent is installed in the virtual machine then we can
        # provide useful information, like the identifiers of the disks that have
        # just been attached.
        for attachment in attachments:
            if attachment.logical_name is not None:
                logging.info(
                    'Logical name for disk \'%s\' is \'%s\'.',
                    attachment.disk.id, attachment.logicalname,
                )
            else:
                logging.info(
                    'The logical name for disk \'%s\' isn\'t available. Is the '
                    'guest agent installed?',
                    attachment.disk.id,
                )

        # We need to sleep here because the system needs time to scan the drives
        time.sleep(self.config["attach_wait_seconds"])

        self.attachments = attachments
        self.attachments_service = attachments_service
        self.snap_description = snap_description
        self.snap_service = snap_service

    def detach_disk(self, data_vm):
        if not self.umount:
            logging.info("Skipping detach")
            return

        # Detach the disks from the agent virtual machine:
        for attachment in self.attachments:
            attachment_service = self.attachments_service.attachment_service(
                attachment.id)
            attachment_service.remove()
            logging.info(
                'Detached disk \'%s\' to from the agent virtual machine.',
                attachment.disk.id,
            )
        self.event(data_vm,
                   severity=types.LogSeverity.NORMAL,
                   description='Backup of virtual machine \'{}\' using snapshot \'{}\' is '
                   'completed.'.format(data_vm.name, self.snap_description))

        # Remove the snapshot:
        self.snap_service.remove()
        logging.info('Removed the snapshot \'%s\'.', self.snap_description)

    def save_ovf(self, data_vm):
        # Save the OVF to a file, so that we can use to restore the virtual
        # machine later. The name of the file is the name of the virtual
        # machine, followed by a dash and the identifier of the virtual machine,
        # to make it unique:
        ovf_data = data_vm.initialization.configuration.data
        ovf_file = self.config["ovf_dest"].format(
            name=data_vm.name, id=data_vm.id)
        with open(ovf_file, 'wb') as ovs_fd:
            ovs_fd.write(ovf_data.encode('utf-8'))
        logging.info('Wrote OVF to file \'%s\'.', os.path.abspath(ovf_file))

    def get_vms(self):
        # Find the virtual machine that we want to back up. Note that we need to
        # use the 'all_content' parameter to retrieve the retrieve the OVF, as
        # it isn't retrieved by default:
        l = self.vms_service.list(all_content=True, search=self.search)

        def exclude_vms(vm):
            if vm.name == self.config["vm_name"]:
                return False
            for x in self.blacklist:
                if x.startswith("/") and x.endswith("/"):
                    x = x[1:-1]
                    if re.match(x, vm.name):
                        return False
                elif x == vm.name:
                    return False
            return True
        return list(filter(exclude_vms, l))

    def close(self):
        logging.info("Closing connection")
        self.connection.close()
        self.connection = None
        self.agent_vm_service = None
        self.vms_service = None
        self.events_service = None

    def backup(self):
        self.connect()
        try:
            vms = self.get_vms()
            logging.info("Backing up %s vms", len(vms))
            for data_vm in vms:
                self.save_ovf(data_vm)
                self.attach_disk(data_vm)
                try:
                    for backend in self.backends:
                        logging.info('Checking backend if enabled...')
                        if backend.enabled_now:
                            logging.info(
                                'Backing %s up with backend %s', data_vm.name, backend.name)
                            backend.backup(data_vm.name)
                        logging.info('Done with backup')
                finally:
                    self.detach_disk(data_vm)
        finally:
            self.close()
