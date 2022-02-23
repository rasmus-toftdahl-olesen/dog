import grp
import os
import platform
import pytest
from conftest import ACTUAL_DOG_VERSION, update_dog_config
from dog import (
    ARGS,
    AS_ROOT,
    AUTO_MOUNT,
    CONFIG_FILE,
    CWD,
    DEVICE,
    DOG,
    DOG_CONFIG_FILE_VERSION,
    EXPOSED_DOG_VARIABLES,
    GID,
    GROUP,
    HOME,
    HOSTNAME,
    INTERACTIVE,
    MAX_DOG_CONFIG_VERSION,
    MINIMUM_VERSION,
    PORTS,
    PULL,
    SANITY_CHECK_ALWAYS,
    SUDO_OUTSIDE_DOCKER,
    TERMINAL,
    UID,
    USB_DEVICES,
    USER,
    USER_ENV_VARS,
    USER_ENV_VARS_IF_SET,
    VERBOSE,
    VERSION,
    VOLUMES,
    read_config,
    UsbDevices,
)


@pytest.fixture
def dummy_dog_args():
    return ['echo', 'foo']


@pytest.fixture
def call_read_config(my_dog, tmp_path, monkeypatch, dummy_dog_args):
    def call(*args: object):
        argv = [str(my_dog)]
        for arg in args:
            argv.append(str(arg))
        argv.extend(dummy_dog_args)
        with monkeypatch.context() as m:
            m.chdir(tmp_path)
            return read_config(argv)

    yield call


def user_config_file(home_temp_dir, config):
    conf_file = home_temp_dir / ('.' + CONFIG_FILE)
    update_dog_config(conf_file, config)


def test_default_config(
    call_read_config, basic_dog_config_with_image, tmp_path, dummy_dog_args
):
    config = call_read_config()
    # Values not modified by environment
    assert config[AS_ROOT] is False
    assert config[AUTO_MOUNT] is True
    assert config[EXPOSED_DOG_VARIABLES] == [
        UID,
        GID,
        USER,
        GROUP,
        HOME,
        AS_ROOT,
        VERSION,
    ]
    assert config[INTERACTIVE] is True
    assert config[PORTS] == {}
    assert config[PULL] is False
    assert config[SANITY_CHECK_ALWAYS] is False
    assert config[SUDO_OUTSIDE_DOCKER] is False
    assert config[TERMINAL] is False
    assert config[USER_ENV_VARS] == {}
    assert config[USER_ENV_VARS_IF_SET] == {}
    assert config[VERBOSE] is False
    assert config[VERSION] == ACTUAL_DOG_VERSION
    # Values modified by current environment
    assert config[ARGS] == dummy_dog_args
    assert config[CWD] == tmp_path
    assert config[GID] == os.getgid()
    assert config[GROUP] == grp.getgrgid(os.getgid()).gr_name
    assert config[HOME] == os.getenv('HOME')
    assert config[HOSTNAME] == platform.node()
    assert config[UID] == os.getuid()
    assert config[USER] == os.getenv('USER')
    assert config[VOLUMES] == {''.join(tmp_path.parts[:2]): ''.join(tmp_path.parts[:2])}


def test_interactive(call_read_config, basic_dog_config_with_image, tmp_path):
    assert call_read_config()[INTERACTIVE] is True
    assert call_read_config('--not-interactive')[INTERACTIVE] is False

    update_dog_config(tmp_path, {DOG: {'interactive': False}})
    assert call_read_config()[INTERACTIVE] is False
    assert call_read_config('--interactive')[INTERACTIVE] is True
    assert call_read_config('-i')[INTERACTIVE] is True
    assert call_read_config('-it')[INTERACTIVE] is True


