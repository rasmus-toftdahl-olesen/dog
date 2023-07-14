import itertools
import os
import platform
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath
from subprocess import CompletedProcess
from typing import List, Tuple, Union

import pytest

import dog
from conftest import (
    append_to_dog_config,
    update_dog_config,
    is_windows,
    ACTUAL_DOG_VERSION,
)
from dog import (
    ADDITIONAL_DOCKER_RUN_PARAMS,
    DEVICE,
    DOG,
    DOG_CONFIG_FILE_VERSION,
    DogConfig,
    IMAGE,
    INIT,
    MAC_ADDRESS,
    NETWORK,
    USB_DEVICES,
    USE_PODMAN,
    UsbDevices,
    VOLUMES,
    VOLUMES_FROM,
    find_mount_point,
    win32_to_dog_unix,
)


class MockExecVp:
    def __init__(self):
        self.file = None
        self.args = None

    def mock_execvp(self, file, args):
        self.file = file
        self.args = args

    def mock_subprocess_run(
        self,
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
    ):
        self.file = args[0]
        self.args = args
        stdout_obj = None
        if stdout == subprocess.PIPE:

            class MyStdout:
                def splitlines(self):
                    return [f'This is the output of {args}']

            stdout_obj = MyStdout()
        return CompletedProcess(args, returncode=0, stdout=stdout_obj)


@pytest.fixture
def mock_execvp(monkeypatch):
    m = MockExecVp()
    if sys.platform != 'win32':
        monkeypatch.setattr(os, 'execvp', m.mock_execvp)
    else:
        monkeypatch.setattr(subprocess, 'run', m.mock_subprocess_run)
    return m


class MockSubprocess:
    def __init__(self):
        self.file = None
        self.args = None

    def mock_run(self, args):
        self.file = args[0]
        self.args = args
        return subprocess.CompletedProcess(args=args, returncode=0)


@pytest.fixture
def mock_subprocess(monkeypatch):
    m = MockSubprocess()
    monkeypatch.setattr(subprocess, 'run', m.mock_run)
    return m


@pytest.fixture(autouse=True)
def mock_env_user(monkeypatch, home_temp_dir):
    if is_windows():
        monkeypatch.setenv('USERNAME', 'dog_test_user')
    else:
        monkeypatch.setenv('USER', 'dog_test_user')
    monkeypatch.setenv('P4USER', 'dog_test_user')
    monkeypatch.setenv('P4PORT', 'my_perforce_server:5000')


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


@pytest.fixture(autouse=True)
def mock_hostname(monkeypatch):
    hostname = 'mocked_hostname'
    monkeypatch.setattr(platform, 'node', lambda: hostname)


def split_single_cmdline_param(
    param: str, args: List[str], include_value: bool = False
) -> Tuple[List[str], List[str]]:
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
    return param_list, args_left


def flatten(container: Iterable) -> List:
    return list(itertools.chain.from_iterable(container))


def assert_docker_std_cmdline(
    exec_mock: Union[MockExecVp, MockSubprocess],
    sudo_outside: bool = False,
    use_podman: bool = False,
) -> List[str]:
    expected_args = []
    if sudo_outside:
        expected_args.append('sudo')
    docker_cmd = 'podman' if use_podman else 'docker'
    expected_args.extend([docker_cmd, 'run', '--rm'])
    assert exec_mock.file == expected_args[0]
    assert exec_mock.args[: len(expected_args)] == expected_args
    return exec_mock.args[len(expected_args) :]


def assert_docker_image_and_cmd_inside_docker(
    run_args: List[str],
    expected_docker_image: str,
    expected_cmd_inside_docker: List[str],
) -> List[str]:
    run_args_cmd_inside_docker = run_args[-len(expected_cmd_inside_docker) :]
    assert expected_cmd_inside_docker == run_args_cmd_inside_docker
    assert expected_docker_image == run_args[-(len(expected_cmd_inside_docker) + 1)]
    return run_args[: -(len(expected_cmd_inside_docker) + 1)]


