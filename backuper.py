# !/usr/bin/python

import docker
import argparse
import sys
import pickle
import tarfile
import os
import re
import texttable
# from subprocess import call

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Arguments parsing
argsparser = argparse.ArgumentParser(description="backup/restore/list a container and its volumes")
subparsers = argsparser.add_subparsers(help='sub-command help : ', dest="command")

listparser = subparsers.add_parser('list', help='Lists the volumes of the container')
listparser.add_argument("container", help="Name of the container")

backupparser = subparsers.add_parser('backup', help="Backups a container to a tar file")
backupparser.add_argument("-p", "--pausecontainer", help="Should we stop the source container before extracting/saving its volumes and restart it after backup (useful for files to be closed prior the backup)", default=False, action="store_true")
backupparser.add_argument("-i", "--includevolumes", help="include volumes in backup (without this option only backups in /var/lib/docker/vfs on host are backed up. The syntax is a string of elements that will be matched against all volumes/bindings. Elements are seperated by a coma ', ' and can be regex")
backupparser.add_argument("-s", "--storage", help="where to store/restore data, defaults to current path (for BACKUP running inside a container, this parameter isn't used)", metavar="Absolute_Storage_Path")
backupparser.add_argument("container", help="Name of the container")

restoreparser = subparsers.add_parser('restore', help='Restore a container from tar backup')
restoreparser.add_argument("-d", "--destcontainer", help="name of the restored container, defaults to source container name", metavar="destcontainername")
restoreparser.add_argument("-s", "--storage", help="where to store/restore data, defaults to current path (for BACKUP running inside a container, this parameter isn't used)", metavar="Absolute_Storage_Path")
restoreparser.add_argument("-r", "--restoreinplace", help="if the backed up container had mounted (bound) directories on host, should we restore these bindings AND the data in it (overwriting data on host maybe)", default=False, action="store_true")
restoreparser.add_argument("container", help="Name of the container")

args = argsparser.parse_args()

# Initialize docker client
c = docker.Client(base_url='unix: //var/run/docker.sock',
                  version='1.9',
                  timeout=30)

# Determines if we run within a docker container
# Might not be truly cleany as a way to check but it works ;)


def dockerized():
    if 'docker' in open('/proc/1/cgroup').read():
        return True

# Currently unused, this sub seems self explanatory


def getowndockerid():
    dockerid = ""
    for line in open('/proc/1/cgroup'):
        if "docker" in line:
            dockerid = re.search(r".*/docker/(.*)$", line)
            return dockerid.group(1)
    if dockerid == "":
        return False

# Returns the terminal size WxH
# Found on http: //stackoverflow.com/a/566752/2646228


def getTerminalSize():
    import os
    env = os.environ

    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            import struct
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))
    return int(cr[1]), int(cr[0])

# Check if a container exists (running or not)


def check_container_exists(c, name):
    containers = c.containers(all=True)
    for i, container in enumerate(containers):
        names = container['Names']
        for j, n in enumerate(names):
            if n == "/" + name:
                return True
    return False

# source container name
name = args.container

# Location of the tar files (for a container running)
datadir = "/backup"

if args.command == "backup":
    if not check_container_exists(c, name):
        print "Container " + name + " not found !"
        sys.exit(3)
    container = c.inspect_container(name)
    container_name = container['Name']
    container_tarfile = ""
    volumes = container['Volumes']

    if dockerized():
        tar = tarfile.open(datadir + "/" + name + ".tar", "w: gz")
        container_tarfile = datadir + "/" + name + ".tar"
    else:
        if args.storage:
            tar = tarfile.open(args.storage + "/" + name + ".tar", "w: gz")
            container_tarfile = args.storage + "/" + name + ".tar"
        else:
            tar = tarfile.open(name + ".tar", "w: gz")
            container_tarfile = name + ".tar"
    print "Backing up : " + container_name + " to : " + container_tarfile
    pickle.dump(container, open("metadata", "wb"))
    tar.add("metadata")
    # Compute and prepare the volumes to backup
    bkpvolumes = {}
    for i, v in enumerate(volumes):
        if args.includevolumes:
            for j, r in enumerate(args.includevolumes.split(', ')):
                if (re.search(str(r), v)) or (re.search(str(r), volumes[v])):
                    bkpvolumes[v] = volumes[v]
        else:
            if str(volumes[v]).find('/var/lib/docker/vfs/dir/') >= 0:
                bkpvolumes[v] = volumes[v]
    if not bkpvolumes:
        print "No Volumes Selected !!!"
        if args.includevolumes:
            print "Please review your --includevolumes option value : '" + args.includevolumes + "'"
        else:
            print "Please use the --includevolumes option"
        print "or use the 'list' command to check your container's volumes"
        sys.exit(4)

    if args.pausecontainer:
        print "Stopping container " + name + " before backup as requested"
        c.stop(name)
        c.wait(name)
    for i, v in enumerate(bkpvolumes):
        print v, bkpvolumes[v]
        if dockerized():
            tar.add(v)
        else:
            tar.add(bkpvolumes[v], v)

    tar.close()
    if args.pausecontainer:
        print "Restarting container " + name + " ..."
        c.restart(name)


