Dog configuration files are simple .ini formatted files.

Configuration are read from two sources, the last one takes precedence:

1. ```.dog.config``` in the users HOME directory (HOMEPATH on Windows)
2. The first ```dog.config``` file found when traversing upwards to the root of the filesystem from the current directory, e.g. given the following directory structure:
   ```
   WORKSPACE_ROOT/
       tests/
          test1.py
          dog.config
       src/
          Makefile
          main.c
       README.md
       dog.config
   ```
   Running dog in the ```WORKSPACE_ROOT/``` directory will use the ```dog.config``` in that directory, running dog in the ```src/``` directory will also use the ```dog.config``` in the ```WORKSPACE_ROOT/``` directory (since it is the first ```dog.config``` when following the parent directories all the way to the file-system root).
   Running dog in the ```tests/``` directory will use the ```dog.config``` in that directory.
   This setup allows a project to use different docker images for different parts of the project, e.g. one docker image for compiling and another one for integration testing.
   
   