def assert_workdir_param(run_args: List[str], expected_workdir_path: str) -> List[str]:
    workdir_params, args_left = split_single_cmdline_param(
        '-w', run_args, include_value=True
    )
    assert ['-w', str(expected_workdir_path)] == workdir_params
    return args_left


def assert_hostname_param(run_args: List[str], expected_hostname: str) -> List[str]:
    hostname_params, args_left = split_single_cmdline_param('--hostname=', run_args)
    assert ['--hostname={}'.format(expected_hostname)] == hostname_params
    return args_left


def assert_network_param(run_args: List[str], expected_network: str) -> List[str]:
    network_params, args_left = split_single_cmdline_param(
        '--network', run_args, include_value=True
    )
    assert network_params == ['--network', expected_network]
    return args_left


def assert_volume_params(
    run_args: List[str], expected_volume_mappings: List[Tuple[str, str]]
) -> List[str]:
    volume_params, args_left = split_single_cmdline_param(
        '-v', run_args, include_value=True
    )
    vol_mapping_values = [
        '{}:{}'.format(vm[1], vm[0]) for vm in expected_volume_mappings
    ]
    num_expected_volume_mappings = len(expected_volume_mappings)
    expected_volume_params = flatten(
        zip(['-v'] * num_expected_volume_mappings, vol_mapping_values)
    )
    params = volume_params[: num_expected_volume_mappings * 2]
    rest_params = volume_params[num_expected_volume_mappings * 2 :]
    assert params == expected_volume_params
    return args_left + rest_params


def assert_volumes_from_params(run_args: List[str], expected) -> List[str]:
    volumes_from_params, args_left = split_single_cmdline_param(
        '--volumes-from', run_args, include_value=True
    )
    num_expected = len(expected)
    expected_volumes_from = flatten(zip(['--volumes-from'] * num_expected, expected))
    params = volumes_from_params[: num_expected * 2]
    rest_params = volumes_from_params[num_expected * 2 :]
    assert params == expected_volumes_from
    return args_left + rest_params


def assert_device_params(run_args: List[str], expected_devices: List[str]) -> List[str]:
    device_params, args_left = split_single_cmdline_param(
        '--device=', run_args, include_value=True
    )
    num_expected_device_params = len(expected_devices)
    expected_device_params = [f'--device={device}' for device in expected_devices]
    params = device_params[:num_expected_device_params]
    rest_params = device_params[num_expected_device_params:]
    assert params == expected_device_params
    return args_left + rest_params


def assert_interactive(run_args: List[str], expected_interactive: bool) -> List[str]:
    interactive_param, args_left = split_single_cmdline_param('-i', run_args)
    expected_interactive_param = ['-i'] if expected_interactive else []
    assert expected_interactive_param == interactive_param
    return args_left


def assert_init(run_args: List[str], expected_init: bool) -> List[str]:
    init_param, args_left = split_single_cmdline_param('--init', run_args)
    expected_init_param = ['--init'] if expected_init else []
    assert expected_init_param == init_param
    return args_left


def assert_env_params(run_args: List[str], expected_env_values: List[str]) -> List[str]:
    env_params, args_left = split_single_cmdline_param(
        '-e', run_args, include_value=True
    )
    expected_env_params = flatten(
        zip(['-e'] * len(expected_env_values), expected_env_values)
    )
    assert expected_env_params == env_params
    return args_left


def std_assert_hostname_param(args_left):
    return assert_hostname_param(args_left, 'mocked_hostname')


def std_assert_volume_params(tmp_path, args_left):
    if is_windows():
        return assert_volume_params(args_left, [('/C', 'C:\\')])
    else:
        mount_point = str(find_mount_point(tmp_path))
        return assert_volume_params(args_left, [(mount_point, mount_point)])


def std_assert_interactive(args_left):
    return assert_interactive(args_left, True)


def std_assert_init(args_left):
    return assert_init(args_left, True)


def assert_mac_address_param(
    run_args: List[str], expected_mac_address: str
) -> List[str]:
    mac_address_params, args_left = split_single_cmdline_param(
        '--mac-address', run_args, include_value=True
    )
    assert ['--mac-address', expected_mac_address] == mac_address_params
    return args_left


