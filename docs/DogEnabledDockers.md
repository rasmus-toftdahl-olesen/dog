dog is nothing more than a simple warapper around the ```docker run``` command, so dor the dog to do its magic it needs docker images that behave like dog expect them to.

The primary part being that the ENTRYPOINT of the docker image should use the DOG_* environment variables to "sudo" to the correct user.

What an dog-enabled ENTRYPOINT usually does is simple to add a user with the same id, username and group as the local user calling dog - and then sudo'ing to that user so the files created will be owned by the local user instead of "root" or some other "docker run" user.

Let us take a look at the example [centos-for-dog image](https://hub.docker.com/r/rtol/centos-for-dog) that is a dog-enabled version of the standard CentOS docker image.

The Dockerfile looks relative straight-forward, all it does is install the sudo package and set up an ENTRYPOINT:
https://github.com/rasmus-toftdahl-olesen/dog/blob/master/tests/dockers/centos-for-dog/Dockerfile

```
FROM centos:7.5.1804
LABEL maintainer=KBN_Project_Team_Continuous@dgs.com
RUN yum install -y sudo

ADD entrypoint.sh /
RUN chmod a+x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

The entrypoint.sh is just a simple shell-script which will "sudo" to the correct user when the docker image is called using dog:
https://github.com/rasmus-toftdahl-olesen/dog/blob/master/tests/dockers/centos-for-dog/entrypoint.sh

```
#!/bin/bash

if [[ ! -d $DOG_HOME ]]; then
    mkdir -p $DOG_HOME
fi

if ! grep -q "$DOG_GROUP:x:$DOG_GID" /etc/group; then
    groupadd -g $DOG_GID $DOG_GROUP
fi
useradd -u $DOG_UID -g $DOG_GID -c Self -d $DOG_HOME -s /bin/bash -M -N $DOG_USER
chown $DOG_UID:$DOG_GID $DOG_HOME
if [[ $DOG_AS_ROOT == "True" ]]; then
    exec "$@"
else
    args="$@"
    exec /usr/bin/sudo -u $DOG_USER --preserve-env=$DOG_PRESERVE_ENV -- /bin/bash -c "$args"
fi
```


