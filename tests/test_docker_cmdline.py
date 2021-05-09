import itertools
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath
from typing import List, Tuple

import pytest

import dog
from conftest import append_to_dog_config, is_windows
from dog import DogConfig, win32_to_dog_unix, find_mount_point


class MockSubprocess:
    def __init__(self):
        self.run_args = None

    def mock_run(self, *args, **kwargs):
        self.run_args = args[0]
        return subprocess.CompletedProcess(args=args, returncode=0)


@pytest.fixture
def mock_subprocess(monkeypatch) -> MockSubprocess:
    m = MockSubprocess()
    monkeypatch.setattr(subprocess, 'run', m.mock_run)
    return m


@pytest.fixture(autouse=True)
def mock_env_user(monkeypatch):
    if is_windows():
        monkeypatch.setenv('USERNAME', 'dog_test_user')
    else:
        monkeypatch.setenv('USER', 'dog_test_user')
    monkeypatch.setenv('P4USER', 'dog_test_user')
    monkeypatch.setenv('P4PORT', 'my_perforce_server:5000')


@pytest.fixture(autouse=True)
def mock_env_home(monkeypatch, home_temp_dir):
    if not is_windows():
        monkeypatch.setenv('HOME', '/home/dog_test_user')


@pytest.fixture(autouse=True)
def mock_getuid(monkeypatch, tmp_path):
    uid = 1000 if is_windows() else 1122
    if not is_windows():
        monkeypatch.setattr(os, 'getuid', lambda: uid)


@pytest.fixture(autouse=True)
def mock_group(monkeypatch):
    gid = 1000 if is_windows() else 5566
    if not is_windows():
        monkeypatch.setattr(os, 'getgid', lambda: gid)

        import grp

        class MockGroup:
            gr_name = 'test_group'

        monkeypatch.setattr(grp, 'getgrgid', lambda x: MockGroup())


def split_single_cmdline_param(param: str, args: List[str], include_value: bool = False) -> Tuple[List[str], List[str]]:
    param_list = []
    args_left = []
    i = iter(args)
    try:
        while True:
            item = next(i)
            if not item.startswith(param):
                args_left.append(item)
                continue
            param_list.append(item)
            if include_value:
                param_list.append(next(i))
    except StopIteration:
        pass
    return (param_list, args_left)


def flatten(container: Iterable) -> List:
    return list(itertools.chain.from_iterable(container))


def assert_docker_std_cmdline(run_args: List[str], sudo_outside: bool = False) -> List[str]:
    expected_args = []
    if sudo_outside:
        expected_args.append('sudo')
    expected_args.extend(['docker', 'run', '--rm'])
    assert expected_args == run_args[:len(expected_args)]
    return run_args[len(expected_args):]


def assert_docker_image_and_cmd_inside_docker(run_args: List[str], expected_docker_image: str, expected_cmd_inside_docker: List[str]) -> List[str]:
    run_args_cmd_inside_docker = run_args[-len(expected_cmd_inside_docker):]
    assert expected_cmd_inside_docker == run_args_cmd_inside_docker
    assert expected_docker_image == run_args[-(len(expected_cmd_inside_docker) + 1)]
    return run_args[:-(len(expected_cmd_inside_docker) + 1)]


def assert_workdir_param(run_args: List[str], expected_workdir_path: str) -> List[str]:
    workdir_params, args_left = split_single_cmdline_param('-w', run_args, include_value=True)
    assert ['-w', str(expected_workdir_path)] == workdir_params
    return args_left


def assert_hostname_param(run_args: List[str], expected_hostname: str) -> List[str]:
    hostname_params, args_left = split_single_cmdline_param('--hostname=', run_args)
    assert ['--hostname={}'.format(expected_hostname)] == hostname_params
    return args_left


def assert_volume_params(run_args: List[str], expected_volume_mappings: List[Tuple[str, str]]) -> List[str]:
    volume_params, args_left = split_single_cmdline_param('-v', run_args, include_value=True)
    vol_mapping_values = ['{}:{}'.format(vm[1], vm[0]) for vm in expected_volume_mappings]
    expected_volume_params = flatten(zip(['-v'] * len(expected_volume_mappings), vol_mapping_values))
    assert expected_volume_params == volume_params
    return args_left


def assert_interactive(run_args: List[str], expected_interactive: bool) -> List[str]:
    interactive_param, args_left = split_single_cmdline_param('-i', run_args)
    expected_interactive_param = ['-i'] if expected_interactive else []
    assert expected_interactive_param == interactive_param
    return args_left


