# dog

[![test Status](https://github.com/rasmus-toftdahl-olesen/dog/workflows/test/badge.svg)](https://github.com/rasmus-toftdahl-olesen/sequanto-automation/actions?query=workflow%3Atest)
[![centos-for-dog](https://github.com/rasmus-toftdahl-olesen/dog/workflows/centos-for-dog/badge.svg)](https://github.com/rasmus-toftdahl-olesen/sequanto-automation/actions?query=workflow%3Acentos-for-dog)

dog is a simple wrapper for docker run to make it simple to call tools residing inside docker containers.

The basic idea is that you just put "dog" in front of the command you normally call.

So if your normally use "make" to compile your code, then if your compiler tools 
are stored inside a docker container you just do "dog make" instead - and dog 
will mount you local workspace and run the correct docker container without the 
developer noticing at all.

The docker container to use is defined in a file called dog.config which is 
normally positioned in the root of your workspace and contains the name of the 
docker image.

By default the docker image is fetched by the standard Oticon docker registry (GitLab),
for instance:

```
[dog]
full-image=gcc:7.5
```


Means that:

```
dog gcc main.c -o main

```

Will copmile main.c using gcc 7.5.
