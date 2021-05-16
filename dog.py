#!/usr/bin/env python3

import argparse
import configparser
import copy
import os
import pprint
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Union

# Version of dog
VERSION = 9

# Constants for consistant naming of dog variables, etc.
ARGS = 'args'
AS_ROOT = 'as-root'
AUTO_MOUNT = 'auto-mount'
CONFIG_FILE = 'dog.config'
CWD = 'cwd'
DOCKER_COMPOSE_FILE = 'docker-compose-file'
DOCKER_COMPOSE_SERVICE = 'docker-compose-service'
DOG_CONFIG_PATH = 'dog-config-path'
EXPOSED_DOG_VARIABLES = 'exposed-dog-variables'
FULL_IMAGE = 'full-image'
GID = 'gid'
GROUP = 'group'
HOME = 'home'
HOSTNAME = 'hostname'
IMAGE = 'image'
INTERACTIVE = 'interactive'
P4USER = 'p4user'
PERFORCE = 'perforce'
PORTS = 'ports'
PRESERVE_ENV = 'preserve-env'
PULL = 'pull'
REGISTRY = 'registry'
SSH = 'ssh'
SUDO_OUTSIDE_DOCKER = 'sudo-outside-docker'
TERMINAL = 'terminal'
UID = 'uid'
USER = 'user'
USER_ENV_VARS = 'user-env-vars'
USER_ENV_VARS_IF_SET = 'user-env-vars-if-set'
VERBOSE = 'verbose'
VOLUMES = 'volumes'
WIN32_CWD = 'win32-cwd'

DogConfig = Dict[str, Union[str, int, bool, Path, List[str], Dict[str, str]]]


def log_verbose(config: DogConfig, txt: str):
    if config[VERBOSE]:
        print(txt)


def log_config(name: str, config: DogConfig, filename: Path = None):
    if filename:
        print('{} Config ({}):'.format(name, filename))
    else:
        print('{} Config:'.format(name))
    pprint.pprint(config, indent=4)


def fatal_error(text: str, error_code: int = -1):
    print('ERROR[dog]: {}'.format(text), file=sys.stderr)
    sys.exit(error_code)


def default_config() -> DogConfig:
    return {ARGS: ['id'],
            AS_ROOT: False,
            AUTO_MOUNT: True,
            CWD: '/home/nobody',
            EXPOSED_DOG_VARIABLES: [UID, GID, USER, GROUP, HOME, AS_ROOT, PRESERVE_ENV],
            GID: 1000,
            GROUP: 'nogroup',
            HOME: '/home/nobody',
            HOSTNAME: 'dog_docker',
            INTERACTIVE: True,
            P4USER: 'nobody',
            PORTS: {},
            PRESERVE_ENV: 'P4USER,P4PORT',
            PULL: False,
            SSH: True,
            PERFORCE: True,
            SUDO_OUTSIDE_DOCKER: False,
            TERMINAL: False,
            UID: 1000,
            USER: 'nobody',
            USER_ENV_VARS: {},
            USER_ENV_VARS_IF_SET: {},
            VERBOSE: False,
            VOLUMES: {}
            }


def find_dog_config() -> Path:
    cur = Path.cwd() / CONFIG_FILE
    for parent in cur.parents:
        dog_config = parent / CONFIG_FILE
        if os.path.isfile(str(dog_config)):
            return dog_config

    fatal_error('Could not find {} in current directory or on of its parents'.format(CONFIG_FILE))


def list_from_config_entry(entry: str) -> List[str]:
    var_list = entry.split(',')
    return [s.strip() for s in var_list]


def get_user_env_vars(config_user_env_vars: str, allow_empty: bool) -> Dict[str, str]:
    env_var_list = list_from_config_entry(config_user_env_vars)
    user_env_vars = {}
    for env_var in env_var_list:
        value = os.getenv(env_var)
        if value is not None:
            user_env_vars[env_var] = value
        elif not allow_empty:
            fatal_error('{} was specified in {} but was not set in the current shell environment'.format(env_var, USER_ENV_VARS))
    return user_env_vars


def read_dog_config(dog_config: Path) -> DogConfig:
    config = configparser.ConfigParser(delimiters='=')
    config.read(str(dog_config))
    dog_config = dict(config['dog'])
    # Parse booleans - use default_config() to determine which values should be booleans
    for k, v in default_config().items():
        if isinstance(v, bool) and k in config['dog']:
            dog_config[k] = config['dog'].getboolean(k)

    if EXPOSED_DOG_VARIABLES in dog_config:
        dog_config[EXPOSED_DOG_VARIABLES] = list_from_config_entry(dog_config[EXPOSED_DOG_VARIABLES])
    if USER_ENV_VARS in dog_config:
        dog_config[USER_ENV_VARS] = get_user_env_vars(dog_config[USER_ENV_VARS], allow_empty=False)
    if USER_ENV_VARS_IF_SET in dog_config:
        dog_config[USER_ENV_VARS_IF_SET] = get_user_env_vars(dog_config[USER_ENV_VARS_IF_SET], allow_empty=True)
    if PORTS in config:
        dog_config[PORTS] = dict(config[PORTS])
    if VOLUMES in config:
        dog_config[VOLUMES] = dict(config[VOLUMES])
    return dog_config