def test_terminal(call_read_config, basic_dog_config_with_image, tmp_path):
    assert call_read_config()[TERMINAL] is False
    assert call_read_config('--terminal')[TERMINAL] is True
    assert call_read_config('-t')[TERMINAL] is True
    assert call_read_config('-it')[TERMINAL] is True

    update_dog_config(tmp_path, {DOG: {'terminal': True}})
    assert call_read_config()[TERMINAL] is True
    assert call_read_config('--no-terminal')[TERMINAL] is False


def test_config_order(
    call_read_config, basic_dog_config_with_image, tmp_path, home_temp_dir
):
    assert call_read_config()[TERMINAL] is False
    assert call_read_config()[PORTS] == {}

    user_config_file(
        home_temp_dir,
        {DOG: {'dog-config-file-version': '1', TERMINAL: True}, PORTS: {'80': '8080'}},
    )
    assert call_read_config()[TERMINAL] is True
    assert call_read_config()[PORTS] == {'80': '8080'}

    update_dog_config(tmp_path, {DOG: {TERMINAL: False}, PORTS: {'80': '8888'}})
    assert call_read_config()[TERMINAL] is False
    assert call_read_config()[PORTS] == {'80': '8888'}

    assert call_read_config('--terminal')[TERMINAL] is True

    user_config_file(home_temp_dir, {PORTS: {'80': '80', '22': '222'}})
    assert call_read_config()[PORTS] == {'80': '8888', '22': '222'}


def test_volumes_v1(
    call_read_config, basic_dog_config_with_image, tmp_path, home_temp_dir
):
    update_dog_config(tmp_path, {DOG: {AUTO_MOUNT: False}})
    assert call_read_config()[VOLUMES] == {}

    update_dog_config(tmp_path, {VOLUMES: {'/foo': '/bar'}})
    assert call_read_config()[VOLUMES] == {'/foo': '/bar'}

    update_dog_config(tmp_path, {VOLUMES: {'/Foo': '/bar'}})
    assert call_read_config()[VOLUMES] == {'/foo': '/bar'}

    update_dog_config(tmp_path, {VOLUMES: {'/FOO': '/bar'}})
    assert call_read_config()[VOLUMES] == {'/foo': '/bar'}

    update_dog_config(tmp_path, {VOLUMES: {'/FOO': '/bar', '/foobar': '/baz'}})
    assert call_read_config()[VOLUMES] == {'/foo': '/bar', '/foobar': '/baz'}

    update_dog_config(tmp_path, {VOLUMES: {'$home/.ssh:ro': '~/.ssh'}})
    assert call_read_config()[VOLUMES] == {
        '/foo': '/bar',
        '/foobar': '/baz',
        str(home_temp_dir / '.ssh:ro'): str(home_temp_dir / '.ssh'),
    }


def test_volumes_v2(
    call_read_config, basic_dog_config_with_image, tmp_path, home_temp_dir
):
    update_dog_config(
        tmp_path, {DOG: {AUTO_MOUNT: False, 'dog-config-file-version': '2'}}
    )
    assert call_read_config()[VOLUMES] == {}

    update_dog_config(tmp_path, {VOLUMES: {'vol1': '/bar:/foo'}})
    assert call_read_config()[VOLUMES] == {'/foo': '/bar'}

    update_dog_config(tmp_path, {VOLUMES: {'vol1': '/bar:/Foo'}})
    assert call_read_config()[VOLUMES] == {'/Foo': '/bar'}

    update_dog_config(tmp_path, {VOLUMES: {'vol1': '/bar:/FOO'}})
    assert call_read_config()[VOLUMES] == {'/FOO': '/bar'}

    update_dog_config(
        tmp_path, {VOLUMES: {'vol1': '/bar:/FOO', 'vol2': '/baz:/foobar'}}
    )
    assert call_read_config()[VOLUMES] == {'/FOO': '/bar', '/foobar': '/baz'}

    update_dog_config(tmp_path, {VOLUMES: {'vol3': '~/.ssh:$home/.ssh:ro'}})
    assert call_read_config()[VOLUMES] == {
        '/FOO': '/bar',
        '/foobar': '/baz',
        str(home_temp_dir / '.ssh:ro'): str(home_temp_dir / '.ssh'),
    }