def assert_env_params(run_args: List[str], expected_env_values: List[str]) -> List[str]:
    env_params, args_left = split_single_cmdline_param('-e', run_args, include_value=True)
    expected_env_params = flatten(zip(['-e'] * len(expected_env_values), expected_env_values))
    assert expected_env_params == env_params
    return args_left


def std_assert_hostname_param(args_left):
    return assert_hostname_param(args_left, 'dog_docker')


def std_assert_volume_params(args_left):
    if is_windows():
        return assert_volume_params(args_left, [('/C', 'C:\\'), ('/home/dog_test_user/.ssh:ro', str(Path.home() / '.ssh')), ('/home/dog_test_user/.p4tickets:ro', str(Path.home() / 'dog_p4tickets.txt'))])
    else:
        mount_point = str(find_mount_point(Path.cwd()))
        return assert_volume_params(args_left, [(mount_point, mount_point),
                                                ('/home/dog_test_user/.ssh:ro', str(Path.home() / '.ssh')),
                                                ('/home/dog_test_user/.p4tickets:ro', str(Path.home() / '.p4tickets'))])


def std_assert_interactive(args_left):
    return assert_interactive(args_left, True)


def std_assert_env_params(args_left):
    if is_windows():
        return assert_env_params(args_left, ['USER=dog_test_user', 'P4USER=dog_test_user', 'P4PORT=my_perforce_server:5000', 'DOG_UID=1000', 'DOG_GID=1000', 'DOG_USER=dog_test_user', 'DOG_GROUP=nodoggroup', 'DOG_HOME=/home/dog_test_user', 'DOG_AS_ROOT=False', 'DOG_PRESERVE_ENV=P4USER,P4PORT'])
    else:
        return assert_env_params(args_left, ['USER=dog_test_user', 'P4USER=dog_test_user', 'P4PORT=my_perforce_server:5000', 'DOG_UID=1122', 'DOG_GID=5566', 'DOG_USER=dog_test_user', 'DOG_GROUP=test_group', 'DOG_HOME=/home/dog_test_user', 'DOG_AS_ROOT=False', 'DOG_PRESERVE_ENV=P4USER,P4PORT'])


def get_workdir(pth: Path) -> str:
    if is_windows():
        return win32_to_dog_unix(pth)
    else:
        return str(pth)


def test_simple_docker_cmdline(call_main, tmp_path, mock_subprocess):
    append_to_dog_config(tmp_path, '[dog]\nimage=rtol/centos-for-dog\n')
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_subprocess.run_args)
    args_left = assert_docker_image_and_cmd_inside_docker(args_left, 'rtol/centos-for-dog', ['echo', 'foo'])
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_env_params(args_left)
    assert args_left == []


@pytest.mark.parametrize('image_name', ['my_little_image', 'a/path/based/image'])
def test_images(call_main, tmp_path, mock_subprocess, image_name: str):
    append_to_dog_config(tmp_path, '[dog]\nimage={}\n'.format(image_name))
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_subprocess.run_args)
    args_left = assert_docker_image_and_cmd_inside_docker(args_left, image_name, ['echo', 'foo'])
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_env_params(args_left)
    assert args_left == []


@pytest.mark.parametrize('cmds', [['echo', 'foo'], ['cat', '/tmp/test.txt'], ['my_cmd']])
def test_commands_in_docker(call_main, tmp_path, mock_subprocess, cmds: List[str]):
    append_to_dog_config(tmp_path, '[dog]\nimage=my_image\n')
    call_main(*cmds)
    args_left = assert_docker_std_cmdline(mock_subprocess.run_args)
    args_left = assert_docker_image_and_cmd_inside_docker(args_left, 'my_image', cmds)
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_env_params(args_left)
    assert args_left == []


@pytest.mark.parametrize('test_sudo', [('sudo-outside-docker=True', True), ('sudo-outside-docker=False', False), ('', False)])
def test_sudo_outside(call_main, tmp_path, mock_subprocess, test_sudo: List[Tuple[str, bool]]):
    append_to_dog_config(tmp_path, '[dog]\nimage=my_image\n{}\n'.format(test_sudo[0]))
    call_main('my_inside_cmd')
    args_left = assert_docker_std_cmdline(mock_subprocess.run_args, test_sudo[1])
    args_left = assert_docker_image_and_cmd_inside_docker(args_left, 'my_image', ['my_inside_cmd'])
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_env_params(args_left)
    assert args_left == []


if is_windows():
    DEFAULT_MOUNT_POINT = ('/C', 'C:\\')
else:
    DEFAULT_MOUNT_POINT = ('/tmp', '/tmp')


