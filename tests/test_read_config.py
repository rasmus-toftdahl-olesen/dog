import os
import platform
import sys

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
    INCLUDE_DOG_CONFIG,
    INTERACTIVE,
    MAX_DOG_CONFIG_VERSION,
    MINIMUM_VERSION,
    NETWORK,
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
    UsbDevices,
    VERBOSE,
    VERSION,
    VOLUMES,
    VOLUMES_FROM,
    read_config,
)
from tests.conftest import is_windows


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


@pytest.mark.skipif(
    is_windows(),
    reason='This test does not work on windows since it uses'
    'the grp python module which does not exist on windows',
)
def test_default_config(
    call_read_config, basic_dog_config_with_image, tmp_path, dummy_dog_args
):
    import grp

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


def test_volumes_v1_conditional(
    call_read_config, basic_dog_config_with_image, tmp_path, monkeypatch
):
    update_dog_config(
        tmp_path,
        {
            DOG: {AUTO_MOUNT: False},
            VOLUMES: {
                '?/test_path': str(tmp_path / 'not_there'),
                '/there': str(tmp_path / 'there'),
            },
        },
    )
    monkeypatch.setattr(os.path, 'exists', lambda x: x == str(tmp_path / 'there'))
    assert call_read_config()[VOLUMES] == {'/there': str(tmp_path / 'there')}


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

    update_dog_config(tmp_path, {VOLUMES: {'vol3': '~/.ssh:${home}/.ssh:ro'}})
    assert call_read_config()[VOLUMES] == {
        '/FOO': '/bar',
        '/foobar': '/baz',
        str(home_temp_dir / '.ssh:ro'): str(home_temp_dir / '.ssh'),
    }


def test_volumes_v2_conditional(
    call_read_config, basic_dog_config_with_image, tmp_path, monkeypatch
):
    update_dog_config(
        tmp_path,
        {
            DOG: {AUTO_MOUNT: False, 'dog-config-file-version': '2'},
            VOLUMES: {
                'vol1?': f'{tmp_path / "not_there"}:/test_path',
                'vol2': f'{tmp_path / "there"}:/there',
            },
        },
    )
    monkeypatch.setattr(os.path, 'exists', lambda x: x == str(tmp_path / 'there'))
    assert call_read_config()[VOLUMES] == {'/there': str(tmp_path / 'there')}


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


@pytest.mark.parametrize('network', ['host', 'none', 'mynetwork'])
def test_network_in_dog_config(
    call_read_config, basic_dog_config_with_image, tmp_path, network: str
):
    update_dog_config(tmp_path, {DOG: {NETWORK: network}})
    assert call_read_config()[NETWORK] == network


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
    assert call_read_config()[DEVICE] == usb_dev_path1

    update_dog_config(tmp_path, {USB_DEVICES: {'dev2': dev2}})
    assert call_read_config()[DEVICE] == usb_dev_path1 + usb_dev_path2

    update_dog_config(tmp_path, {USB_DEVICES: {'dev3': dev3}})
    assert call_read_config()[DEVICE] == usb_dev_path1 + usb_dev_path2 + usb_dev_path3

    my_dev = '/dev/my_strange_dev'
    update_dog_config(tmp_path, {DOG: {DEVICE: my_dev}})
    assert (
        call_read_config()[DEVICE]
        == [f'{my_dev}'] + usb_dev_path1 + usb_dev_path2 + usb_dev_path3
    )


def test_volumes_from(call_read_config, basic_dog_config_with_image, tmp_path):
    assert call_read_config()[VOLUMES_FROM] == {}

    update_dog_config(tmp_path, {VOLUMES_FROM: {'vol1': 'my_tool'}})
    assert call_read_config()[VOLUMES_FROM] == {'vol1': 'my_tool'}

    update_dog_config(tmp_path, {VOLUMES_FROM: {'vol2': 'path/to/other_tool'}})
    assert call_read_config()[VOLUMES_FROM] == {
        'vol1': 'my_tool',
        'vol2': 'path/to/other_tool',
    }


def test_volumes_from_with_registry_subst(
    call_read_config, basic_v2_dog_config_with_image, tmp_path
):
    assert call_read_config()[VOLUMES_FROM] == {}

    update_dog_config(
        tmp_path,
        {
            DOG: {'registry': 'gitlab.ci.demant.com:4567/dockers'},
            VOLUMES_FROM: {'vol1': '${registry}/my_tool:latest'},
        },
    )
    assert call_read_config()[VOLUMES_FROM] == {
        'vol1': 'gitlab.ci.demant.com:4567/dockers/my_tool:latest'
    }

    update_dog_config(
        tmp_path,
        {
            DOG: {'custom_registry': 'my.example.com/my-custom-dockers'},
            VOLUMES_FROM: {'vol1': '${custom_registry}/my_tool:latest'},
        },
    )
    assert call_read_config()[VOLUMES_FROM] == {
        'vol1': 'my.example.com/my-custom-dockers/my_tool:latest'
    }


