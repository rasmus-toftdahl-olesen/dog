#!/usr/bin/env python3

import argparse
import configparser
import copy
import os
import platform
import pprint
import re
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import List, Deque, Dict, Tuple, Union

# Version of dog
DOG_VERSION = 15
MAX_DOG_CONFIG_VERSION = 2

# Constants for consistent naming of dog variables, etc.
ADDITIONAL_DOCKER_RUN_PARAMS = 'additional-docker-run-params'
ARGS = 'args'
AS_ROOT = 'as-root'
AUTO_MOUNT = 'auto-mount'
AUTO_RUN_VOLUMES_FROM = 'auto-run-volumes-from'
CONFIG_FILE = 'dog.config'
CWD = 'cwd'
DEVICE = 'device'
DOCKER = 'docker'
DOCKER_COMPOSE = 'docker-compose'
DOCKER_COMPOSE_FILE = 'docker-compose-file'
DOCKER_COMPOSE_MINIMUM_VERSION = 'docker-compose-minimum-version'
DOCKER_COMPOSE_SERVICE = 'docker-compose-service'
DOCKER_MINIMUM_VERSION = 'docker-minimum-version'
DOG = 'dog'
DOG_CONFIG_FILE_VERSION = 'dog-config-file-version'
DOG_CONFIG_PATH = 'dog-config-path'
DOG_CONFIG_PATH_RESOLVE_SYMLINK = 'dog-config-path-resolve-symlink'
EXPOSED_DOG_VARIABLES = 'exposed-dog-variables'
FULL_IMAGE = 'full-image'
GID = 'gid'
GROUP = 'group'
HOME = 'home'
HOSTNAME = 'hostname'
IMAGE = 'image'
INIT = 'init'
INCLUDE_DOG_CONFIG = 'include-dog-config'
INTERACTIVE = 'interactive'
MINIMUM_VERSION = 'minimum-version'
NETWORK = 'network'
PODMAN = 'podman'
PORTS = 'ports'
PULL = 'pull'
REGISTRY = 'registry'
SANITY_CHECK = 'sanity-check'
SANITY_CHECK_ALWAYS = 'sanity-check-always'
SUDO = 'sudo'
SUDO_OUTSIDE_DOCKER = 'sudo-outside-docker'
TERMINAL = 'terminal'
UID = 'uid'
USB_DEVICES = 'usb-devices'
USER = 'user'
USER_ENV_VARS = 'user-env-vars'
USER_ENV_VARS_IF_SET = 'user-env-vars-if-set'
USE_PODMAN = 'use-podman'
VERBOSE = 'verbose'
VERSION = 'version'
VOLUMES = 'volumes'
VOLUMES_FROM = 'volumes-from'
VOLUMES_FROM_SILENT = 'volumes-from-silent'
WIN32_CWD = 'win32-cwd'

DOG_CONFIG_SECTIONS = [DOG, USB_DEVICES, VOLUMES, VOLUMES_FROM]
SUBST_NAME_RE = re.compile(r'\${([^}]+)}')

DogConfig = Dict[str, Union[str, int, bool, Path, List[str], Dict[str, str]]]

DEFAULT_CONFIG = {
    ADDITIONAL_DOCKER_RUN_PARAMS: '',
    ARGS: ['id'],
    AS_ROOT: False,
    AUTO_MOUNT: True,
    AUTO_RUN_VOLUMES_FROM: True,
    CWD: '/home/nobody',
    EXPOSED_DOG_VARIABLES: [UID, GID, USER, GROUP, HOME, AS_ROOT, VERSION],
    GID: 1000,
    GROUP: 'nogroup',
    HOME: '/home/nobody',
    HOSTNAME: 'dog_docker',
    INIT: True,
    INTERACTIVE: True,
    PORTS: {},
    PULL: False,
    SANITY_CHECK_ALWAYS: False,
    SUDO_OUTSIDE_DOCKER: False,
    TERMINAL: False,
    UID: 1000,
    USB_DEVICES: {},
    USER: 'nobody',
    USER_ENV_VARS: {},
    USER_ENV_VARS_IF_SET: {},
    USE_PODMAN: False,
    VERBOSE: False,
    VERSION: DOG_VERSION,
    VOLUMES: {},
    VOLUMES_FROM: {},
    VOLUMES_FROM_SILENT: False,
}


