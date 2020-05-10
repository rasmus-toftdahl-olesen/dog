#!/usr/bin/env python3

import sys
import os
import subprocess
from pathlib import Path
import configparser
import argparse
from typing import Optional, List, Dict, Union

REGISTRY = 'gitlab.kitenet.com:4567'
CONFIG_FILE = 'dog.config'
VERSION = 1

DogConfig = Dict[str, Union[str, List[str], Dict[str, str]]]


def default_config() -> DogConfig:
    return {'sudo-outside-docker': False,
            'exposed-dog-variables': ['uid', 'gid', 'user', 'group', 'home', 'as-root'],
            'uid': 1000,
            'gid': 1000,
            'user': 'nobody',
            'group': 'nogroup',
            'home': '/home/nobody',
            'p4user': 'nobody',
            'cwd': '/home/nobody',
            'volumes': {},
            'args': ['id'],
            'image': 'alpine',
            'registry': REGISTRY,
            'interactive': True,
            'terminal': False,
            'as-root': False,
            'pull': False}


def find_dog_config() -> Optional[Path]:
    cur = Path.cwd() / CONFIG_FILE
    for parent in cur.parents:
        dog_config = parent / CONFIG_FILE
        if dog_config.exists():
            return dog_config
    return None


def read_dog_config(dog_config=find_dog_config()) -> DogConfig:
    if dog_config is None:
        image = 'esw/serverscripts/forge'
        return {'image': image, 'registry': REGISTRY}
    else:
        config = configparser.ConfigParser()
        config.read(dog_config)
        return dict(config['dog'])


def parse_command_line_args() -> DogConfig:
    parser = argparse.ArgumentParser(description='Docker run wrapper to make it easier to call commands.')
    parser.add_argument('args', type=str, nargs='+', help='Command to call inside docker (with arguments)')
    parser.add_argument('--pull', dest='pull', action='store_const', const=True, help='Pull the latest version of the docker image')
    interactive_group = parser.add_mutually_exclusive_group()
    interactive_group.add_argument('--interactive', dest='interactive', action='store_const', const=True, help='Run interactive (keep stdin open)')
    interactive_group.add_argument('--not-interactive', dest='interactive', action='store_const', const=False, help='Do not run interactive')
    terminal_group = parser.add_mutually_exclusive_group()
    terminal_group.add_argument('--terminal', dest='terminal', action='store_const', const=True, help='Allocate a pseudo terminal')
    terminal_group.add_argument('--no-terminal', dest='terminal', action='store_const', const=False, help='Do not allocate a pseudo terminal')
    parser.add_argument('--as-root', dest='as-root', action='store_const', const=True, help='Run as root inside the docker')
    parser.add_argument('--version', action='version', version=f'dog version {VERSION}')

    # Insert the needed -- to seperate dog args with the rest of the commands
    # But only if the user did not do it himself
    argv = list(sys.argv[1:])
    own_name = os.path.basename(sys.argv[0])
    if 'dog' not in own_name:
        argv.insert(0, own_name)
    if '--' not in argv:
        first_normal_arg = -1
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
    return config


def get_env_config(**extra) -> DogConfig:
    config = {}
    if sys.platform == 'win32':
        config['uid'] = 1000
        config['gid'] = 1000
        config['user'] = os.getenv('USERNAME')
        config['group'] = 'oticon'
        config['home'] = f'/home/{config["user"]}'
        # Write a unix version of the p4tickets.txt file
        win_version = Path.home() / 'p4tickets.txt'
        unix_verison = Path.home() / 'dog_p4tickets.txt'
        if win_version.exists():
            # Convert windows line endings to unix line endings
            unix_verison.write_bytes(win_version.read_text().encode('ascii'))
        else:
            unix_version.write_text('')

    else:
        config['uid'] = os.getuid()
        config['gid'] = os.getgid()
        config['home'] = os.getenv('HOME')
        config['user'] = os.getenv('USER')
        config['group'] = os.getenv('GROUP')

    config['p4user'] = os.getenv('P4USER', config['user'])

    if sys.platform == 'win32':
        config['cwd'] = '/c/' + os.getcwd().replace('\\', '/')[2:]
    else:
        config['cwd'] = os.getcwd()

    if sys.platform == 'win32':
        config['volumes'] = {'c:\\': '/c',
                             f'{Path.home() / "dog_p4tickets.txt"}': f'{config["home"]}/.p4tickets:ro'}
    else:
        config['volumes'] = {'/scratch': '/scratch',
                             '/tc/w': '/tc/w',
                             f'{Path.home() / ".p4tickets"}': f'{config["home"]}/.p4tickets:ro'}
    config['volumes'][f'{Path.home() / ".ssh"}'] = f'{config["home"]}/.ssh:ro'

    return config


def run(config: DogConfig):
    assert config['full-image'] is not None, 'You need to at least specify the full_image.'

    args = []
    if config['sudo-outside-docker']:
        args += ['sudo']
    args += ['docker']
    args += ['run',
             '--rm',
             '--hostname=kbnuxdockerrtol',
             '-w', config['cwd']]

    for outside, inside in config['volumes'].items():
        args += ['-v', f'{outside}:{inside}']

    if config['interactive']:
        args.append('-i')

    if config['terminal']:
        args.append('-t')

    if not config['as-root']:
        args.extend(['-e', f'USER={config["user"]}',
                     '-e', f'P4USER={config["p4user"]}'])

    for name in config['exposed-dog-variables']:
        env_name = name.upper().replace('-', '_')
        args.extend(['-e', f'DOG_{env_name}={config[name]}'])

    args.append(config['full-image'])
    args.extend(config['args'])

    try:
        proc = subprocess.run(args)
        return proc.returncode
    except KeyboardInterrupt:
        print('Dog received Ctrl+C')
        return -1


if __name__ == '__main__':
    config = default_config()
    config.update(get_env_config())
    user_config = Path.home() / '.dog.config'
    if user_config.is_file():
        config.update(read_dog_config(user_config))
    config.update(read_dog_config())
    config.update(parse_command_line_args())

    if 'full-image' not in config:
        config['full-image'] = config['registry'] + '/' + config['image']

    if config['pull']:
        try:
            args = []
            if config['sudo-outside-docker']:
                args += ['sudo']
            args += ['docker']
            args += ['pull', config['full-image']]
            proc = subprocess.run(args)
            if proc.returncode != 0:
                print(f'ERROR {proc.returncode} while pulling:')
                print(proc.stdout)
                print(proc.stderr)
                sys.exit(proc.returncode)
        except KeyboardInterrupt:
            print('Dog received Ctrl+C')
            sys.exit(-1)

    returncode = run(config)
    sys.exit(returncode)
