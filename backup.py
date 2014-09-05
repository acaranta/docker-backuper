import docker
import sys
import pickle
import tarfile
import os
from subprocess import call

c = docker.Client(base_url='unix://var/run/docker.sock',
                  version='1.9',
                  timeout=10)

#Prints Help Message
def usage():
	print "Running normally :"
	print " python backup.py [backup/restore] data-container-name [restore-container-name]"
	print "Running withing as a docker image (named docker-volume-backup) :"
	print " docker run -t -i --rm \ "
	print "  -v /var/lib/docker/vfs:/var/lib/docker/vfs \ "
	print "  -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/backup docker-volume-backup \ "
	print "  backup <container>"
	print "docker run -t -i --rm \ "
	print "  -v /var/lib/docker/vfs:/var/lib/docker/vfs \ "
	print "  -v /var/run/docker.sock:/var/run/docker.sock \ "
	print "  restore <backupedcontainer> <newcontainer> <tar storage absolute path on host>"

#Determines if we run within a docker container
#Might not be truly cleany as a way to check but it works ;)
def dockerized():
	if 'docker' in open('/proc/1/cgroup').read():
		return True

#first argument is the option backup/restore
if len(sys.argv) < 3:
	print "Not enough arguments !!"
	usage()
	sys.exit(1)

option = sys.argv[1]
name = sys.argv[2]

#Location of the tar files (for a container running)
datadir = "/backup"

if option == "backup":
	# second argument is the container name

	container = c.inspect_container(name)
	import pprint
	pp = pprint.PrettyPrinter(indent=4)
	pp.pprint(container)
	container_name =  container['Name']
	print "Backing up : " + container_name
	volumes =  container['Volumes']
	
	print "writing meta data to file "
	pickle.dump ( container , open ("metadata","wb") )

	if dockerized():
		tar = tarfile.open(datadir + "/" + name + ".tar", "w:gz")
	else:
		tar = tarfile.open(name + ".tar", "w:gz")
	tar.add("metadata")
	for i, v in enumerate(volumes):
	    print  v, volumes[v]
	    tar.add(volumes[v],v)
	tar.close()

elif option == "restore":
	#third argument is the restored container name
	destname = sys.argv[3]
	if dockerized() and len(sys.argv) < 5:
		print "Restore Storage is missing !"
		usage()
		sys.exit(1)

	print "Restoring "+name+".tar into "+destname
	if dockerized():
		tar = tarfile.open(datadir + "/" + name + ".tar")
	else:
		tar = tarfile.open(name + ".tar")
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
	import pprint
	pp = pprint.PrettyPrinter(indent=4)
#	pp.pprint(ports)
	#Re-inject Env Vars	
	for i, v in enumerate(ports):
#		print v, ports[v]
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

	print "Ports lists"	
	pp.pprint(portslist)
	pp.pprint(portsbindings)

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
                datadir = sys.argv[4]
                binds.update({str(datadir): {'bind': '/backup2'} })
        else:
                binds.update({ str(os.path.dirname(os.path.realpath(__file__))): {'bind': '/backup2'} })


	restorer_container = c.create_container('ubuntu',detach=False, stdin_open=True, tty=True, command="tar xvf /backup2/"+ name +".tar", volumes=vlist)
	print "Starting Restoration container ("+restorer_container['Id']+")"
	c.start(restorer_container,binds=binds)

	print "Waiting for the end of restore container ..."
	c.wait(restorer_container)
	print c.logs(restorer_container['Id'])
	c.remove_container(restorer_container)

else:
	usage()
