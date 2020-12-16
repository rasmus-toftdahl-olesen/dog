# Tutorial

This is a simple tutorial on how to work with dog - a simple way to get started by playing with dog.

## Installation of dog

The simplest way to install dog is by pip-installing it:

```
$ pip install dog
```

You should now be able to say:
```
$ dog --version
dog version 8
```

## Creating an example project

To try out dog, create a random folder somewhere on your disk.

```
$ mkdir dog_test
$ cd dog_test
```

Create a dog.config file telling dog to use the centos-for-dog image when running commands using dog inside this folder.

```
$ echo [dog] >> dog.config
$ echo image=rtol/centos-for-dog >> dog.config
$ cat dog.config
[dog]
image=rtol/centos-for-dog
```

You should now be able to start calling dog to use commands and tools inside the centos-for-dog image:

```
$ dog wc dog.config
 2  2 36 dog.config
```

Notice that dog by default mounts your projects' workspace root and sets the current directory to the directory you are currently in.

So if we create a sub-directory and run a command, the current directory when running a command using dog will also change:

```
$ mkdir subdir
$ cd subdir
$ touch file_in_subdir.txt
$ dog ls
file_in_subdir.txt
```

Hopefully that short tutorial has showed how to get started using dog - the idea is that you put your dog.config in your git repo so you can start versioning the tools inside the docker along with the code which is using them.