def test_volumes_from_with_failing_registry_subst(
    call_read_config, basic_v2_dog_config_with_image, tmp_path, capsys
):
    update_dog_config(tmp_path, {VOLUMES_FROM: {'vol1': '${registry}/my_tool:latest'}})

    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    assert '"registry" used in "${registry}" not found in config' in captured.err


def test_include_missing_file(
    call_read_config, basic_dog_config_with_image, tmp_path, capsys
):
    missing_file_name = 'missing-include.config'
    update_dog_config(tmp_path, {DOG: {INCLUDE_DOG_CONFIG: missing_file_name}})

    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    expected_error = (
        f'Could not find "{missing_file_name}" used in {INCLUDE_DOG_CONFIG} here:'
        f' {tmp_path / missing_file_name}'
    )
    assert expected_error in captured.err


def test_include_non_config_file(
    call_read_config, basic_dog_config_with_image, tmp_path, capsys
):
    empty_config_file = 'empty.config'
    update_dog_config(tmp_path, {DOG: {INCLUDE_DOG_CONFIG: empty_config_file}})
    update_dog_config(tmp_path / empty_config_file, {})

    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    expected_error = f'Could not find [dog] in {tmp_path / empty_config_file}'
    assert expected_error in captured.err


def test_include_valid_config_file(
    call_read_config, basic_dog_config_with_image, tmp_path
):
    empty_config_file = 'empty.config'
    update_dog_config(tmp_path, {DOG: {INCLUDE_DOG_CONFIG: empty_config_file}})
    update_dog_config(
        tmp_path / empty_config_file, {DOG: {'dog-config-file-version': '1'}}
    )

    assert INCLUDE_DOG_CONFIG not in call_read_config()


def test_versions_in_included_file(
    call_read_config, basic_dog_config_with_image, tmp_path, capsys
):
    empty_config_file = 'empty.config'
    update_dog_config(tmp_path, {DOG: {INCLUDE_DOG_CONFIG: empty_config_file}})
    update_dog_config(tmp_path / empty_config_file, {DOG: {}})

    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    expected_error = (
        'Do not know how to handle a dog.config file without'
        ' dog-config-file-version specified'
    )
    assert expected_error in captured.err

    update_dog_config(
        tmp_path / empty_config_file,
        {
            DOG: {
                'dog-config-file-version': '1',
                MINIMUM_VERSION: ACTUAL_DOG_VERSION + 5,
            }
        },
    )

    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    expected_error = (
        f'Minimum version required ({ACTUAL_DOG_VERSION + 5}) is greater than your'
        f' dog version ({ACTUAL_DOG_VERSION}) - please upgrade dog'
    )
    assert expected_error in captured.err


def test_include_with_path(
    call_read_config, basic_dog_config_with_image, tmp_path, tmp_path_factory
):
    test_dir = tmp_path_factory.mktemp('test_dir')
    empty_config_file = test_dir / 'empty.config'
    update_dog_config(tmp_path, {DOG: {INCLUDE_DOG_CONFIG: str(empty_config_file)}})
    update_dog_config(empty_config_file, {DOG: {'dog-config-file-version': '1'}})

    assert INCLUDE_DOG_CONFIG not in call_read_config()

    relative_path = empty_config_file.relative_to(tmp_path.parent)
    update_dog_config(tmp_path, {DOG: {INCLUDE_DOG_CONFIG: f'../{relative_path}'}})

    assert INCLUDE_DOG_CONFIG not in call_read_config()


def test_multi_level_include(call_read_config, basic_dog_config_with_image, tmp_path):
    inc_config_1 = tmp_path / 'config1.config'
    inc_config_2 = tmp_path / 'config2.config'
    update_dog_config(tmp_path, {DOG: {INCLUDE_DOG_CONFIG: str(inc_config_1)}})
    update_dog_config(
        inc_config_1,
        {DOG: {'dog-config-file-version': '1', INCLUDE_DOG_CONFIG: str(inc_config_2)}},
    )
    update_dog_config(inc_config_2, {DOG: {'dog-config-file-version': '1'}})

    assert INCLUDE_DOG_CONFIG not in call_read_config()


def test_include_config_order(
    call_read_config, basic_dog_config_with_image, tmp_path, home_temp_dir
):
    user_config_file(
        home_temp_dir,
        {
            DOG: {
                'dog-config-file-version': '1',
                'user1': 'user1',
                'user_common': 'user1',
                'global_common': 'user1',
                INCLUDE_DOG_CONFIG: 'user2.config',
            }
        },
    )
    update_dog_config(
        home_temp_dir / 'user2.config',
        {
            DOG: {
                'dog-config-file-version': 1,
                'user2': 'user2',
                'user_common': 'user2',
                'global_common': 'user2',
            }
        },
    )

    assert call_read_config()['user1'] == 'user1'
    assert call_read_config()['user2'] == 'user2'
    assert call_read_config()['user_common'] == 'user1'
    assert call_read_config()['global_common'] == 'user1'

    update_dog_config(
        tmp_path,
        {
            DOG: {
                INCLUDE_DOG_CONFIG: 'dog2.config',
                'dog': 'dog',
                'dog_common': 'dog',
                'global_common': 'dog',
            }
        },
    )

    update_dog_config(
        tmp_path / 'dog2.config',
        {
            DOG: {
                'dog-config-file-version': 1,
                'dog2': 'dog2',
                'dog_common': 'dog2',
                'global_common': 'dog2',
            }
        },
    )

    assert call_read_config()['user1'] == 'user1'
    assert call_read_config()['user2'] == 'user2'
    assert call_read_config()['user_common'] == 'user1'
    assert call_read_config()['dog'] == 'dog'
    assert call_read_config()['dog2'] == 'dog2'
    assert call_read_config()['dog_common'] == 'dog'
    assert call_read_config()['global_common'] == 'dog'


