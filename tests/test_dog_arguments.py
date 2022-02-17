import getpass
import os
import pytest
import re
import subprocess
import sys

from conftest import (
    ACTUAL_DOG_VERSION,
    DOG_PYTHON_UNDER_TEST,
    append_to_dog_config,
    update_dog_config,
)
from dog import DOG_CONFIG_FILE_VERSION, MAX_DOG_CONFIG_VERSION
from pathlib import Path


@pytest.fixture
def call_shell(call_centos7, tmp_path, my_dog, monkeypatch):
    if 'win32' in sys.platform:
        monkeypatch.setenv('DOG', f'"{DOG_PYTHON_UNDER_TEST}" "{my_dog}"')
    else:
        monkeypatch.setenv('DOG', f'{DOG_PYTHON_UNDER_TEST} {my_dog}')

    def call(shell_string: str):
        return subprocess.run(shell_string, shell=True, cwd=tmp_path)

    return call


def test_no_arguments_reports_help_on_stderr(call_dog, capfd):
    call_dog()
    captured = capfd.readouterr()
    assert 'usage:' in captured.err
    assert 'error' in captured.err


def test_dash_dash_help_reports_help_on_stdout(call_dog, capfd):
    call_dog('--help')
    captured = capfd.readouterr()
    assert 'usage:' in captured.out
    assert 'error' not in captured.err


def test_pull_latest_just_in_case(call_centos7):
    assert call_centos7('--pull', 'echo', 'Up-to-date') == 0


def test_user_is_me(call_centos7, capfd, uid):
    assert call_centos7('id') == 0
    captured = capfd.readouterr()
    assert f'uid={uid}({getpass.getuser()})' in captured.out


def test_as_root(call_centos7, capfd):
    call_centos7('--as-root', 'id')
    captured = capfd.readouterr()
    assert 'uid=0(root)' in captured.out


def test_pull_as_echo_argument(call_centos7, capstrip):
    # --pull should only be interpreted as a dog argument if it comes before the first
    # argument
    call_centos7('echo', '-n', '--pull')
    captured = capstrip.get()
    assert captured == ('--pull', '')


def test_version(call_dog, capfd):
    # --version should just return the current dog version
    call_dog('--version')
    captured = capfd.readouterr()
    assert re.match('dog version [0-9]+', captured.out)


def test_verbose(call_centos7, capfd):
    # --verbose should report the actual setup
    call_centos7('--verbose', 'id')
    captured = capfd.readouterr()
    assert 'Dog Config' in captured.out
    assert "'verbose': True" in captured.out


def test_stdin_testing_works(call_shell, capstrip):
    # Just verifying that my stdin testing works before testing it with dog.
    call_shell('echo hello world | cat -')
    captured = capstrip.get()
    assert captured == ('hello world', '')


def test_stdin(call_shell, capstrip, dog_env):
    """stdin should be available from inside dog."""
    call_shell(f'echo hello world | {dog_env} cat')
    captured = capstrip.get()
    assert captured == ('hello world', '')


def test_auto_mount_works(call_centos7, capstrip):
    # auto-mount is on by default, and should therefore show the files in the current
    # directory.

    call_centos7('ls')
    captured = capstrip.get()
    assert captured == ('dog.config', '')


def test_disabled_auto_mount(call_centos7, capstrip, tmp_path):
    # disable auto-mount and make sure that we do not see the files in the
    # current directory.
    append_to_dog_config(tmp_path, ['auto-mount=False'])
    call_centos7('ls')
    captured = capstrip.get()
    assert captured == ('', '')


def test_volumes(call_centos7, capstrip, tmp_path, system_temp_dir):
    # Try adding the "system temp dir" as a volume in the dog.config.
    append_to_dog_config(
        tmp_path, ['[volumes]', f'/dog_test_of_system_temp={system_temp_dir}']
    )
    call_centos7('mountpoint', '/dog_test_of_system_temp')
    captured = capstrip.get()
    assert captured == ('/dog_test_of_system_temp is a mountpoint', '')


def test_dog_is_too_old_for_minimum_version(call_centos7, tmp_path, capstrip):
    append_to_dog_config(tmp_path, ['minimum-version=999999'])
    call_centos7('ls')
    captured = capstrip.get()
    expected_error = (
        'Minimum version required (999999) is greater than your dog version'
        f' ({ACTUAL_DOG_VERSION}) - please upgrade dog'
    )
    assert expected_error in captured[1]


def test_dog_config_file_version_is_unknown(call_centos7, tmp_path, capstrip):
    update_dog_config(
        tmp_path, {'dog': {DOG_CONFIG_FILE_VERSION: MAX_DOG_CONFIG_VERSION + 1}}
    )
    call_centos7('ls')
    captured = capstrip.get()
    expected_error = (
        'Do not know how to interpret a dog.config file with version'
        f' {MAX_DOG_CONFIG_VERSION+1}'
        f' (max file version supported: {MAX_DOG_CONFIG_VERSION})'
    )
    assert expected_error in captured[1]