def std_assert_env_params(home_temp_dir, args_left):
    if is_windows():
        return assert_env_params(
            args_left,
            [
                'DOG_UID=1000',
                'DOG_GID=1000',
                'DOG_USER=dog_test_user',
                'DOG_GROUP=nodoggroup',
                'DOG_HOME=/home/dog_test_user',
                'DOG_AS_ROOT=False',
                f'DOG_VERSION={ACTUAL_DOG_VERSION}',
            ],
        )
    else:
        return assert_env_params(
            args_left,
            [
                'DOG_UID=1122',
                'DOG_GID=5566',
                'DOG_USER=dog_test_user',
                'DOG_GROUP=test_group',
                f'DOG_HOME={home_temp_dir}',
                'DOG_AS_ROOT=False',
                f'DOG_VERSION={ACTUAL_DOG_VERSION}',
            ],
        )


def get_workdir(pth: Path) -> str:
    if is_windows():
        return win32_to_dog_unix(pth)
    else:
        return str(pth)


@pytest.mark.parametrize('network', ['none', 'host', 'mynetwork'])
def test_network(
    basic_dog_config_with_image,
    call_main,
    tmp_path,
    mock_execvp,
    home_temp_dir,
    network: str,
):
    update_dog_config(tmp_path, {DOG: {NETWORK: network}})
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'debian:latest', ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = assert_network_param(args_left, network)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    assert args_left == []


@pytest.mark.parametrize(
    'additional_run_params',
    ['--mac-address="00:11:22:33:44:55"', '--security-opt label=disable'],
)
def test_additional_run_params(
    basic_dog_config_with_image,
    call_main,
    tmp_path,
    mock_execvp,
    home_temp_dir,
    additional_run_params: str,
):
    update_dog_config(
        tmp_path, {DOG: {ADDITIONAL_DOCKER_RUN_PARAMS: additional_run_params}}
    )
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'debian:latest', ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    assert args_left == additional_run_params.split()


@pytest.mark.parametrize('use_podman', [False, True])
def test_simple_docker_cmdline(
    basic_dog_config, call_main, tmp_path, mock_execvp, home_temp_dir, use_podman: bool,
):
    update_dog_config(
        tmp_path,
        {
            DOG: {
                IMAGE: 'ghcr.io/rasmus-toftdahl-olesen/dog/centos-for-dog',
                USE_PODMAN: use_podman,
            }
        },
    )
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp, use_podman=use_podman)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'ghcr.io/rasmus-toftdahl-olesen/dog/centos-for-dog', ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    assert args_left == []


@pytest.mark.parametrize('image_name', ['my_little_image', 'a/path/based/image'])
def test_images(
    basic_dog_config, call_main, tmp_path, mock_execvp, home_temp_dir, image_name: str,
):
    append_to_dog_config(tmp_path, ['image={}'.format(image_name)])
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, image_name, ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    assert args_left == []


@pytest.mark.parametrize(
    'cmds', [['echo', 'foo'], ['cat', '/tmp/test.txt'], ['my_cmd']]
)
def test_commands_in_docker(
    basic_dog_config, call_main, tmp_path, home_temp_dir, mock_execvp, cmds: List[str],
):
    append_to_dog_config(tmp_path, ['image=my_image'])
    call_main(*cmds)
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(args_left, 'my_image', cmds)
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    assert args_left == []


@pytest.mark.parametrize(
    'test_sudo',
    [
        ('sudo-outside-docker=True', True),
        ('sudo-outside-docker=False', False),
        ('', False),
    ],
)
def test_sudo_outside(
    basic_dog_config,
    call_main,
    tmp_path,
    mock_execvp,
    home_temp_dir,
    test_sudo: Tuple[str, bool],
):
    append_to_dog_config(tmp_path, ['image=my_image', test_sudo[0]])
    call_main('my_inside_cmd')
    args_left = assert_docker_std_cmdline(mock_execvp, test_sudo[1])
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'my_image', ['my_inside_cmd']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    assert args_left == []


