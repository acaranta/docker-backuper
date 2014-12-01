docker-backuper
====================
[![Build Status](https://travis-ci.org/acaranta/docker-backuper.svg?branch=master)](https://travis-ci.org/acaranta/docker-backuper)
 [![Stories in Ready](https://badge.waffle.io/acaranta/docker-backuper.svg?label=ready&title=Ready)](http://waffle.io/acaranta/docker-backuper) 

A python script to backup/restore the docker containers / volumes.

The idea :
- backup will backup the metadata from a container and its volumes
- restore will recreate a container from the saved metadata and restore its volumes

####Requires Python && Docker-py python package.

```
apt-get install python-pip 
pip install docker-py texttable
```


##How to use
Running backuper.py with -h will produce :
```
usage: backuper.py [-h] {list,backup,restore} ...

backup/restore/list a container and its volumes

positional arguments:
  {list,backup,restore}
                        sub-command help :
    list                Lists the volumes of the container
    backup              Backups a container to a tar file
    restore             Restore a container from tar backup

optional arguments:
  -h, --help            show this help message and exit
```

You can then get help for the sub commands via 
```
./backuper.py <subcommand> -h
```

Help for *backup* :
```
usage: backuper.py backup [-h] [-p] [-i INCLUDEVOLUMES]
                          [-s Absolute_Storage_Path]
                          container

positional arguments:
  container             Name of the container

optional arguments:
  -h, --help            show this help message and exit
  -p, --pausecontainer  Should we stop the source container before
                        extracting/saving its volumes and restart it after
                        backup (useful for files to be closed prior the
                        backup)if docker is >=1.3, the pause/unpause system
                        will be usedif docker is <1.3, a stop/restart command
                        will be used (breaking links)
  -i INCLUDEVOLUMES, --includevolumes INCLUDEVOLUMES
                        include volumes in backup (without this option only
                        backups in /var/lib/docker/vfs on host are backed up.
                        The syntax is a string of elements that will be
                        matched against all volumes/bindings. Elements are
                        seperated by a coma ', ' and can be regex
  -s Absolute_Storage_Path, --storage Absolute_Storage_Path
                        where to store/restore data, defaults to current path
                        (for BACKUP running inside a container, this parameter
                        isn't used)
```

Help for *list* :
```
$ ./backuper.py list -h
usage: backuper.py list [-h] container

positional arguments:
  container   Name of the container

optional arguments:
  -h, --help  show this help message and exit
```

Help for *restore* :
```
$ ./backuper.py restore -h

usage: backuper.py restore [-h] [-d destcontainername]
                           [-s Absolute_Storage_Path] [-r]
                           container

positional arguments:
  container             Name of the container

optional arguments:
  -h, --help            show this help message and exit
  -d destcontainername, --destcontainer destcontainername
                        name of the restored container, defaults to source
                        container name
  -s Absolute_Storage_Path, --storage Absolute_Storage_Path
                        where to store/restore data, defaults to current path
                        (for BACKUP running inside a container, this parameter
                        isn't used)
  -r, --restoreinplace  if the backed up container had mounted (bound)
                        directories on host, should we restore these bindings
                        AND the data in it (overwriting data on host maybe)
```

### Natively on host, LIST :
```
./backuper.py list containername 
```
This command will list all the volumes/mount points/boindings of containername

### Natively on host, BACKUP :
```
./backuper.py backup containername --storage /tmp 
```
This command will save the metadata and volumes as a tar file named : `/tmp/containername.tar`


```
./backuper.py backup containername --storage /tmp --pausecontainer
```
This command will save the metadata and volumes as a tar file named : `/tmp/containername.tar`
Additionnaly, the source container will be stopped (check KNOWN BUGS below about pausing) before backup and restarted afterwards

### Natively on host, RESTORE :
```
./backuper.py restore containername --storage /tmp --destcontainer newone
```
This command will restore the container `containername` and its volumes as a new container named `newone` from the tar file named : `/tmp/containername.tar`


### Run as a Container:
First, you need to build it :
```
docker build -t docker-backuper .
```

Once done, can can backup using :
```
docker run -t -i --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --volumes-from <container>
  -v /tmp:/backup \
  acaranta/docker-backuper \
  backup <container> --pausecontainer
```
- The .tar backups will be stored in /backup ... which you can bind to any dir on your docker host.
- In this mode, the `--storage` option is ignored as the data will be stored in the bound directory `/backup`.
- The container's volumes to be backed up are mounted using the --volumes-from option
- if added, the option `--pausecontainer` will stop the container to backup, and restart it afterwards (see KNOWN BUGS below about pausing)

Then you can restore using :
```
 docker run -t -i --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v <TarStoragePath>:/backup \
  acaranta/docker-backuper \
  restore <container> --destname <newcontainer> --storage <TarStoragePath>
```
- The .tar backups will be Fetched in the argument passed as `--storage` and which also has to be bound using `-v` option to `/backup`. It works differently from the backup, because for the restore, a container is launched on the docker host with the data storage dir mounted directly in order to read the tar files, it therefore need the `/backup` binding AND the --storage argument both pointing towards the same path.
- the container will be restored under the name `<newcontainer>`


##FULL EXAMPLE
Let's imagine we want a mysql container and we inject some data :
```
$ docker run -p 3306:3306 -e MYSQL_ROOT_PASSWORD=pouet -v /var/mytest:/justanexample --name mysqlsrv -d mysql
$ #Wait a moment (few seconds) for mysql to be available ;)
$ mysql -h 127.0.0.1 -uroot -ppouet -e "create database mytestdb ;"
$ echo "CREATE TABLE myTable (id mediumint(8) unsigned NOT NULL auto_increment,naming varchar(255) default NULL,  phone varchar(100) default NULL,  PRIMARY KEY (id)) AUTO_INCREMENT=1;
INSERT INTO myTable (naming,phone) VALUES (\"Brittany Z. Casey\",\"03 38 23 30 49\"),(\"Brandon C. Brady\",\"04 31 19 78 68\"),(\"Celeste I. Fletcher\",\"08 05 11 34 95\"),(\"Jael X. Mueller\",\"04 02 92 34 51\"),(\"Jonah T. Short\",\"09 07 74 41 37\"),(\"Natalie P. Hayes\",\"06 95 60 81 42\"),(\"Idola T. Mason\",\"06 49 92 54 92\"),(\"Indigo D. Chase\",\"04 77 59 48 16\"),(\"David K. Craig\",\"02 98 39 69 02\"),(\"Byron K. Sanders\",\"01 07 76 41 74\");
INSERT INTO myTable (naming,phone) VALUES (\"Brody D. Fitzpatrick\",\"06 60 39 08 84\"),(\"Grady B. Kline\",\"01 11 62 76 30\"),(\"Tanek O. Nelson\",\"04 34 16 80 50\"),(\"Ralph N. Reeves\",\"06 68 22 14 15\"),(\"Finn F. Castro\",\"06 17 23 14 90\"),(\"Imelda Z. Kemp\",\"02 37 63 50 46\"),(\"Denise A. Mcguire\",\"08 16 40 59 90\"),(\"Kellie U. Pierce\",\"02 63 15 98 34\"),(\"Rhiannon P. Holman\",\"05 60 21 05 15\"),(\"Quail A. Copeland\",\"04 26 63 57 14\");
" | mysql -h 127.0.0.1 -uroot -ppouet mytestdb 
$ mysql -h 127.0.0.1 -uroot -ppouet mytestdb -e "select * from myTable"
```
Then we check what volumes can be backed up :
```
$ docker run -t -i --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  acaranta/docker-backuper \
  list mysqlsrv
Volumes on container mysqlsrv ...
+-------------------------------------------------------+-------------------------------------------------------+
|              Mount point (in container)               |               Bound to (on docker host)               |
+=======================================================+=======================================================+
| /justanexample                                        | /var/mytest                                           |
+-------------------------------------------------------+-------------------------------------------------------+
| /var/lib/mysql                                        | /var/lib/docker/vfs/dir/aad993c1c9dbb9d3e31a9e7c48a31 |
|                                                       | 6b88bc607e3416b57deaaf44ca5cd1c887a                   |
+-------------------------------------------------------+-------------------------------------------------------+
```
The result show that there are 2 volumes that can be backed up. 
One of them volume resides in docker's `/var/lib/docker/vfs/dir/` folder.
By default, launching a backup without specifying anything more would include this volume only.

However let's imagine we want both volumes included ... We would use the `--includevolumes` option :
- `--includevolumes "/justanexample,/var/lib/mysql"`
- `--includevolumes ".*"`
- `--includevolumes "justan,vfs"`
- `--includevolumes "exam,mytest"`
All of these would match both volumes !

Then we backup this container :
```
$ docker run -t -i --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --volumes-from mysqlsrv \
  -v /tmp:/backup \
  acaranta/docker-backuper \
  backup mysqlsrv --pausecontainer --includevolumes ".*"
```
We can remove completely the test container :
```
$ docker rm -f mysqlsrv
```
And restore from backup :
```
$ docker run -t -i --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /tmp:/backup \
  acaranta/docker-backuper \
  restore mysqlsrv --destcontainer mysqlnewsrv --storage /tmp
```
And retest :
```
$ mysql -h 127.0.0.1 -uroot -ppouet mytestdb -e "select * from myTable"
```

##IMPORTANT NOTES & KNOWN "BUGS"
###In Place restoring and bound volumes
if a container was launched with a boud volume, ie :
```
docker run -d  -v /srv/docker-external-volumes/registry:/mnt/registry \
	-e STORAGE_PATH=/mnt/registry/storage \
	-e SQLALCHEMY_INDEX_DATABASE=sqlite:////mnt/registry/db/dbreg.sqlite \
	-p 5000:5000 --name my_registry registry
```
(here `/srv/docker-external-volumes/registry` --> `/mnt/registry`)).
The restore will create a new volumes under `/var/lib/docker/vfs` unless option `--restoreinplace` is added.
In this case, the restore WILL take place in the bound path on host ... aka it will overwrite (it data is present) the contents of `/srv/docker-external-volumes/registry` !!!

###Docker UNIX Socket and not TCP socket
Why is the docker client access statically set to use the docker socket `/var/run/docker.sock` instead of gibing the choice to use either unix socket or TCP socket ?
That is not a mistake, that is a choice I made : to be clear the backup/restore NEEDS to access the docker host's filesystem.
You could in theory do that while using local tcp socket to the docker API ... but allowing this could generate (esay) mistake by running the backup/restore distantly ... while trying to work on local Filesystem ... and err ... BAM ! ;)
So until I find a better way, it should stay this way ;)

###Restarting the container during backup
If you use the `--pausecontainer` container option during backup, bear in mind that 
there are two ways it can behave :
- you are using Docker version <1.3 : the `--pausecontainer` option will *stop*/*restart* the container... Therefore containers linked to the backed up container will have to be recreated in order to regenerate links !!! Dynamic links are a strongly wished feature in docker (https://github.com/docker/docker/issues/3155). But for the time being, restart or stop/start breaks them. You have been warned ;)
- you are using Docker version >=1.3 : the `--pausecontainer` option will use the *pause*/*unpause* commands to hang the container, therefore not breaking links AFAIT(ested) ;)

##TODO
- add a way to nicely name the tar files ?
- add a way to timestamp the tar files and let the user choose different restore points ?
- Review all the metadata parameters that still needs to be restored (ie : ro or rw volumes)

##DISCLAIMER 
Please TEST your backup/restore procedure, your data, etc ... this is provided as-is and does not garantee anything ! ;)


## Sources
Based on the code from docker-volume-backup : https://github.com/paimpozhil/docker-volume-backup