class UsbDevices:
    def __init__(self):
        self.devs = {}
        self._subdev_re = re.compile(r'^[0-9]+-[0-9]+(\.[0-9]+)*$')
        self._find_devices()

    def get_bus_paths(self, vendor_product):
        devices = self.devs.get(vendor_product, None)
        if not devices:
            return []
        return ['/dev/bus/usb/{0:03}/{1:03}'.format(dev[0], dev[1]) for dev in devices]

    def _find_devices(self):
        for p in Path('/sys/bus/usb/devices').glob('usb*'):
            self._add_device(p)

    def _add_device(self, p):
        busnum = self.read_info(p / 'busnum')
        devnum = self.read_info(p / 'devnum')
        vendor = self.read_info(p / 'idVendor')
        product = self.read_info(p / 'idProduct')
        if busnum and devnum and vendor and product:
            key = '{}:{}'.format(vendor, product)
            try:
                dev_list = self.devs[key]
            except KeyError:
                dev_list = []
                self.devs[key] = dev_list
            dev_list.append((int(busnum), int(devnum)))
        for t in p.glob('{}-*'.format(busnum)):
            m = self._subdev_re.match(str(t.name))
            if m:
                self._add_device(p / m[0])

    @staticmethod
    def read_info(path):
        if not path.exists():
            return ''
        return path.read_text().rstrip()


def log_verbose(config: DogConfig, txt: str):
    if config[VERBOSE]:
        print(txt)


def log_config(name: str, config: DogConfig, filename: Path = None):
    if filename:
        print('{} Config ({}):'.format(name, filename))
    else:
        print('{} Config:'.format(name))
    pprint.pprint(config, indent=4)


def log_config_from_files(name: str, config: Deque[Tuple[DogConfig, Path]]):
    for conf in config:
        log_config(name, conf[0], conf[1])


def fatal_error(text: str, error_code: int = -1):
    print('ERROR[dog]: {}'.format(text), file=sys.stderr)
    sys.exit(error_code)


def find_dog_config() -> Path:
    cur = Path.cwd() / CONFIG_FILE
    for parent in cur.parents:
        dog_config = parent / CONFIG_FILE
        if os.path.isfile(str(dog_config)):
            return dog_config

    fatal_error(
        'Could not find {} in current directory or on of its parents'.format(
            CONFIG_FILE
        )
    )


def list_from_config_entry(entry: str) -> List[str]:
    var_list = entry.split(',')
    return [s.strip() for s in var_list]


def get_user_env_vars(
    config_user_env_vars: str, allow_empty: bool
) -> Dict[str, Union[str, List[str]]]:
    env_var_list = list_from_config_entry(config_user_env_vars)
    user_env_vars = {}
    for env_var in env_var_list:
        value = os.getenv(env_var)
        if value is not None:
            user_env_vars[env_var] = value
        elif not allow_empty:
            fatal_error(
                (
                    '{} was specified in {} but was not set in the current shell'
                    ' environment'
                ).format(env_var, USER_ENV_VARS)
            )
    return user_env_vars


def parse_volumes_v1(volumes):
    """Translate $home in v1 format to ${home} in v2 format,
    so general subst can be used.
    """
    for key in list(volumes.keys()):
        if '$home' in key:
            if key[0] == '$':
                new_key = '${{home}}{}'.format(key[5:])
            else:
                new_key = '?${{home}}{}'.format(key[6:])
            volumes[new_key] = volumes[key]
            del volumes[key]
    return volumes


def parse_volumes_v2(volumes):
    res = {}
    for key, vol in volumes.items():
        outside, *inside = vol.split(':')
        if isinstance(inside, list):
            inside = ':'.join(inside)
        if not inside:
            fatal_error(
                (
                    '"{}={}" found in volumes section has unknown format.'
                    ' Did you use dog.config v1 format in a v2 file?'
                ).format(key, vol)
            )
        if key[-1] == '?':
            inside = '?' + inside
        res[inside] = outside
    return res


volumes_parser = [parse_volumes_v1, parse_volumes_v2]