def test_user_sections(call_read_config, basic_dog_config_with_image, tmp_path):
    update_dog_config(tmp_path, {'vars': {'test1': 'foo', 'test2': 'bar'}})

    config = call_read_config()
    assert config['vars_test1'] == 'foo'
    assert config['vars_test2'] == 'bar'

    update_dog_config(tmp_path, {'vars': {'test3': 42}, 'my-vars': {'test': 'foobar'}})

    config = call_read_config()
    assert config['vars_test1'] == 'foo'
    assert config['vars_test2'] == 'bar'
    assert config['vars_test3'] == '42'
    assert config['my-vars_test'] == 'foobar'


def test_variable_subst(
    call_read_config, basic_v2_dog_config_with_image, tmp_path, capsys
):
    update_dog_config(
        tmp_path, {DOG: {'test1': 'foo', 'test2': '${test1}_bar', '${test1}': 'baz'}}
    )

    config = call_read_config()
    assert config['test1'] == 'foo'
    assert config['test2'] == 'foo_bar'
    assert config['foo'] == 'baz'
    assert '${test1}' not in config


def test_variable_multi_subst(
    call_read_config, basic_v2_dog_config_with_image, tmp_path, capsys
):
    update_dog_config(
        tmp_path,
        {DOG: {'t1': 'foo', 't2': 'bar', '${t1}_${t2}': 'baz', 'foo': '${t1}${t2}'}},
    )

    config = call_read_config()
    assert config['t1'] == 'foo'
    assert config['t2'] == 'bar'
    assert config['foo_bar'] == 'baz'
    assert config['foo'] == 'foobar'
    assert '${t1}_${t2}' not in config


def test_variable_subst_not_found_value(
    call_read_config, basic_v2_dog_config_with_image, tmp_path, capsys
):
    update_dog_config(tmp_path, {DOG: {'${not_there}': 'foo'}})

    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    expected_error = '"not_there" used in "${not_there}" not found in config'
    assert expected_error in captured.err


def test_variable_subst_not_found_key(
    call_read_config, basic_v2_dog_config_with_image, tmp_path, capsys
):
    update_dog_config(tmp_path, {DOG: {'test_not_there': '${not_there}'}})

    with pytest.raises(SystemExit):
        call_read_config()
    captured = capsys.readouterr()
    expected_error = '"not_there" used in "${not_there}" not found in config'
    assert expected_error in captured.err


def test_subst_for_values_from(
    call_read_config, basic_v2_dog_config_with_image, tmp_path
):
    update_dog_config(
        tmp_path,
        {
            DOG: {'registry': 'my.example.com/my-custom-dockers'},
            'tool-versions': {'my_tool': '220301.1'},
            VOLUMES_FROM: {
                'my_tool_${tool-versions_my_tool}': (
                    '${registry}/my_tool:${tool-versions_my_tool}'
                )
            },
        },
    )

    assert call_read_config()[VOLUMES_FROM] == {
        'my_tool_220301.1': 'my.example.com/my-custom-dockers/my_tool:220301.1'
    }


def test_subst_for_usb_devices(
    call_read_config, basic_v2_dog_config_with_image, tmp_path
):
    update_dog_config(
        tmp_path,
        {
            'usb': {'vendor1': 'abcd', 'product1': '4242'},
            USB_DEVICES: {'dev1': '${usb_vendor1}:${usb_product1}'},
        },
    )

    assert call_read_config()[USB_DEVICES] == {'dev1': 'abcd:4242'}


def test_env_without_user_win32(
    call_read_config, basic_dog_config_with_image, tmp_path, monkeypatch
):
    # Disable auto-mount to make this test pass on unix- otherwise the test
    # will end up trying to use a unix path as a window path during auto-mount
    update_dog_config(tmp_path, {DOG: {AUTO_MOUNT: 'False'}})
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.delenv('USERNAME', raising=False)
    assert call_read_config()[USER] == 'nobody'


@pytest.mark.skipif(
    is_windows(),
    reason='This test does not work on windows since it uses the'
    'grp python module which does not exist on windows',
)
def test_env_without_user_unix(
    call_read_config, basic_dog_config_with_image, tmp_path, monkeypatch
):
    import pwd

    def my_pwd_getgetpwuid():
        raise KeyError('This is the test_env_without_user_unix test')

    monkeypatch.delenv('USER', raising=False)
    monkeypatch.setattr(pwd, 'getgetpwuid', my_pwd_getgetpwuid)
    assert call_read_config()[USER] == 'nobody'