@pytest.mark.parametrize(
    'extra_dog_conf,default_mount_point',
    [('auto-mount=True', True), ('auto-mount=False', False), ('', True)],
)
def test_auto_mount(
    basic_dog_config,
    call_main,
    tmp_path,
    mock_execvp,
    home_temp_dir,
    extra_dog_conf: str,
    default_mount_point: bool,
):
    append_to_dog_config(tmp_path, ['image=my_image', extra_dog_conf])
    call_main('my_inside_cmd')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'my_image', ['my_inside_cmd']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    if default_mount_point:
        if is_windows():
            args_left = assert_volume_params(args_left, [('/C', 'C:\\')])
        else:
            mount_point = str(find_mount_point(tmp_path))
            args_left = assert_volume_params(args_left, [(mount_point, mount_point)])
    else:
        args_left = assert_volume_params(args_left, [])
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    assert args_left == []


class MockReadDogConfig:
    def __init__(self, orig_read_dog_config, win_path, config_path):
        self.orig_read_dog_config = orig_read_dog_config
        self.win_path = win_path
        self.config_path = config_path

    def mocked_read_dog_config(self, dog_config: Path) -> DogConfig:
        path_to_dog_config = (
            self.config_path if dog_config == self.win_path else dog_config
        )
        return self.orig_read_dog_config(path_to_dog_config)


def mock_win32(monkeypatch, tmp_path, win_path, dog_config_contents: List[str]):
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setenv('USERNAME', 'dog_test_user')
    monkeypatch.setattr(Path, 'cwd', lambda: win_path)
    monkeypatch.setattr(os.path, 'isfile', lambda x: True)
    append_to_dog_config(tmp_path, dog_config_contents)
    mrdc = MockReadDogConfig(
        dog.read_dog_config, win_path / 'dog.config', tmp_path / 'dog.config'
    )
    monkeypatch.setattr(dog, 'read_dog_config', mrdc.mocked_read_dog_config)


def test_auto_mount_win32(
    call_main, basic_dog_config, tmp_path, mock_subprocess, monkeypatch
):
    win_path = PureWindowsPath('C:\\tmp\\test')
    mock_win32(monkeypatch, tmp_path, win_path, ['image=my_image'])
    call_main('my_inside_cmd')
    args_left = assert_docker_std_cmdline(mock_subprocess)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'my_image', ['my_inside_cmd']
    )
    args_left = assert_workdir_param(args_left, '/C/tmp/test')
    args_left = std_assert_hostname_param(args_left)
    args_left = assert_volume_params(args_left, [('/C', 'C:\\')])
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = assert_env_params(
        args_left,
        [
            'DOG_UID=1000',
            'DOG_GID=1000',
            'DOG_USER=dog_test_user',
            'DOG_GROUP=nodoggroup',
            'DOG_HOME=/home/dog_test_user',
            'DOG_AS_ROOT=False',
            f'DOG_VERSION={ACTUAL_DOG_VERSION}',
        ],
    )
    assert args_left == []


def test_perforce_win32(
    call_main, basic_dog_config, tmp_path, mock_subprocess, monkeypatch, home_temp_dir
):
    win_path = PureWindowsPath('C:\\tmp\\test')
    mock_win32(monkeypatch, tmp_path, win_path, ['image=my_image', 'auto-mount=False'])
    call_main('my_inside_cmd')
    args_left = assert_docker_std_cmdline(mock_subprocess)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'my_image', ['my_inside_cmd']
    )
    args_left = assert_workdir_param(args_left, '/C/tmp/test')
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = assert_env_params(
        args_left,
        [
            'DOG_UID=1000',
            'DOG_GID=1000',
            'DOG_USER=dog_test_user',
            'DOG_GROUP=nodoggroup',
            'DOG_HOME=/home/dog_test_user',
            'DOG_AS_ROOT=False',
            f'DOG_VERSION={ACTUAL_DOG_VERSION}',
        ],
    )
    assert args_left == []