def get_config_file_version(dog_config):
    if MINIMUM_VERSION in dog_config:
        minimum_version = int(dog_config[MINIMUM_VERSION])
        if DOG_VERSION < minimum_version:
            fatal_error(
                (
                    'Minimum version required ({}) is greater than your dog version'
                    ' ({}) - please upgrade dog'
                ).format(minimum_version, DOG_VERSION)
            )
    dog_config_file_version = dog_config.get(DOG_CONFIG_FILE_VERSION, None)
    if dog_config_file_version is None:
        fatal_error(
            'Do not know how to handle a dog.config file without {} specified'.format(
                DOG_CONFIG_FILE_VERSION
            )
        )
    dog_config_file_version = int(dog_config_file_version)
    dog_config[DOG_CONFIG_FILE_VERSION] = dog_config_file_version
    if dog_config_file_version < 1 or dog_config_file_version > MAX_DOG_CONFIG_VERSION:
        fatal_error(
            (
                'Do not know how to interpret a dog.config file with version {}'
                ' (max file version supported: {})'
            ).format(dog_config_file_version, MAX_DOG_CONFIG_VERSION)
        )
    return dog_config_file_version


def set_dog_config_path(dog_config, dog_config_file):
    if dog_config.get(DOG_CONFIG_PATH_RESOLVE_SYMLINK, False):
        dog_config[DOG_CONFIG_PATH] = str(dog_config_file.resolve().parent)
    else:
        dog_config[DOG_CONFIG_PATH] = str(dog_config_file.parent)


def handle_booleans_in_config(config, dog_config):
    """Use DEFAULT_CONFIG to determine which values should be booleans."""
    for k, v in DEFAULT_CONFIG.items():
        if isinstance(v, bool) and k in config[DOG]:
            dog_config[k] = config[DOG].getboolean(k)


def handle_user_env_vars(dog_config):
    if USER_ENV_VARS in dog_config:
        dog_config[USER_ENV_VARS] = get_user_env_vars(
            dog_config[USER_ENV_VARS], allow_empty=False
        )
    if USER_ENV_VARS_IF_SET in dog_config:
        dog_config[USER_ENV_VARS_IF_SET] = get_user_env_vars(
            dog_config[USER_ENV_VARS_IF_SET], allow_empty=True
        )


def handle_dict_config_vars(config: configparser.ConfigParser, dog_config):
    for v in [PORTS, USB_DEVICES, VOLUMES_FROM]:
        if v in config:
            dog_config[v] = dict(config[v])


def handler_user_sections(config: configparser.ConfigParser, dog_config):
    for section in config.sections():
        if section in DOG_CONFIG_SECTIONS:
            continue
        conf_section = config[section]
        for key in conf_section:
            dog_config['{}_{}'.format(section, key)] = conf_section[key]


def read_config_file(dog_config_file: Path) -> DogConfig:
    config = configparser.ConfigParser(delimiters='=')
    with dog_config_file.open() as f:
        config.read_file(f)
    try:
        dog_config = dict(config[DOG])
    except KeyError:
        fatal_error('Could not find [dog] in {}'.format(dog_config_file))

    dog_config_file_version = get_config_file_version(dog_config)

    handle_booleans_in_config(config, dog_config)
    handle_user_env_vars(dog_config)
    handle_dict_config_vars(config, dog_config)
    handler_user_sections(config, dog_config)

    if EXPOSED_DOG_VARIABLES in dog_config:
        dog_config[EXPOSED_DOG_VARIABLES] = list_from_config_entry(
            dog_config[EXPOSED_DOG_VARIABLES]
        )
    if DEVICE in dog_config:
        dog_config[DEVICE] = list_from_config_entry(dog_config[DEVICE])
    if VOLUMES in config:
        dog_config[VOLUMES] = volumes_parser[dog_config_file_version - 1](
            dict(config[VOLUMES])
        )
    set_dog_config_path(dog_config, dog_config_file)
    return dog_config


def read_dog_config(dog_config_file: Path) -> Deque[Tuple[DogConfig, Path]]:
    res = deque()
    while True:
        try:
            conf = read_config_file(dog_config_file)
        except FileNotFoundError:
            fatal_error(
                'Could not find "{}" used in {} here: {}'.format(
                    dog_config_file.name, INCLUDE_DOG_CONFIG, dog_config_file
                )
            )
        res.appendleft((conf, dog_config_file))
        if INCLUDE_DOG_CONFIG not in conf:
            break
        dog_config_file = dog_config_file.parent / conf[INCLUDE_DOG_CONFIG]
        del conf[INCLUDE_DOG_CONFIG]
    return res


