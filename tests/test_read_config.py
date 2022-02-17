import grp
import os
import platform
import pytest
from conftest import update_dog_config
from dog import (
    ARGS,
    AS_ROOT,
    AUTO_MOUNT,
    CONFIG_FILE,
    CWD,
    EXPOSED_DOG_VARIABLES,
    GID,
    GROUP,
    HOME,
    HOSTNAME,
    INTERACTIVE,
    PORTS,
    PULL,
    SANITY_CHECK_ALWAYS,
    SUDO_OUTSIDE_DOCKER,
    TERMINAL,
    UID,
    USER,
    USER_ENV_VARS,
    USER_ENV_VARS_IF_SET,
    VERBOSE,
    VOLUMES,
    read_config,
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


@pytest.fixture
def basic_dog_config_with_image(tmp_path, basic_dog_config):
    update_dog_config(tmp_path, {'dog': {'image': 'debian:latest'}})


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
    assert config[EXPOSED_DOG_VARIABLES] == [UID, GID, USER, GROUP, HOME, AS_ROOT]
    assert config[INTERACTIVE] is True
    assert config[PORTS] == {}
    assert config[PULL] is False
    assert config[SANITY_CHECK_ALWAYS] is False
    assert config[SUDO_OUTSIDE_DOCKER] is False
    assert config[TERMINAL] is False
    assert config[USER_ENV_VARS] == {}
    assert config[USER_ENV_VARS_IF_SET] == {}
    assert config[VERBOSE] is False
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

    update_dog_config(tmp_path, {'dog': {'interactive': False}})
    assert call_read_config()[INTERACTIVE] is False
    assert call_read_config('--interactive')[INTERACTIVE] is True
    assert call_read_config('-i')[INTERACTIVE] is True
    assert call_read_config('-it')[INTERACTIVE] is True


def test_terminal(call_read_config, basic_dog_config_with_image, tmp_path):
    assert call_read_config()[TERMINAL] is False
    assert call_read_config('--terminal')[TERMINAL] is True
    assert call_read_config('-t')[TERMINAL] is True
    assert call_read_config('-it')[TERMINAL] is True

    update_dog_config(tmp_path, {'dog': {'terminal': True}})
    assert call_read_config()[TERMINAL] is True
    assert call_read_config('--no-terminal')[TERMINAL] is False


def test_config_order(
    call_read_config, basic_dog_config_with_image, tmp_path, home_temp_dir
):
    assert call_read_config()[TERMINAL] is False
    assert call_read_config()[PORTS] == {}

    user_config_file(home_temp_dir, {'dog': {TERMINAL: True}, PORTS: {'80': '8080'}})
    assert call_read_config()[TERMINAL] is True
    assert call_read_config()[PORTS] == {'80': '8080'}

    update_dog_config(tmp_path, {'dog': {TERMINAL: False}, PORTS: {'80': '8888'}})
    assert call_read_config()[TERMINAL] is False
    assert call_read_config()[PORTS] == {'80': '8888'}

    assert call_read_config('--terminal')[TERMINAL] is True

    user_config_file(home_temp_dir, {PORTS: {'80': '80', '22': '222'}})
    assert call_read_config()[PORTS] == {'80': '8888', '22': '222'}