@pytest.mark.parametrize(
    'device,usb_devices,expected_device_param',
    [
        ('', {}, []),
        ('/dev/foo_bar', {}, ['/dev/foo_bar']),
        ('', {'dev1': '1111:aaaa'}, ['/dev/bus/usb/001/004']),
        ('', {'dev1': '1111:aaaa'}, ['/dev/bus/usb/001/004', '/dev/bus/usb/002/013']),
        ('/dev/baz', {'dev1': '1111:aaaa'}, ['/dev/baz', '/dev/bus/usb/001/004']),
    ],
)
def test_device(
    basic_dog_config_with_image,
    call_main,
    tmp_path,
    mock_execvp,
    home_temp_dir,
    monkeypatch,
    device: str,
    usb_devices: dict,
    expected_device_param: str,
):
    def test_path(x):
        assert x == usb_devices['dev1']
        if device:
            usb_dev_paths = expected_device_param[1:]
        else:
            usb_dev_paths = expected_device_param
        return usb_dev_paths

    monkeypatch.setattr(UsbDevices, 'get_bus_paths', lambda _, x: test_path(x))

    update_dog_config(tmp_path, {USB_DEVICES: usb_devices})
    if device:
        update_dog_config(tmp_path, {DOG: {DEVICE: device}})
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'debian:latest', ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    args_left = assert_device_params(args_left, expected_device_param)
    assert args_left == []


@pytest.mark.parametrize(
    'volumes',
    [
        {'vol1': '/foo/bar:/foo/bar'},
        {'vol1': '/foo/bar:/foo/bar', 'ro_vol': '/my_path:/my_other_path:ro'},
    ],
)
def test_volumes(
    basic_dog_config_with_image,
    call_main,
    tmp_path,
    mock_execvp,
    home_temp_dir,
    volumes: dict,
):
    expected_volumes = []
    for vol in volumes.values():
        s = vol.split(':')
        inside = s[1] if len(s) < 3 else f'{s[1]}:{s[2]}'
        outside = s[0]
        expected_volumes.append((inside, outside))
    update_dog_config(tmp_path, {DOG: {DOG_CONFIG_FILE_VERSION: 2}, VOLUMES: volumes})
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'debian:latest', ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    args_left = assert_volume_params(args_left, expected_volumes)
    args_left = std_assert_volume_params(tmp_path, args_left)
    assert args_left == []


@pytest.mark.parametrize(
    'volumes_from',
    [
        {},
        {'container1': 'debian:latest'},
        {
            'container1': 'my.example.com/my-custom-dockers/my_tool:latest',
            'cont2': 'alpine:latest',
        },
        {
            'container1': 'my.example.com/my-custom-dockers/my_tool:latest',
            'cont2:ro': 'alpine:latest',
        },
    ],
)
def test_volumes_from(
    basic_dog_config_with_image,
    call_main,
    tmp_path,
    mock_execvp,
    home_temp_dir,
    volumes_from: dict,
):
    update_dog_config(tmp_path, {VOLUMES_FROM: volumes_from})
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'debian:latest', ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = assert_volumes_from_params(args_left, volumes_from.keys())
    assert args_left == []


@pytest.mark.parametrize('init', [True, False])
def test_init(
    basic_dog_config_with_image,
    call_main,
    tmp_path,
    mock_execvp,
    home_temp_dir,
    init: bool,
):
    update_dog_config(tmp_path, {DOG: {INIT: init}})
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'debian:latest', ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = std_assert_interactive(args_left)
    args_left = assert_init(args_left, init)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    assert args_left == []


def test_mac_address(
    basic_dog_config_with_image, call_main, tmp_path, mock_execvp, home_temp_dir
):
    append_to_dog_config(tmp_path, [f'{MAC_ADDRESS}=AA:BB:CC:DD:EE:FF'])
    call_main('echo', 'foo')
    args_left = assert_docker_std_cmdline(mock_execvp)
    args_left = assert_docker_image_and_cmd_inside_docker(
        args_left, 'debian:latest', ['echo', 'foo']
    )
    args_left = assert_workdir_param(args_left, get_workdir(tmp_path))
    args_left = std_assert_hostname_param(args_left)
    args_left = std_assert_interactive(args_left)
    args_left = std_assert_init(args_left)
    args_left = std_assert_env_params(home_temp_dir, args_left)
    args_left = std_assert_volume_params(tmp_path, args_left)
    args_left = assert_mac_address_param(args_left, 'AA:BB:CC:DD:EE:FF')
    assert args_left == []