def parse_command_line_args(own_name: str, argv: list) -> DogConfig:
    parser = argparse.ArgumentParser(
        description='Docker run wrapper to make it easier to call commands.'
    )
    parser.add_argument(
        '--pull',
        dest=PULL,
        action='store_const',
        const=True,
        help='Pull the latest version of the docker image',
    )
    interactive_group = parser.add_mutually_exclusive_group()
    interactive_group.add_argument(
        '-i',
        '--interactive',
        dest=INTERACTIVE,
        action='store_const',
        const=True,
        help='Run interactive (keep stdin open)',
    )
    interactive_group.add_argument(
        '--not-interactive',
        dest=INTERACTIVE,
        action='store_const',
        const=False,
        help='Do not run interactive',
    )
    terminal_group = parser.add_mutually_exclusive_group()
    terminal_group.add_argument(
        '-t',
        '--terminal',
        dest=TERMINAL,
        action='store_const',
        const=True,
        help='Allocate a pseudo terminal',
    )
    terminal_group.add_argument(
        '--no-terminal',
        dest=TERMINAL,
        action='store_const',
        const=False,
        help='Do not allocate a pseudo terminal',
    )
    parser.add_argument(
        '--as-root',
        dest=AS_ROOT,
        action='store_const',
        const=True,
        help='Run as root inside the docker',
    )
    parser.add_argument(
        '--version', action=VERSION, version='dog version {}'.format(DOG_VERSION)
    )
    parser.add_argument(
        '--verbose',
        dest=VERBOSE,
        action='store_const',
        const=True,
        help='Provide more dog output (useful for debugging)',
    )
    sanity_check_group = parser.add_mutually_exclusive_group(required=True)
    sanity_check_group.add_argument(
        ARGS,
        type=str,
        nargs='*',
        default=[],
        help='Command to call inside docker (with arguments)',
    )
    sanity_check_group.add_argument(
        '--sanity-check',
        dest=SANITY_CHECK,
        action='store_const',
        const=True,
        help='Perform sanity check, i.e. is required docker-compose version available',
    )

    # Insert the needed -- to separate dog args with the rest of the commands
    # But only if the user did not do it himself
    if DOG not in own_name:
        argv.insert(0, own_name)
    if '--' not in argv:
        for index, arg in enumerate(argv):
            if arg[0] != '-':
                argv.insert(index, '--')
                break
    args = parser.parse_args(argv)
    config = vars(args)
    if config[PULL] is None:
        del config[PULL]
    if config[TERMINAL] is None:
        del config[TERMINAL]
    if config[INTERACTIVE] is None:
        del config[INTERACTIVE]
    if config[AS_ROOT] is None:
        del config[AS_ROOT]
    if config[VERBOSE] is None:
        del config[VERBOSE]
    return config


def win32_to_dog_unix(win_path: Path) -> str:
    """Convert a Windows path to what it will be inside dog (unix)."""
    return '/' + win_path.as_posix().replace(':', '')


def get_env_config() -> DogConfig:
    hostname = platform.node()
    if sys.platform == 'win32':
        cwd = Path.cwd()
        env_config = {
            UID: 1000,
            GID: 1000,
            HOSTNAME: hostname,
            GROUP: 'nodoggroup',
            CWD: win32_to_dog_unix(cwd),
            WIN32_CWD: cwd,
        }
        user = os.getenv('USERNAME')
        if user:
            env_config[HOME] = '/home/' + user
            env_config[USER] = user
        return env_config
    else:
        import grp

        uid = os.getuid()
        gid = os.getgid()
        group = grp.getgrgid(gid).gr_name
        cwd = Path.cwd()

        env_config = {UID: uid, GID: gid, HOSTNAME: hostname, GROUP: group, CWD: cwd}

        home_env = os.getenv('HOME')
        user_env = os.getenv('USER')
        if home_env:
            env_config[HOME] = home_env
        if user_env:
            env_config[USER] = user_env
        return env_config


def find_mount_point(p: Path):
    while not os.path.ismount(str(p)) and not str(p.parent) == p.root:
        p = p.parent
    return p


def docker_cmd(config: DogConfig) -> str:
    return PODMAN if config[USE_PODMAN] else DOCKER


