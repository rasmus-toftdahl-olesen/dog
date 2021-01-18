# dog

[![test Status](https://github.com/rasmus-toftdahl-olesen/dog/workflows/test/badge.svg)](https://github.com/rasmus-toftdahl-olesen/dog/actions?query=workflow%3Atest)
[![centos-for-dog](https://github.com/rasmus-toftdahl-olesen/dog/workflows/centos-for-dog/badge.svg)](https://github.com/rasmus-toftdahl-olesen/dog/actions?query=workflow%3Acentos-for-dog)
[![package Status](https://github.com/rasmus-toftdahl-olesen/dog/workflows/package/badge.svg)](https://github.com/rasmus-toftdahl-olesen/dog/actions?query=workflow%3Apackage)
[![Available from PyPI](https://badgen.net/pypi/v/dog)](https://pypi.org/project/dog/)
[![Licensed under the Unlicense License](https://badgen.net/pypi/license/dog)](https://unlicense.org/)

dog is a simple wrapper for docker run to make it simple to call tools residing inside docker containers.

The basic idea is that you just put "dog" in front of the command you normally call.

So if your normally use "make" to compile your code, then if your compiler tools
are stored inside a docker container you just do "dog make" instead - and dog
will mount you local workspace and run the correct docker container without the
developer noticing at all.

The docker container to use is defined in a file called dog.config which is
normally positioned in the root of your workspace and contains the name of the
docker image.


## Documentation

Usage, Configuration and how it works is [all available here](http://halfdans.net/dog/).


## Installation

Dog is a single file script that only require Python 3.5+ and does not use any 
modules outside the ones that ship with Python.

So basically you can just clone the repo and stick a symlink to dog.py in your PATH.

Dog is also available on pypi so you should also be able to simply do:

```
pip install dog

# Or

python -m pip install dog
``` 
To get going.


# Example

By default the docker image is fetched from the default docker registry (hub.docker.com),
for instance:

```
[dog]
full-image=gcc:7.5
```


Means that:

```
dog gcc main.c -o main

```

Will compile main.c using gcc 7.5.

## crossbuild-for-dog

You can see a more real-world example by looking at the [crossbuild-for-dog test image](https://hub.docker.com/repository/docker/rtol/crossbuild-for-dog) that extends the standard crossbuild docker image with a dog enabled entrypoint - which can then be used to compile ARM linux executables anywhere.

The source for crossbuild-for-dog is available in [tests/dockers/crossbuild-for-dog](tests/dockers/crossbuild-for-dog) and there is a pytest verifying it in [tests/test_crossbuild_for_dog.py](tests/test_crossbuild_for_dog.py).