@pytest.mark.parametrize('auto_mount', [('auto-mount=True', [DEFAULT_MOUNT_POINT]), ('auto-mount=False', []), ('', [DEFAULT_MOUNT_POINT])])
def test_auto_mount(call_main, tmp_path, mock_subprocess, auto_mount: List[Tuple[str, List[Tuple[str, str]]]]):
    append_to_dog_config(tmp_path, '[dog]\nimage=my_image\nperforce=False\nssh=False\n{}\n'.format(auto_mount[0]))
    call_main('my_inside_cmd')
    args_left = assert_docker_std_cmdline(mock_subprocess.run_args)
    args_left = assert_docker_image_and_cmd_inside_docker(args_left, 'my_image', ['my_inside_cmd'])
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = assert_volume_params(args_left, auto_mount[1])
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_env_params(args_left)
    assert args_left == []


class MockReadDogConfig:
    def __init__(self, orig_read_dog_config, win_path, config_path):
        self.orig_read_dog_config = orig_read_dog_config
        self.win_path = win_path
        self.config_path = config_path

    def mocked_read_dog_config(self, dog_config: Path) -> DogConfig:
        path_to_dog_config = self.config_path if dog_config == self.win_path else dog_config
        return self.orig_read_dog_config(path_to_dog_config)


def mock_win32(monkeypatch, tmp_path, win_path, dog_config_contents: str):
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setenv('USERNAME', 'dog_test_user')
    monkeypatch.setattr(Path, 'cwd', lambda: win_path)
    monkeypatch.setattr(os.path, 'isfile', lambda x: True)
    append_to_dog_config(tmp_path, dog_config_contents)
    mrdc = MockReadDogConfig(dog.read_dog_config, win_path / 'dog.config', tmp_path / 'dog.config')
    monkeypatch.setattr(dog, 'read_dog_config', mrdc.mocked_read_dog_config)


def test_auto_mount_win32(call_main, tmp_path, mock_subprocess, monkeypatch):
    win_path = PureWindowsPath('C:\\tmp\\test')
    mock_win32(monkeypatch, tmp_path, win_path, '[dog]\nimage=my_image\nperforce=False\nssh=False\n')
    call_main('my_inside_cmd')
    args_left = assert_docker_std_cmdline(mock_subprocess.run_args)
    args_left = assert_docker_image_and_cmd_inside_docker(args_left, 'my_image', ['my_inside_cmd'])
    args_left = assert_workdir_param(args_left, '/C/tmp/test')
    args_left = std_assert_hostname_param(args_left)
    args_left = assert_volume_params(args_left, [('/C', 'C:\\')])
    args_left = std_assert_interactive(args_left)
    args_left = assert_env_params(args_left, ['USER=dog_test_user', 'P4USER=dog_test_user', 'P4PORT=my_perforce_server:5000', 'DOG_UID=1000', 'DOG_GID=1000', 'DOG_USER=dog_test_user', 'DOG_GROUP=nodoggroup', 'DOG_HOME=/home/dog_test_user', 'DOG_AS_ROOT=False', 'DOG_PRESERVE_ENV=P4USER,P4PORT'])
    assert args_left == []


def test_perforce_win32(call_main, tmp_path, mock_subprocess, monkeypatch, home_temp_dir):
    win_path = PureWindowsPath('C:\\tmp\\test')
    mock_win32(monkeypatch, tmp_path, win_path, '[dog]\nimage=my_image\nauto-mount=False\nperforce=True\nssh=False\n')
    call_main('my_inside_cmd')
    args_left = assert_docker_std_cmdline(mock_subprocess.run_args)
    args_left = assert_docker_image_and_cmd_inside_docker(args_left, 'my_image', ['my_inside_cmd'])
    args_left = assert_workdir_param(args_left, '/C/tmp/test')
    args_left = std_assert_hostname_param(args_left)
    args_left = assert_volume_params(args_left, [('/home/dog_test_user/.p4tickets:ro', str(home_temp_dir / 'dog_p4tickets.txt'))])
    args_left = std_assert_interactive(args_left)
    args_left = assert_env_params(args_left, ['USER=dog_test_user', 'P4USER=dog_test_user', 'P4PORT=my_perforce_server:5000', 'DOG_UID=1000', 'DOG_GID=1000', 'DOG_USER=dog_test_user', 'DOG_GROUP=nodoggroup', 'DOG_HOME=/home/dog_test_user', 'DOG_AS_ROOT=False', 'DOG_PRESERVE_ENV=P4USER,P4PORT'])
    assert args_left == []