def docker_pull(config: DogConfig):
    if DOCKER_COMPOSE_FILE in config:
        fatal_error('{} is not compatible with pull'.format(DOCKER_COMPOSE_FILE))
    try:
        args = [SUDO] if config[SUDO_OUTSIDE_DOCKER] else []
        args.append(docker_cmd(config))
        args += ['pull', config[FULL_IMAGE]]
        proc = subprocess.run(args)
        if proc.returncode != 0:
            print('ERROR {} while pulling:'.format(proc.returncode))
            print(proc.stdout)
            print(proc.stderr)
            sys.exit(proc.returncode)
    except KeyboardInterrupt:
        print('Dog received Ctrl+C')
        sys.exit(-1)


def generate_env_arg_list(config: DogConfig) -> List[str]:
    args = []
    for name in config[EXPOSED_DOG_VARIABLES]:
        env_name = name.upper().replace('-', '_')
        args.extend(['-e', 'DOG_{}={}'.format(env_name, config[name])])

    for env_name, value in config[USER_ENV_VARS].items():
        args.extend(['-e', '{}={}'.format(env_name, value)])
    for env_name, value in config[USER_ENV_VARS_IF_SET].items():
        args.extend(['-e', '{}={}'.format(env_name, value)])
    return args


def docker_container_names(config: DogConfig) -> List[str]:
    args = [docker_cmd(config), 'container', 'ls', '-a', '--format={{.Names}}']
    proc = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True
    )
    return proc.stdout.splitlines()


