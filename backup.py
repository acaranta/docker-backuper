#!/usr/bin/python

import docker
import argparse
import sys
import pickle
import tarfile
import os
from subprocess import call

import pprint
pp = pprint.PrettyPrinter(indent=4)

#Arguments parsing
argsparser = argparse.ArgumentParser()
argsparser.add_argument("action", choices=["backup", "restore"])
argsparser.add_argument("container")
argsparser.add_argument("-s","--storage", help="[BACKUP/RESTORE] where to store/restore data, defaults to current path (for BACKUP running inside a container, this parameter isn't used)", metavar="Absolute_Storage_Path")
argsparser.add_argument("-d","--destcontainer", help="[RESTORE] name of the restored container, defaults to source container name", metavar="destcontainername")

args=argsparser.parse_args()


#Initialize docker client
c = docker.Client(base_url='unix://var/run/docker.sock',
                  version='1.9',
                  timeout=10)

#Determines if we run within a docker container
#Might not be truly cleany as a way to check but it works ;)
def dockerized():
	if 'docker' in open('/proc/1/cgroup').read():
		return True

#Check if a container exists (running or not)
def check_container_exists(c, name):
	containers = c.containers(all=True)
	for i, container in enumerate(containers):
		names = container['Names']
		for j, n in enumerate(names):
			if n == "/"+name:
				return True
	return False

#source container name
name = args.container

#Location of the tar files (for a container running)
datadir = "/backup"

if args.action == "backup":
	container = c.inspect_container(name)
##	pp.pprint(container)
	container_name =  container['Name']
	container_tarfile = ""
	volumes =  container['Volumes']
	
#NEED TO FIND A WAY TO SET DIFFERENT PATHS FOR BACK (Containerized backup TOO ?)
	if dockerized():
		tar = tarfile.open(datadir + "/" + name + ".tar", "w:gz")
		container_tarfile = datadir + "/" + name + ".tar"
	else:
		if args.storage:
			tar = tarfile.open(args.storage + "/" + name + ".tar", "w:gz")
			container_tarfile = args.storage + "/" + name + ".tar"
		else:
			tar = tarfile.open(name + ".tar", "w:gz")
			container_tarfile = name + ".tar"
	print "Backing up : " + container_name + " to : " + container_tarfile
	pickle.dump ( container , open ("metadata","wb") )
	tar.add("metadata")
	for i, v in enumerate(volumes):
	    print  v, volumes[v]
	    tar.add(volumes[v],v)
	tar.close()

elif args.action == "restore":
	#third argument is the restored container name
	destname = args.container
	if args.destcontainer:
		destname = args.destcontainer

	if check_container_exists(c, destname):
		print "Destination container : "+ destname + " already exists ... cannot continue !!"
		sys.exit(2)
	
	if dockerized() and not args.storage:
		print "Restore Storage is missing !"
		sys.exit(1)
#	if dockerized() and args.storage:
#		datadir = args.storage

	container_tarfile = ""
	if dockerized():
		tar = tarfile.open(datadir + "/" + name + ".tar")
		container_tarfile = datadir + "/" + name + ".tar"
	else:
		tar = tarfile.open(name + ".tar")
		container_tarfile = name + ".tar"
	print "Restoring "+container_tarfile+" into "+destname
	metadatafile =  tar.extractfile("metadata")
	metadata =  pickle.load(metadatafile)

	imagename = metadata["Config"]["Image"]
	volumes =  metadata['Volumes']
	envs = metadata['Config']['Env']
	ports = metadata['NetworkSettings']['Ports']
	envlist = []
	vlist = []
	binds = {} 
	portslist = []
	portsbindings = {}
	#Re-inject Env Vars	
	if ports:
		for i, v in enumerate(ports):
			if v.split('/')[1] == 'tcp':
				portslist.append(int(v.split('/')[0]))
			elif v.split('/')[1] == 'udp':
				portslist.append((int(v.split('/')[0]),'udp'))
			if ports[v] is list:
				for j, p in enumerate(ports[v]):
					print p['HostIp']
					print p['HostPort']
					if v.split('/')[1] == 'tcp':
						portsbindings[int(p['HostPort'])] = (p['HostIp'], v.split('/')[0])
					elif v.split('/')[1] == 'udp':
						portsbindings[p['HostPort']+"/udp"] = (p['HostIp'], v.split('/')[0])
			else:
				if v.split('/')[1] == 'tcp':
					portsbindings[int(v.split('/')[0])] = ports[v]
				elif v.split('/')[1] == 'udp':
					portsbindings[v] = ports[v]

##	print "Ports lists"	
##	pp.pprint(portslist)
##	pp.pprint(portsbindings)

	for i, v in enumerate(envs):
		envlist.append(v)

	for i, v in enumerate(volumes):
       		print  v, volumes[v]
		vlist.append(v)
		#check if volume has a binding, and add it to bindings for inplace restore
		if str(volumes[v]).find('/var/lib/docker/vfs/dir/') < 0:
			binding = { volumes[v]:{'bind':v} }
			binds.update(binding)
	restored_container = c.create_container(imagename,tty=True,volumes=vlist,environment=envlist,name=destname,ports=portslist)
	print "Starting "+destname+" container..."
	c.start(restored_container,binds=binds,port_bindings=portsbindings);

	#Recreate volumes_from (as it does not work when binds+volumes_from are used together
	infodest = c.inspect_container(restored_container)
	volumes = infodest['Volumes']
	vlist = []
	binds = {}
	for i, v in enumerate(volumes):
		vlist.append(v)
		binding = { volumes[v]:{'bind':v} }
		binds.update(binding)

        #Add tar storage to bindings list
        if dockerized():
                datadir = args.storage
                binds.update({str(datadir): {'bind': '/backup2'} })
        else:
		if args.storage:
			binds.update({ args.storage: {'bind': '/backup2'} })
		else:
			binds.update({ str(os.path.dirname(os.path.realpath(__file__))): {'bind': '/backup2'} })

	pp.pprint(vlist)
	restorer_container = c.create_container('ubuntu',detach=False, stdin_open=True, tty=True, command="tar xvf /backup2/"+ name +".tar", volumes=vlist)
	print "Starting Restoration container ("+restorer_container['Id']+")"
	c.start(restorer_container,binds=binds)

	print "Waiting for the end of restore container ..."
	c.wait(restorer_container)
	print c.logs(restorer_container['Id'])
	c.remove_container(restorer_container)

else:
	usage()
