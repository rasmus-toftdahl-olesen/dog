#!/bin/bash

if [[ ! -d $DOG_HOME ]]; then
    mkdir -p $DOG_HOME
fi

if ! grep "$DOG_GROUP:x:$DOG_GID" /etc/group; then
    groupadd -g $DOG_GID $DOG_GROUP
fi
useradd -u $DOG_UID -g $DOG_GID -c Self -d $DOG_HOME -s /bin/bash -M -N $DOG_USER
chown $DOG_UID:$DOG_GID $DOG_HOME
if [[ $DOG_AS_ROOT = "True" ]]; then
    exec "$@"
else
    args="$@"
    exec /usr/bin/sudo -u $DOG_USER --preserve-env=PATH,P4PORT,P4USER -- /bin/bash -c "LANG=en_US.UTF-8 $args"
fi