def docker_run_volumes_from(config: DogConfig):
    if not config[VOLUMES_FROM_SILENT]:
        container_names = docker_container_names(config)
        volumes_from_names = set(
            name.split(':')[0] for name in config[VOLUMES_FROM].keys()
        )
        missing_containers = volumes_from_names.difference(container_names)
        for name in missing_containers:
            print('Dog creating volumes_from container: {} ...'.format(name))

    cmd = docker_cmd(config)

    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run_volume_installer(name, image):

        proc = await asyncio.create_subprocess_exec(
            cmd,
            'run',
            '--network',
            'none',
            '--name',
            name,
            image,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return await proc.wait()

    async def run_all():
        tasks = [
            run_volume_installer(name.split(':')[0], image)
            for name, image in config[VOLUMES_FROM].items()
        ]
        await asyncio.gather(*tasks)

    loop.run_until_complete(run_all())
    loop.close()


def docker_run(config: DogConfig):
    args = []
    if config[SUDO_OUTSIDE_DOCKER]:
        args += [SUDO]
    args += [docker_cmd(config)]
    args += [
        'run',
        '--rm',
        '--hostname={}'.format(config[HOSTNAME]),
        '-w',
        str(config[CWD]),
    ]

    for inside, outside in config[VOLUMES].items():
        args += ['-v', outside + ':' + inside]

    for inside, outside in config[PORTS].items():
        args += ['-p', outside + ':' + inside]

    for container in config[VOLUMES_FROM].keys():
        args += ['--volumes-from', container]

    if config[INTERACTIVE]:
        args.append('-i')

    if config[INIT]:
        args.append('--init')

    if config[TERMINAL]:
        args.append('-t')

    if NETWORK in config:
        args.extend(['--network', config[NETWORK]])

    if DEVICE in config:
        for device in config[DEVICE]:
            args.append('--device={}'.format(device))

    env_args = generate_env_arg_list(config)
    args.extend(env_args)

    if config[ADDITIONAL_DOCKER_RUN_PARAMS]:
        args.extend(config[ADDITIONAL_DOCKER_RUN_PARAMS].split())

    args.append(config[FULL_IMAGE])
    args.extend(config[ARGS])

    log_verbose(config, ' '.join(args))
    if sys.platform != 'win32':
        sys.stdout.flush()
        sys.stderr.flush()
        os.execvp(args[0], args)
        return 0  # execvp does not return but this makes testing easier
    # Using execvp on Windows results in weird behavior,
    # so keep using a subprocess here
    try:
        proc = subprocess.run(args)
        return proc.returncode
    except KeyboardInterrupt:
        print('Dog received Ctrl+C')
        return -1


def docker_compose_run(config: DogConfig) -> int:
    assert config[INTERACTIVE], 'non-interactive mode not supported for docker-compose'

    args = ['sudo'] if config[SUDO_OUTSIDE_DOCKER] else []
    args.extend(
        [
            DOCKER_COMPOSE,
            '-f',
            str(Path(config[DOG_CONFIG_PATH]) / config[DOCKER_COMPOSE_FILE]),
        ]
    )
    cleanup_args = args.copy()
    if config[VERBOSE]:
        args += ['--verbose', '--log-level', 'DEBUG']
    args += ['run', '--rm', '-w', str(config[CWD])]
    cleanup_args += ['rm', '-f']

    if not config[TERMINAL]:
        args.append('-T')

    for inside, outside in config[VOLUMES].items():
        args += ['-v', outside + ':' + inside]

    for inside, outside in config[PORTS].items():
        args += ['-p', outside + ':' + inside]

    args.extend(generate_env_arg_list(config))

    args.append(config[DOCKER_COMPOSE_SERVICE])

    args.extend(config[ARGS])

    log_verbose(config, ' '.join(args))
    try:
        docker_compose_env = dict(os.environ)
        for name in config[EXPOSED_DOG_VARIABLES]:
            env_name = 'DOG_{}'.format(name.upper().replace('-', '_'))
            docker_compose_env[env_name] = str(config[name])
        proc = subprocess.run(args, env=docker_compose_env)
        stderr_out = None if config[VERBOSE] else subprocess.DEVNULL
        subprocess.run(cleanup_args, stdout=stderr_out, stderr=stderr_out)
        return proc.returncode
    except KeyboardInterrupt:
        print('Dog received Ctrl+C')
        return -1


def update_config(existing_config: DogConfig, new_config: DogConfig):
    """Merge two DogConfigs.

    All exiting keys in existing_config will be replaced with the keys in new_config
    - except for dictionaries, they will be merged with the existing dictionary.
    """
    for k, v in new_config.items():
        if k in existing_config and isinstance(v, dict):
            update_config(existing_config[k], new_config[k])
        else:
            existing_config[k] = copy.copy(new_config[k])


def update_config_from_files(
    existing_config: DogConfig, config_from_files: Deque[Tuple[DogConfig, Path]]
):
    for conf in config_from_files:
        update_config(existing_config, conf[0])


def subst_in_dict(d, config):
    def replace(m):
        var = m.group(1)
        if var in config:
            return config[var]
        fatal_error('"{0}" used in "${{{0}}}" not found in config'.format(var))

    for key, value in d.items():
        if not isinstance(value, str):
            continue
        if '${' in value:
            d[key] = SUBST_NAME_RE.sub(replace, value)

    for key in list(d.keys()):
        if '${' in key:
            new_key = SUBST_NAME_RE.sub(replace, key)
            d[new_key] = d[key]
            del d[key]


def perform_variable_subst(config):
    if config[DOG_CONFIG_FILE_VERSION] == 1:
        subst_in_dict(config[VOLUMES], config)
    else:
        subst_in_dict(config, config)
        subst_in_dict(config[VOLUMES], config)
        subst_in_dict(config[VOLUMES_FROM], config)
        subst_in_dict(config[USB_DEVICES], config)


def handle_auto_mount(config):
    if not config[AUTO_MOUNT]:
        return
    if sys.platform == 'win32':
        drive = config[WIN32_CWD].drive
        config[VOLUMES]['/' + drive[0]] = drive + '\\'
    else:
        mount_point = str(find_mount_point(config[CWD]))
        config[VOLUMES][mount_point] = mount_point


def handle_full_image(config):
    if DOCKER_COMPOSE_FILE in config:
        if FULL_IMAGE in config or IMAGE in config:
            fatal_error(
                '{} and {} both found in {}'.format(
                    DOCKER_COMPOSE_FILE, IMAGE, CONFIG_FILE
                )
            )
        elif DOCKER_COMPOSE_SERVICE not in config:
            fatal_error(
                '{} must be specified when {} is in {}'.format(
                    DOCKER_COMPOSE_SERVICE, DOCKER_COMPOSE_FILE, CONFIG_FILE
                )
            )
    elif FULL_IMAGE not in config:
        if IMAGE not in config:
            fatal_error('No {} specified in {}'.format(IMAGE, CONFIG_FILE))
        if REGISTRY in config:
            config[FULL_IMAGE] = config[REGISTRY] + '/' + config[IMAGE]
        else:
            config[FULL_IMAGE] = config[IMAGE]


def handle_usb_devices(config):
    if USB_DEVICES in config:
        usb_device_paths = []
        system_usb_devices = UsbDevices()
        for vendor_product in config[USB_DEVICES].values():
            dev_path = system_usb_devices.get_bus_paths(vendor_product)
            if dev_path:
                usb_device_paths.extend(dev_path)
        if usb_device_paths:
            if DEVICE in config:
                config[DEVICE].extend(usb_device_paths)
            else:
                config[DEVICE] = usb_device_paths


def handle_volumes(config):
    home_path = str(Path.home())
    volumes = {}
    for inside, outside in config[VOLUMES].items():
        only_if_outside_exists = False
        if inside[0] == '?':
            only_if_outside_exists = True
            new_inside = inside[1:]
        else:
            new_inside = inside
        if outside.startswith('~'):
            new_outside = home_path + outside[1:]
        else:
            new_outside = outside
        if not only_if_outside_exists or os.path.exists(new_outside):
            volumes[new_inside] = new_outside
    config[VOLUMES] = volumes


def update_dependencies_in_config(config: DogConfig):
    """Update values in config depending on other values in config."""
    perform_variable_subst(config)
    handle_auto_mount(config)
    handle_full_image(config)
    handle_usb_devices(config)
    handle_volumes(config)


def get_minimum_version_from_config(version_var: str, config: DogConfig) -> str:
    if version_var not in config:
        fatal_error('{} not found in {}'.format(version_var, CONFIG_FILE))
    return config[version_var]


def get_tool_version(tool: str) -> str:
    args = [tool, '--version']
    proc = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True
    )
    if proc.returncode:
        fatal_error('{} failed to run'.format(tool))
    m = re.search(r'version (\d+\.\d+\.\d+)', proc.stdout)
    try:
        return m.group(1)
    except (AttributeError, IndexError):
        fatal_error('Could not parse version info from {}'.format(tool))


