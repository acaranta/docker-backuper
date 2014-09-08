docker-backuper
====================

a python script to backup/restore the docker containers / volumes.

The idea :
* backup will backup the metadata from a container and its volumes
* restore will recreate a container from the saved metadata and restore its volumes

####Requires Python && Docker-py python package.

```
apt-get install python-pip 
pip install docker-py
```


##How to use
Running backup.py with -h will produce :
```
usage: backup.py [-h] [-s Absolute_Storage_Path] [-d destcontainername]
                 {backup,restore} container

positional arguments:
  {backup,restore}
  container

optional arguments:
  -h, --help            show this help message and exit
  -s Absolute_Storage_Path, --storage Absolute_Storage_Path
                        [BACKUP/RESTORE] where to store/restore data, defaults
                        to current path (for BACKUP running inside a
                        container, this parameter isn't used)
  -d destcontainername, --destcontainer destcontainername
                        [RESTORE] name of the restored container, defaults to
                        source container name
```
### Natively on host, BACKUP :
```
./backup.py backup containername --storage /tmp 
```
This command will save the metadata and volumes as a tar file named : `/tmp/containername.tar`
### Natively on host, RESTORE :
```
./backup.py restore containername --storage /tmp --destcontainer newone
```
This command will restore the container `containername` and its volumes as a new container named `newone` from the tar file named : `/tmp/containername.tar`



### Run as a Container:
First, you need to build it :
```
docker build --rm --no-cache -t docker-backuper .
```

Once done, can can backup using :
```
docker run -t -i --rm \
  -v /var/lib/docker/vfs:/var/lib/docker/vfs \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /tmp:/backup \
  acaranta/docker-backuper \
  backup <container> 
```
The .tar backups will be stored in /backup ... which you can bind to any dir on your docker host (above on `/tmp` not a good idea ;) )
In this mode, the `--storage` option is ignored as the data will be stored in the bound directory `/backup`

Then you can restore using :
```
 docker run -t -i --rm \
  -v /var/lib/docker/vfs:/var/lib/docker/vfs \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /tmp:/backup \
  acaranta/docker-backuper \
  restore <container> --destname <newcontainer> --storage /tmp
```
The .tar backups will be Fetched in the argument passed as `--storage`. It works differently from the backup, because for the restore, a container is launched on the docker host with the data storage dir mounted directly in order to read the tar files, it therefore need the `/backup` binding AND the --storage argument both pointing towards the same path.

##NOTES
if a container was launched with a boud volume, ie :
```
docker run -d  -v /srv/docker-external-volumes/registry:/mnt/registry \
	-e STORAGE_PATH=/mnt/registry/storage \
	-e SQLALCHEMY_INDEX_DATABASE=sqlite:////mnt/registry/db/dbreg.sqlite \
	-p 5000:5000 --name my_registry registry
```
(here `/srv/docker-external-volumes/registry` --> `/mnt/registry`)).
The restore WILL take place in this bound path ... aka it will overwrite (it data is present) the contents of `/srv/docker-external-volumes/registry` !!!
That is not a bug, it was designed like this ;)

##TODO
* remove the bound inplace restore by default and add a `--bound-restore` option ?
* add a way to nicely name the tar files ?
* add a way to timestamp the tar files and let the user choose different restore points ?
# DISCLAIMER 
Please TEST your backup/restore procedure, your data, etc ... this is provided as-is and does not garantee anything ! ;)


## Sources
Based on the code from docker-volume-backup : https://github.com/paimpozhil/docker-volume-backup