def parse_command_line_args(own_name: str, argv: list) -> DogConfig:
    parser = argparse.ArgumentParser(description='Docker run wrapper to make it easier to call commands.')
    parser.add_argument(ARGS, type=str, nargs='+', help='Command to call inside docker (with arguments)')
    parser.add_argument('--pull', dest=PULL, action='store_const', const=True, help='Pull the latest version of the docker image')
    interactive_group = parser.add_mutually_exclusive_group()
    interactive_group.add_argument('--interactive', dest=INTERACTIVE, action='store_const', const=True, help='Run interactive (keep stdin open)')
    interactive_group.add_argument('--not-interactive', dest=INTERACTIVE, action='store_const', const=False, help='Do not run interactive')
    terminal_group = parser.add_mutually_exclusive_group()
    terminal_group.add_argument('--terminal', dest=TERMINAL, action='store_const', const=True, help='Allocate a pseudo terminal')
    terminal_group.add_argument('--no-terminal', dest=TERMINAL, action='store_const', const=False, help='Do not allocate a pseudo terminal')
    parser.add_argument('--as-root', dest=AS_ROOT, action='store_const', const=True, help='Run as root inside the docker')
    parser.add_argument('--version', action='version', version='dog version {}'.format(VERSION))
    parser.add_argument('--verbose', dest=VERBOSE, action='store_const', const=True, help='Provide more dog output (useful for debugging)')

    # Insert the needed -- to seperate dog args with the rest of the commands
    # But only if the user did not do it himself
    if 'dog' not in own_name:
        argv.insert(0, own_name)
    if '--' not in argv:
        for index, arg in enumerate(argv):
            if arg[0] != '-':
                argv.insert(index, '--')
                break
    args = parser.parse_args(argv)
    config = vars(args)
    if config['pull'] is None:
        del config['pull']
    if config['terminal'] is None:
        del config['terminal']
    if config['interactive'] is None:
        del config['interactive']
    if config['as-root'] is None:
        del config['as-root']
    if config[VERBOSE] is None:
        del config[VERBOSE]
    return config


def win32_to_dog_unix(win_path: Union[str, Path]) -> str:
    """Convert a windows path to what i will be inside dog (unix)."""
    if isinstance(win_path, str):
        win_path = Path(win_path)
    return '/' + win_path.as_posix().replace(':', '')


def get_env_config() -> DogConfig:
    config = {}
    if sys.platform == 'win32':
        config[UID] = 1000
        config[GID] = 1000
        config[USER] = os.getenv('USERNAME')
        config[GROUP] = 'nodoggroup'
        config[HOME] = '/home/' + config[USER]
    else:
        import grp
        config[UID] = os.getuid()
        config[GID] = os.getgid()
        config[HOME] = str(Path.home())
        config[USER] = os.getenv('USER')
        config[GROUP] = grp.getgrgid(config['gid']).gr_name

    config[P4USER] = os.getenv('P4USER', config[USER])

    cwd = Path.cwd()
    if sys.platform == 'win32':
        config[WIN32_CWD] = cwd
        config[CWD] = win32_to_dog_unix(cwd)
    else:
        config[CWD] = cwd

    return config


def find_mount_point(p: Path):
    while not os.path.ismount(str(p)) and not str(p.parent) == p.root:
        p = p.parent
    return p


def docker_pull(config: DogConfig):
    if DOCKER_COMPOSE_FILE in config:
        fatal_error('{} is not compatible with pull'.format(DOCKER_COMPOSE_FILE))
    try:
        args = ['sudo'] if config[SUDO_OUTSIDE_DOCKER] else []
        args.append('docker')
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
    if not config[AS_ROOT]:
        if 'USER' not in config[USER_ENV_VARS].keys() and 'USER' not in config[USER_ENV_VARS_IF_SET].keys() and 'USER' not in config[PRESERVE_ENV].split(','):
            args.extend(['-e', 'USER=' + config[USER]])
        if 'P4USER' not in config[USER_ENV_VARS].keys() and 'P4USER' not in config[USER_ENV_VARS_IF_SET].keys() and 'P4USER' not in config[PRESERVE_ENV].split(','):
            args.extend(['-e', 'P4USER=' + config[P4USER]])

    for env_var_name in config[PRESERVE_ENV].split(','):
        if env_var_name in os.environ:
            args.extend(['-e', '{}={}'.format(env_var_name, os.environ[env_var_name])])

    for name in config[EXPOSED_DOG_VARIABLES]:
        env_name = name.upper().replace('-', '_')
        args.extend(['-e', 'DOG_{}={}'.format(env_name, config[name])])

    for env_name, value in config[USER_ENV_VARS].items():
        args.extend(['-e', '{}={}'.format(env_name, value)])
    for env_name, value in config[USER_ENV_VARS_IF_SET].items():
        args.extend(['-e', '{}={}'.format(env_name, value)])
    return args