elif args.command == "restore":
    # third argument is the restored container name
    destname = args.container
    if args.destcontainer:
        destname = args.destcontainer

    if check_container_exists(c, destname):
        print "Destination container : " + destname + " already exists ... cannot continue !!"
        sys.exit(2)

    if dockerized() and not args.storage:
        print "Restore Storage is missing !"
        sys.exit(1)

    container_tarfile = ""
    if dockerized():
        tar = tarfile.open(datadir + "/" + name + ".tar")
        container_tarfile = datadir + "/" + name + ".tar"
    else:
        if args.storage:
            tar = tarfile.open(args.storage + "/" + name + ".tar")
            container_tarfile = args.storage + "/" + name + ".tar"
        else:
            tar = tarfile.open(name + ".tar")
            container_tarfile = name + ".tar"
    print "Restoring " + container_tarfile + " into " + destname
    metadatafile = tar.extractfile("metadata")
    metadata = pickle.load(metadatafile)

    imagename = metadata["Config"]["Image"]
    volumes = metadata['Volumes']
    envs = metadata['Config']['Env']
    ports = metadata['NetworkSettings']['Ports']
    envlist = []
    vlist = []
    binds = {}
    portslist = []
    portsbindings = {}
    # Re-inject Env Vars
    if ports:
        for i, v in enumerate(ports):
            if v.split('/')[1] == 'tcp':
                portslist.append(int(v.split('/')[0]))
            elif v.split('/')[1] == 'udp':
                portslist.append((int(v.split('/')[0]), 'udp'))
            if ports[v] is list:
                for j, p in enumerate(ports[v]):
                    print p['HostIp']
                    print p['HostPort']
                    if v.split('/')[1] == 'tcp':
                        portsbindings[int(p['HostPort'])] = (p['HostIp'], v.split('/')[0])
                    elif v.split('/')[1] == 'udp':
                        portsbindings[p['HostPort'] + "/udp"] = (p['HostIp'], v.split('/')[0])
            else:
                if v.split('/')[1] == 'tcp':
                    portsbindings[int(v.split('/')[0])] = ports[v]
                elif v.split('/')[1] == 'udp':
                    portsbindings[v] = ports[v]

    for i, v in enumerate(envs):
        envlist.append(v)

    # Preparing nice volumes restored output
    table = texttable.Texttable()
    table.set_cols_align(["l", "l"])
    (cwidth, cheight) = getTerminalSize()
    cwidth = (cwidth-8)/2
    table.set_cols_width([cwidth, cwidth])
    table.header(["Mount point (in container)", "Bound to (on docker host)"])

    for i, v in enumerate(volumes):
        vlist.append(v)
        # check if volume has a binding, and add it to bindings for inplace restore
        if str(volumes[v]).find('/var/lib/docker/vfs/dir/') < 0:
            if args.restoreinplace:
                binding = {volumes[v]: {'bind': v}}
                binds.update(binding)
    restored_container = c.create_container(imagename, tty=True, volumes=vlist, environment=envlist, name=destname, ports=portslist)
    print "Starting " + destname + " container first time to fetch volumes information..."
    c.start(restored_container, binds=binds, port_bindings=portsbindings)

    # Recreate volumes_from (as it does not work when binds + volumes_from are used together
    infodest = c.inspect_container(restored_container)
    c.stop(restored_container)
    print "Waiting " + destname + " container to stop ..."
    c.wait(restored_container)
    volumes = infodest['Volumes']
    vlist = []
    bindrestore = {}
    for i, v in enumerate(volumes):
        table.add_row([v, volumes[v]])
        vlist.append(v)
        binding = {volumes[v]: {'bind': v}}
        bindrestore.update(binding)

    print table.draw()
    # Add tar storage to bindings list
    if dockerized():
            datadir = args.storage
            bindrestore.update({str(datadir): {'bind': '/backup2'}})
    else:
        if args.storage:
            bindrestore.update({args.storage: {'bind': '/backup2'}})
        else:
            bindrestore.update({str(os.path.dirname(os.path.realpath(__file__))): {'bind': '/backup2'}})

    restorer_container = c.create_container('ubuntu', detach=False, stdin_open=True, tty=True, command="tar xvf /backup2/" + name + ".tar", volumes=vlist)
    print "Starting Restoration container (" + restorer_container['Id'] + ")"
    c.start(restorer_container, binds=bindrestore)

    print "Waiting for the end of restore container ..."
    c.wait(restorer_container)
    print c.logs(restorer_container['Id'])
    c.remove_container(restorer_container)

    print "Starting " + destname + " container..."
    c.start(restored_container, port_bindings=portsbindings)

elif args.command == "list":
    if not check_container_exists(c, name):
        print "Container " + name + " not found !"
        sys.exit(3)
    (cwidth, cheight) = getTerminalSize()
    container = c.inspect_container(name)
    container_name = container['Name']
    container_tarfile = ""
    volumes = container['Volumes']
    if volumes:
        print "Volumes on container " + name + " ..."
        table = texttable.Texttable()
        table.set_cols_align(["l", "l"])
        cwidth = (cwidth-8)/2
        table.set_cols_width([cwidth, cwidth])
        table.header(["Mount point (in container)", "Bound to (on docker host)"])
        for i, v in enumerate(volumes):
            table.add_row([v, volumes[v]])
        print table.draw()
else:
    print "You did not choose any action to be performed [--backup|--restore|--list] !!!"
    argsparser.print_help()
    sys.exit()
