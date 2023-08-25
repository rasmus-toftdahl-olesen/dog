# Configuration

## Table of contents
1. [Effective configuration](#effective-configuration)
   1. [Example](#example)
2. [Value interpolation](#value-interpolation)
3. [Sections of `dog.config`](#sections-of-dogconfig)
   1. [The `[dog]` section](#the-dog-section)
   2. [The `[ports]` section](#the-ports-section)
   3. [The `[volumes]` section](#the-volumes-section)
   4. [The `[volumes-from]` section](#the-volumes-from-section)
   5. [The `[usb-devices]` section](#the-usb-devices-section)

## Effective configuration
The container that `dog` runs its given command in is spun up based on the contents of one or more [INI-formatted](https://en.wikipedia.org/wiki/INI_file) `dog.config` files.
The effective configuration is the union of entries from the following sources, with entries from former sources taking precedence:
  1. Command-line arguments.
  2. `dog.config` in the current working directory or closest parent directory with such file.
  3. `dog.config` in the user's home directory (if present).
  4. Default values.

A `dog.config` can furthermore declare a parent `dog.config` that it is based on, meaning source (2) and (3) themselves are unions of configurations;
see the `include-dog-config` entry under [the `[dog]` section](#the-dog-section).

### Example
As an example, consider the following directory structure:
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
* Running `dog` in the `WORKSPACE_ROOT/` directory will use the `dog.config` in that directory.
* Running `dog` in the `src/` directory will also use the `dog.config` in the ``WORKSPACE_ROOT/`` directory. This is because it is the first `dog.config` file when following the parent directories all the way to the file system root.
* Running `dog` in the `tests/` directory will use the `dog.config` in that directory.

The setup allows a project to use different Docker images for different parts of the project, e.g. one Docker image for compiling and another one for integration testing.

## Value interpolation

`dog` recognizes the syntax `${<section>_<key>}` as a reference to a configuration entry and substitutes such construct with its resolved configuration value.
This is done in both configuration keys and string-based values.
References without a `<section>_` identifier identifies an entry under the `[dog]` section.

As an example, consider the following configuration entry:

```
full-image = ${docker-registry-url}/build-docker:${tools_build-docker-version}
```

Here `${docker-registry-url}` references the `docker-registry-url` entry under `[dog]`, and `${tools_build-docker-version}` references the `build-docker-version` entry under some custom `[tools]` section.

In addition to configuration values, certain constants may also be interpolated:

| Key               | Description
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dog-config-path` | Parent directory of the precedent `dog.config` file, usually the file mentioned as (2) in [Effective configuration](#effective-configuration). See also the `dog-config-path-resolve-symlink` entry under [the `[dog]` section](#the-dog-section). |
| `version`         | Version number of `dog`.                                                                                                                                                                                                                           |

Value interpolation is done after the effective configuration has been built.\
It thus does not work with the `include-dog-config` entry mentioned under [Effective configuration](#effective-configuration).

## Sections of `dog.config`

A `dog.config` file can contain multiple sections to organize configuration entries.
The sections
   * [`[dog]`](#the-dog-section)
   * [`[ports]`](#the-ports-section)
   * [`[volumes]`](#the-volumes-section)
   * [`[volumes-from]`](#the-volumes-from-section)
   * [`[usb-devices]`](#the-usb-devices-section)

are however given special treatment by `dog`, as documented below.

## The `[dog]` section

The `[dog]` section contains core `dog` configuration. These include:

| Key                               | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Default value                                                                                                                      |
|-----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `additional-docker-run-params`    | `dog` will pass these additional arguments when executing `docker run`.                                                                                                                                                                                                                                                                                                                                                                                                  | None                                                                                                                              |
| `as-root`                         | Should `dog` run its command as root inside the Docker container? The Docker image entrypoint is responsible for setting this up.                                                                                                                                                                                                                                                                                                                                        | `false`                                                                                                                           |
| `auto-mount`                      | Should `dog` mount the current working directory host volume inside the Docker container?                                                                                                                                                                                                                                                                                                                                                                                | `true`                                                                                                                            |
| `auto-run-volumes-from`           | Should `dog` spin up containers for the volume images configured in the `[volumes-from]` section? If `false` it is assumed that containers by the configured names already are running.                                                                                                                                                                                                                                                                                  | `true`                                                                                                                            |
| `cwd`                             | `dog` will run its command inside the Docker container with this directory set as the current working directory. <br><br> The Docker image entrypoint is responsible for setting this up.                                                                                                                                                                                                                                                                                | The current working directory of `dog`, outside the container. Assumes `auto-mount = true`.                                       |
| `device`                          | A comma-separated list of host devices, which `dog` will make available to the Docker container. See also the documentation for [the `[usb-devices]` section](#the-usb-devices-section).                                                                                                                                                                                                                                                                                 | None                                                                                                                              |
| `docker-minimum-version`          | When sanity-checking is performed, `dog` will abort if the installed Docker (or Podman) version is lower than this value.                                                                                                                                                                                                                                                                                                                                                | None                                                                                                                              |
| `dog-config-file-version`         | The version number of the `dog.config` format used. This document describes the `dog-config-file-version = 2` format, the latest.                                                                                                                                                                                                                                                                                                                                        | None                                                                                                                              |
| `dog-config-path-resolve-symlink` | Should the `dog-config-path` constant be based on a "resolved" `dog.config` file path? If `true`, the precedent `dog.config` file path will be made absolute with all symlink indirections resolved.                                                                                                                                                                                                                                                                     | `false`                                                                                                                           |
| `exposed-dog-variables`           | A comma-separated list of `dog` configuration entries to make available as environment variables to the entry point of the Docker container. Entries are identified by the scheme `<section>_<key>` as documented under the [Value interpolation](#value-interpolation) section. The exposed environment variables will prefixed with `DOG_`, will be uppercased, and hyphens (`-`) will be replaced with underscores (`_`), e.g. `DOG_AS_ROOT` for the `as-root` entry. | `uid, gid, user, group, home, as-root, version`                                                                                   |
| `full-image`                      | `dog` will run its command inside a container spun up from this fully qualified Docker image. See also `image` to specify the image without a registry.                                                                                                                                                                                                                                                                                                                  | [`registry` `/`] `image`                                                                                                          |
| `gid`                             | `dog` will run its command inside the Docker container as a user in a group with this group identifier. <br><br> The Docker image entrypoint is responsible for setting this up.                                                                                                                                                                                                                                                                                         | The identifier of the real group assigned to the `dog` process, outside the container, if applicable; otherwise `1000` (Windows). |
| `group`                           | `dog` will run its command inside the Docker container as a user in a group with this group name. <br><br> The Docker image entrypoint is responsible for setting this up.                                                                                                                                                                                                                                                                                               | The name of the real group assigned to the `dog` process, outside the container, if applicable; otherwise `nogroup` (Windows).    |
| `home`                            | `dog` will run its command inside the Docker container as a user with this directory as its home. <br><br> The Docker image entrypoint is responsible for setting this up.                                                                                                                                                                                                                                                                                               | `/home/$USERNAME` (Windows), `$HOME`, or `/home/nobody`, based on host environment variables.                                     |
| `hostname`                        | `dog` will assign this to be the hostname of the spun-up Docker container.                                                                                                                                                                                                                                                                                                                                                                                               | Hostname of the host, or `dog_docker`.                                                                                            |
| `image`                           | This entry can be used to configure `full-image`, denoting the Docker image to spin up. See also the `registry` entry.                                                                                                                                                                                                                                                                                                                                                   | None                                                                                                                              |
| `include-dog-config`              | Path to a `dog.config` file, relative to the parent directory of the declaring `dog.config` file. Denotes that the declaring `dog.config` file inherits configuration entries from the specified file. Its effective configuration is thus the set of the two configuration files, with the entries of the declaring file taking precedence.                                                                                                                             | None                                                                                                                              |
| `init`                            | Should `dog` pass `--init` to `docker run`?                                                                                                                                                                                                                                                                                                                                                                                                                              | `true`                                                                                                                            |
| `interactive`                     | Should `dog` pass `--interactive` to `docker run`, attaching the host STDIN to the command process spawned inside the container?                                                                                                                                                                                                                                                                                                                                         | `true`                                                                                                                            |
| `minimum-version`                 | `dog` will abort if its version is lower than this.                                                                                                                                                                                                                                                                                                                                                                                                                      | None                                                                                                                              |
| `network`                         | `dog` will connect the spun-up Docker container to this network.                                                                                                                                                                                                                                                                                                                                                                                                         | None                                                                                                                              |
| `pull`                            | Should `dog` always pull the latest version of the Docker image before use?                                                                                                                                                                                                                                                                                                                                                                                              | `false`                                                                                                                           |
| `registry`                        | This entry can be used to configure `full-image`, denoting which registry `image` should be pulled from.                                                                                                                                                                                                                                                                                                                                                                 | None (interpreted as the Docker Hub)                                                                                              |
| `sanity-check-always`             | Should `dog` perform sanity-checks before running? This performs the same checks as `dog --sanity-check` but is not mutally exclusive to running commands.                                                                                                                                                                                                                                                                                                               | `false`                                                                                                                           |
| `sudo-outside-docker`             | Should `dog` run commands outside its container as root? Affected commands include `docker run` and `docker pull`.                                                                                                                                                                                                                                                                                                                                                       | `false`                                                                                                                           |
| `terminal`                        | Should `dog` allocate a pseudo-terminal (TTY) to its container process?                                                                                                                                                                                                                                                                                                                                                                                                  | `false`                                                                                                                           |
| `uid`                             | `dog` will run its command inside the Docker container as a user with this identifier. <br><br> The Docker image entrypoint is responsible for setting this up.                                                                                                                                                                                                                                                                                                          | The identifier of the real user assigned to the `dog` process, outside the container, if applicable; otherwise `1000` (Windows).  |
| `use-podman`                      | Should `dog` use `podman` instead of `docker` for all Docker commands?                                                                                                                                                                                                                                                                                                                                                                                                   | `false`                                                                                                                           |
| `user`                            | `dog` will run its command inside the Docker container as a user with this name. <br><br> The Docker image entrypoint is responsible for setting this up.                                                                                                                                                                                                                                                                                                                | The name of the real user assigned to the `dog` process, outside the container, if applicable; otherwise `nobody` (Windows).      |
| `user-env-vars`                   | `dog` will expose these host environment variables to the Docker entrypoint, aborting if any of them are not set.                                                                                                                                                                                                                                                                                                                                                        | None                                                                                                                              |
| `user-env-vars-if-set`            | `dog` will expose these host environment variables to the Docker entrypoint, ignoring any that are not set.                                                                                                                                                                                                                                                                                                                                                              | None                                                                                                                              |
| `verbose`                         | Should `dog` be verbose with its output? This option is most often passed as a command-line argument to `dog`, e.g. `dog --verbose`.                                                                                                                                                                                                                                                                                                                                     | `false`                                                                                                                           |
| `volumes-from-silent`             | Should `dog` be quiet when creating containers from `[volumes-from]` images? Assumes `auto-run-volumes-from = true`.                                                                                                                                                                                                                                                                                                                                                     | `false`                                                                                                                           |

## The `[ports]` section

The `[ports]` section is interpreted by `dog` as a list of container ports to publish to host ports.
The general syntax for each entry is:

```
<inside> = <outside>
```

* `<outside>` identifies the host port to forward traffic from/to.
* `<inside>` identifies the container port to expose.

Example:

```
[ports]
80 = localhost:8080
```

## The `[volumes]` section

The `[volumes]` section is interpreted by `dog` as a list of directories to be mounted as volumes inside the Docker container.
Under `dog-config-file-version = 2` the general syntax for each entry is:

```
<label>[?] = <outside>:<inside>[:ro]
```

* `<outside>` identifies the host directory to be mounted. It may start with `~` to denote a path relative to the user's home directory.
* `<inside>` identifies the mount point within the container. If `<inside>` is followed by `:ro` the mounted volume will be read-only.
* `<label>` can be anything but must be unique; use it as a mmemonic for humans.
* If the `<label>` is followed by a `?`, the mounting will be skipped if `<outside>` does not exist.

Example:

```
[volumes]
ssh = ~/.ssh:${home}/.ssh:ro
```

## The `[volumes-from]` section

The `[volumes-from]` section lists Docker images whose volumes should be mounted by `dog` inside the Docker container.
The syntax for each entry is:

```
<name>[:ro] = <image>
```

* `<name>` is the name of the container to start the corresponding `<image>` as. If `<name>` is followed by `:ro` the mounted volumes will be read-only.
* `<image>` identifies the Docker image whose volumes to mount; see the documentation for [`docker pull`](https://docs.docker.com/engine/reference/commandline/pull/).

Example:

```
[volumes-from]
jdk-vol-installer-1.8.0_202.1:ro = ${registry}/jdk-installer:1.8.0_202.1
```

## The `[usb-devices]` section

The `[usb-devices]` section is interpreted as a list of host USB devices to make available to the Docker container by `dog`, identified by USB vendor and product IDs.
This feature is currently unsupported for Windows. The general syntax for each entry is:

```
<label> = <vendor>:<product>
```

* `<label>` can be anything but must be unique; use it as a mmemonic for humans.
* `<vendor>` the vendor identifier of the USB device.
* `<product>` the product identifier of the USB device.

Each entry may match multiple USB devices, and all matched devices are made available to the Docker container.

Example:

```
[usb-devices]
hipro = 0c33:0012
```
