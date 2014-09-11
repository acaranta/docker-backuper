FROM ubuntu:14.04
MAINTAINER Arthur Caranta <arthur@caranta.com>

RUN apt-get update
RUN apt-get -y install python-pip
RUN pip install docker-py texttable

ADD backuper.py /backuper.py
WORKDIR /

ENTRYPOINT ["python",  "/backuper.py" ]
