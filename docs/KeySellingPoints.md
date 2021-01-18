
## Key selling points

Also known as the three reasons for using dog.

### 1. Versioning your tools

By putting the docker your project uses to compile in a dog.config file inside the projects repo, the version of the tools to use is now versioned along with the project itself.

This means that you are able to reproduce (and bug-fix) on a 10 year old project, because the dog.config on your release tag/branch will point to the build tools as they looked 10 years ago, and by the "magic" of docker they will still work the same way they did 10 years ago.

It also makes it easier when the tools needs to be upgraded, you can work on a feature branch to get the tools and project build scripts working and then merge both tools and build scripts to master when they are ready.

Experimenting with your tools without breaking anything also becomes much easier when you do not have to modify a machine, but can just modify a Dockerfile.


### 2. Making developers happy

Installing tools is never fun, or at least, as a developer you would like your build to "just work" on the developers machine without a lot of work.

By putting the build tools inside a docker image you can suddenly compile your project anywhere, so the developer can decide to use the Linux distro (or even Windows or Mac) that they like, and use the editor of their choice - compilation will be the same on all systems since the build tools are contained and versioned inside the docker image.


### 3. Avoiding the permission issues that arises from using docker for containing tools

Dog is simply a wrapper around "docker run" but with some sane default like mounting the current project inside the docker since that is where you would normally want the build tools to look.

But docker run will run as "root" by default inside the docker, or any other "default user" that has been set up for that particular docker image.

This is problematic since the output of your build will then suddenly be owned by whichever user is running inside the docker, making life difficult for the developer.

To solve this, dog will set a few environment variables that the docker image entrypoint can then use to "sudo" to the correct user and execute the build as the same user that just called dog.

In essence it just makes it simpler to use docker image containing your build tools.

```
D9.12 kbnuxaes01 [/scratch]
$ id
uid=4548(rtol) gid=1000(oticon) groups=1000(oticon),44(video),1007(docker)
D9.12 kbnuxaes01 [/scratch]
$ dog touch demo.txt
D9.12 kbnuxaes01 [/scratch]
$ ls -l demo.txt
-rw-r--r-- 1 rtol oticon 0 Oct  2 21:55 demo.txt
```