def test_dog_is_minimum_version(call_centos7, tmp_path, capstrip):
    append_to_dog_config(tmp_path, [f'minimum-version={ACTUAL_DOG_VERSION}'])
    call_centos7('echo ok')
    captured = capstrip.get()
    assert captured == ('ok', '')


def test_dog_is_newer_than_minimum_version(call_centos7, tmp_path, capstrip):
    append_to_dog_config(tmp_path, [f'minimum-version={ACTUAL_DOG_VERSION - 1}'])
    call_centos7('echo ok')
    captured = capstrip.get()
    assert captured == ('ok', '')


def test_no_image_given(call_dog, basic_dog_config, tmp_path, capfd):
    call_dog('echo ok')
    assert 'No image specified' in capfd.readouterr().err


def test_dog_config_not_found(my_dog, system_temp_dir, capfd):
    # If a dog.config is found, report an error.
    # We run this test in the system_temp_dir to be more sure that no-one has a
    # dog.config file somewhere in the parent directories.

    for parent in Path(system_temp_dir).parents:
        assert not (parent / 'dog.config').exists(), (
            'Pre-conditions for this test failed - we expect no dog.config',
            f' files in the parent directories of {system_temp_dir}',
        )

    cmd_line = [DOG_PYTHON_UNDER_TEST, str(my_dog), 'echo', 'ok']
    subprocess.run(cmd_line, cwd=system_temp_dir)
    assert 'ERROR' in capfd.readouterr().err


@pytest.mark.skipif(
    'TEAMCITY_PROJECT_NAME' not in os.environ,
    reason='This test only works inside Demant (sorry!)',
)
def test_pull_latest_demant_debian(basic_dog_config, call_dog, tmp_path, capstrip):
    # This test only exists to pull the latest image before the next test
    # - this is to make sure that the test does not fail due to lots of
    # pullling layer ....blah.balh... output.
    append_to_dog_config(
        tmp_path,
        [
            'registry=artifactory.oticon.com/demant-docker-local',
            'image=demant-debian:buster-20211011-slim',
        ],
    )
    call_dog('echo', 'ok')


@pytest.mark.skipif(
    'TEAMCITY_PROJECT_NAME' not in os.environ,
    reason='This test only works inside Demant (sorry!)',
)
def test_registry(basic_dog_config, call_dog, tmp_path, capstrip):
    append_to_dog_config(
        tmp_path,
        [
            'registry=artifactory.oticon.com/demant-docker-local',
            'image=demant-debian:buster-20211011-slim',
        ],
    )
    call_dog('echo', 'ok')
    assert capstrip.get() == ('ok', '')


def test_bad_registry(call_centos7, tmp_path, capfd):
    append_to_dog_config(tmp_path, ['registry=this-is-a-bad-registry'])
    call_centos7('echo', 'ok')
    assert 'Unable to find image' in capfd.readouterr().err


def test_user_env_vars(call_centos7, tmp_path, capfd, monkeypatch):
    # First call without the local variable
    monkeypatch.delenv('MY_ENV_VAR', raising=False)
    call_centos7('echo', 'MY_ENV_VAR is $MY_ENV_VAR')
    captured = capfd.readouterr()
    assert 'MY_ENV_VAR is' in captured.out

    # Then set the local variable - but still do not preserve it
    monkeypatch.setenv('MY_ENV_VAR', 'this is preserved')
    call_centos7('echo', 'MY_ENV_VAR is $MY_ENV_VAR')
    captured = capfd.readouterr()
    assert 'MY_ENV_VAR is' in captured.out

    # Then preserve the local variable - expect it to be preserved now
    append_to_dog_config(
        tmp_path,
        [
            'exposed-dog-variables=gid,uid,user,group,home,as-root,preserve-env',
            'user-env-vars=MY_ENV_VAR',
            'preserve-env=MY_ENV_VAR',
        ],
    )
    call_centos7('echo', 'MY_ENV_VAR is $MY_ENV_VAR')
    captured = capfd.readouterr()
    assert 'MY_ENV_VAR is this is preserved' in captured.out


def test_preserve_non_existing_env(call_centos7, tmp_path, capfd, monkeypatch):
    monkeypatch.delenv('NON_EXISTING_VAR', raising=False)
    append_to_dog_config(
        tmp_path,
        [
            'exposed-dog-variables=gid,uid,user,group,home,as-root,preserve-env',
            'user-env-vars-if-set=MY_ENV_VAR',
            'preserve-env=NON_EXISTING_VAR',
        ],
    )
    assert call_centos7('echo', 'NON_EXISTING_VAR is $NON_EXISTING_VAR') == 0
    captured = capfd.readouterr()
    assert 'NON_EXISTING_VAR is' in captured.out
