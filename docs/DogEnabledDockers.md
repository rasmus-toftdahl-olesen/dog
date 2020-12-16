dog is nothing more than a simple warapper around the ```docker run``` command, so dor the dog to do its magic it needs docker images that behave like dog expect them to.

The primary part being that the ENTRYPOINT of the docker image should use the DOG_* environment variables to "sudo" to the correct user.

What an dog-enabled ENTRYPOINT usually does is simple to add a user with the same id, username and group as the local user calling dog - and then sudo'ing to that user so the files created will be owned by the local user instead of "root" or some other "docker run" user.

```
{% include_relative _config.yml %}
```