def perform_sanity_check(config: DogConfig) -> int:
    if DOCKER_COMPOSE_FILE in config:
        min_version_config = DOCKER_COMPOSE_MINIMUM_VERSION
        tool = DOCKER_COMPOSE
    else:
        min_version_config = DOCKER_MINIMUM_VERSION
        tool = docker_cmd(config)
    minimum_version = get_minimum_version_from_config(min_version_config, config)
    tool_version = get_tool_version(tool)
    if tool_version < minimum_version:
        fatal_error(
            'Version of {} ({}) is less than the minimum required version ({})'.format(
                tool, tool_version, minimum_version
            )
        )
    return 0


def read_config(argv) -> DogConfig:
    command_line_config = parse_command_line_args(
        own_name=os.path.basename(argv[0]), argv=list(argv[1:])
    )

    env_config = get_env_config()

    user_config = deque()
    user_config_file = Path.home() / ('.' + CONFIG_FILE)
    if user_config_file.is_file():
        user_config = read_dog_config(user_config_file)

    dog_config_file = find_dog_config()
    dog_config = read_dog_config(dog_config_file)

    config = {}
    update_config(config, DEFAULT_CONFIG)
    update_config(config, env_config)
    update_config_from_files(config, user_config)
    update_config_from_files(config, dog_config)
    update_config(config, command_line_config)
    update_dependencies_in_config(config)

    if config[VERBOSE]:
        log_config('Default', DEFAULT_CONFIG)
        log_config('Environment', env_config)
        log_config_from_files('User', user_config)
        log_config_from_files('Dog', dog_config)
        log_config('Cmdline', command_line_config)
        log_config('Final', config)

    return config


def main(argv) -> int:
    config = read_config(argv)

    if config[SANITY_CHECK_ALWAYS] or config[SANITY_CHECK]:
        res = perform_sanity_check(config)
        if config[SANITY_CHECK]:
            return res

    if config[PULL]:
        docker_pull(config)

    if DOCKER_COMPOSE_FILE in config:
        return docker_compose_run(config)

    if config[VOLUMES_FROM] and config[AUTO_RUN_VOLUMES_FROM]:
        docker_run_volumes_from(config)

    return docker_run(config)


def setup_tools_main():
    return main(sys.argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
