#!/bin/sh

if [[ ! -d $DOG_HOME ]]; then
    mkdir -p $DOG_HOME
fi

if ! grep -q "$DOG_GROUP:x:$DOG_GID" /etc/group; then
    addgroup -g $DOG_GID $DOG_GROUP
fi
adduser -u $DOG_UID -G $DOG_GROUP -g Self -h $DOG_HOME -s /bin/sh -H -D $DOG_USER
chown $DOG_UID:$DOG_GID $DOG_HOME
if [[ $DOG_AS_ROOT = "True" ]]; then
    exec "$@"
else
    args="$@"
    exec /usr/bin/sudo -u $DOG_USER --preserve-env=PATH,P4PORT,P4USER -- /bin/sh -c "$args"
fi
