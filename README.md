docker-volume-backup
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
```
python backup.py backup [yourcontainername]
```

will output a tar file with name of your container that you can move around

```
python backup.py restore [yourcontainername] [destinationname]
```

will restore the tar backup as a new data container

## Example usage:
TBD

## Run as a Container:
First, you need to build it :
```
docker build --rm --no-cache -t docker-volume-backup .
```

Once done, can can backup using :
```
docker run -t -i --rm \
  -v /var/lib/docker/vfs:/var/lib/docker/vfs \
  -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/backup docker-volume-backup \
  backup <container>
```
The .tar backups will be stored in /backup ... which you can bind to any dir on your docker host (above on /tmp not a good idea ;) )

```
 docker run -t -i --rm \
  -v /var/lib/docker/vfs:/var/lib/docker/vfs \
  -v /var/run/docker.sock:/var/run/docker.sock \
  restore <backupedcontainer> <newcontainer> <tar storage absolute path on host>
```
The .tar backups will be Fetched in "tar storage absolute path on host" ...


## Sources
Based on the code from docker-volume-backup : https://github.com/paimpozhil/docker-volume-backup