def test_volumes_v2_using_v1_format(
    call_read_config, basic_dog_config_with_image, tmp_path, capsys
):
    update_dog_config(
        tmp_path, {DOG: {AUTO_MOUNT: False, 'dog-config-file-version': '2'}}
    )

    update_dog_config(tmp_path, {VOLUMES: {'/foo': '/bar'}})
    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    assert '"/foo=/bar" found in volumes' in captured.err


def test_dog_is_too_old_for_minimum_version(
    call_read_config, basic_dog_config_with_image, tmp_path, capsys
):
    update_dog_config(tmp_path, {DOG: {MINIMUM_VERSION: ACTUAL_DOG_VERSION + 5}})
    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    expected_error = (
        f'Minimum version required ({ACTUAL_DOG_VERSION + 5}) is greater than your'
        f' dog version ({ACTUAL_DOG_VERSION}) - please upgrade dog'
    )
    assert expected_error in captured.err


@pytest.mark.parametrize('file_version', [-1, MAX_DOG_CONFIG_VERSION + 1])
def test_dog_config_file_version_is_unknown(
    call_read_config, basic_dog_config_with_image, tmp_path, capsys, file_version: int
):
    update_dog_config(tmp_path, {DOG: {DOG_CONFIG_FILE_VERSION: file_version}})
    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    expected_error = (
        'Do not know how to interpret a dog.config file with version'
        f' {file_version}'
        f' (max file version supported: {MAX_DOG_CONFIG_VERSION})'
    )
    assert expected_error in captured.err


@pytest.mark.parametrize('minimum_version', range(1, ACTUAL_DOG_VERSION))
def test_dog_is_minimum_version_or_newer(
    call_read_config, basic_dog_config_with_image, tmp_path, minimum_version: int
):
    update_dog_config(tmp_path, {DOG: {MINIMUM_VERSION: minimum_version}})
    call_read_config()


def test_usb_devices(
    call_read_config, basic_dog_config_with_image, tmp_path, monkeypatch
):
    assert call_read_config()[USB_DEVICES] == {}
    assert DEVICE not in call_read_config()

    dev1 = '1111:aaaa'
    dev2 = '2222:aaaa'
    dev3 = 'cccc:dddd'
    usb_dev_path1 = ['/dev/bus/usb/001/004']
    usb_dev_path2 = ['/dev/bus/usb/002/013']
    usb_dev_path3 = ['/dev/bus/usb/002/010', '/dev/bus/usb/001/002']

    def test_path(x):
        if x == dev1:
            return usb_dev_path1
        elif x == dev2:
            return usb_dev_path2
        elif x == dev3:
            return usb_dev_path3
        assert False

    monkeypatch.setattr(UsbDevices, 'get_bus_paths', lambda _, x: test_path(x))

    update_dog_config(tmp_path, {USB_DEVICES: {'dev1': dev1}})
    assert call_read_config()[DEVICE] == usb_dev_path1[0]

    update_dog_config(tmp_path, {USB_DEVICES: {'dev2': dev2}})
    assert call_read_config()[DEVICE] == f'{usb_dev_path1[0]}:{usb_dev_path2[0]}'

    update_dog_config(tmp_path, {USB_DEVICES: {'dev3': dev3}})
    assert (
        call_read_config()[DEVICE]
        == f'{usb_dev_path1[0]}:{usb_dev_path2[0]}:{":".join(usb_dev_path3)}'
    )

    my_dev = '/dev/my_strange_dev'
    update_dog_config(tmp_path, {DOG: {DEVICE: my_dev}})
    assert (
        call_read_config()[DEVICE]
        == f'{my_dev}:{usb_dev_path1[0]}:{usb_dev_path2[0]}:{":".join(usb_dev_path3)}'
    )