def docker_run(config: DogConfig):
    args = []
    if config[SUDO_OUTSIDE_DOCKER]:
        args += ['sudo']
    args += ['docker']
    args += ['run',
             '--rm',
             '--hostname={}'.format(config[HOSTNAME]),
             '-w', str(config[CWD])]

    for outside, inside in config['volumes'].items():
        args += ['-v', outside + ':' + inside]

    for outside, inside in config['ports'].items():
        args += ['-p', outside + ':' + inside]

    if config[INTERACTIVE]:
        args.append('-i')

    if config[TERMINAL]:
        args.append('-t')

    env_args = generate_env_arg_list(config)
    args.extend(env_args)

    args.append(config[FULL_IMAGE])
    args.extend(config[ARGS])

    log_verbose(config, ' '.join(args))
    try:
        proc = subprocess.run(args)
        return proc.returncode
    except KeyboardInterrupt:
        print('Dog received Ctrl+C')
        return -1


def update_config(existing_config: DogConfig, new_config: DogConfig):
    """Merge two DogConfigs - all exiting keys in exising_config will be replaced with the keys in new_config
       - except for dictionaries - they will be merged with the existing dictionary."""
    for k, v in new_config.items():
        if k in existing_config and isinstance(v, dict):
            update_config(existing_config[k], new_config[k])
        else:
            existing_config[k] = copy.copy(new_config[k])


def update_dependencies_in_config(config: DogConfig):
    """Update values in config depending on other values in config."""
    if 'minimum-version' in config:
        minimum_version = int(config['minimum-version'])
        if VERSION < minimum_version:
            fatal_error('Minimum version required ({}) is greater than your dog version ({}) - please upgrade dog'.format(minimum_version, VERSION))

    if config[AUTO_MOUNT]:
        if sys.platform == 'win32':
            drive = config[WIN32_CWD].drive
            config[VOLUMES][drive + '\\'] = '/' + drive[0]
        else:
            mount_point = str(find_mount_point(config[CWD]))
            config[VOLUMES][mount_point] = mount_point

    if config[SSH]:
        config[VOLUMES][str(Path.home() / ".ssh")] = config[HOME] + '/.ssh:ro'

    if config[PERFORCE]:
        if sys.platform == 'win32':
            # Write a unix version of the p4tickets.txt file
            win_version = Path.home() / 'p4tickets.txt'
            unix_version = Path.home() / 'dog_p4tickets.txt'
            if win_version.exists():
                # Convert windows line endings to unix line endings
                unix_version.write_bytes(win_version.read_text().encode('ascii'))
            else:
                unix_version.write_text('')

            config[VOLUMES][str(Path.home() / "dog_p4tickets.txt")] = config[HOME] + '/.p4tickets:ro'
        else:
            config[VOLUMES][str(Path.home() / ".p4tickets")] = config[HOME] + '/.p4tickets:ro'

    if DOCKER_COMPOSE_FILE in config:
        if FULL_IMAGE in config or IMAGE in config:
            fatal_error('{} and {} both found in {}'.format(DOCKER_COMPOSE_FILE, IMAGE, CONFIG_FILE))
        elif DOCKER_COMPOSE_SERVICE not in config:
            fatal_error('{} must be specified when {} is in {}'.format(DOCKER_COMPOSE_SERVICE, DOCKER_COMPOSE_FILE, CONFIG_FILE))
    elif FULL_IMAGE not in config:
        if IMAGE not in config:
            fatal_error('No {} specified in {}'.format(IMAGE, CONFIG_FILE))
        if REGISTRY in config:
            config[FULL_IMAGE] = config[REGISTRY] + '/' + config[IMAGE]
        else:
            config[FULL_IMAGE] = config[IMAGE]

    home_path = str(Path.home())
    volumes = {}
    for outside, inside in config[VOLUMES].items():
        if inside.startswith('$' + HOME):
            new_inside = config[HOME] + inside[5:]
        else:
            new_inside = inside
        if outside.startswith('~'):
            new_outside = home_path + outside[1:]
        else:
            new_outside = outside
        volumes[new_outside] = new_inside
    config[VOLUMES] = volumes


def main(argv) -> int:
    command_line_config = parse_command_line_args(own_name=os.path.basename(argv[0]), argv=list(argv[1:]))

    default_conf = default_config()
    env_config = get_env_config()
    user_config_file = Path.home() / ('.' + CONFIG_FILE)
    user_config = None
    if user_config_file.is_file():
        user_config = read_dog_config(user_config_file)
    dog_config_file = find_dog_config()
    dog_config = read_dog_config(dog_config_file)
    dog_config[DOG_CONFIG_PATH] = str(dog_config_file.parent)

    config = {}
    update_config(config, default_conf)
    update_config(config, env_config)
    if user_config:
        update_config(config, user_config)
    update_config(config, dog_config)
    update_config(config, command_line_config)
    update_dependencies_in_config(config)

    if config[VERBOSE]:
        log_config('Default', default_conf)
        log_config('Environment', env_config)
        log_config('User', user_config, user_config_file)
        log_config('Dog', dog_config, dog_config_file)
        log_config('Final', config)

    if config['pull']:
        docker_pull(config)

    return docker_run(config)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
