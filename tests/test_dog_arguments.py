import getpass
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from dog import VERSION as ACTUAL_DOG_VERSION

DOG_PYTHON_UNDER_TEST = os.getenv('DOG_PYTHON_UNDER_TEST', sys.executable)


@pytest.fixture
def capstrip(capfd):
    class CapStrip:
        def get(self) -> Tuple[str, str]:
            out, err = capfd.readouterr()
            out, err = out.strip(), err.strip()
            return out, err

    return CapStrip()


@pytest.fixture
def uid() -> int:
    if 'win32' in sys.platform:
        return 1000
    else:
        return os.getuid()


@pytest.fixture
def my_dog() -> Path:
    return (Path(__file__).parent.parent / 'dog.py').absolute()


@pytest.fixture
def call_dog(my_dog, tmp_path):
    def call(*args: object):
        cmd_line = [DOG_PYTHON_UNDER_TEST, str(my_dog)]
        for arg in args:
            cmd_line.append(str(arg))
        return subprocess.run(cmd_line, cwd=tmp_path).returncode

    yield call


@pytest.fixture
def call_centos7(call_dog, tmp_path):
    dog_config = tmp_path / 'dog.config'
    dog_config.write_text('[dog]\nfull-image=rtol/centos-for-dog\n')
    return call_dog


@pytest.fixture
def call_shell(call_centos7, tmp_path, my_dog, monkeypatch):
    if 'win32' in sys.platform:
        monkeypatch.setenv('DOG', f'"{DOG_PYTHON_UNDER_TEST}" "{my_dog}"')
    else:
        monkeypatch.setenv('DOG', f'{DOG_PYTHON_UNDER_TEST} {my_dog}')

    def call(shell_string: str):
        return subprocess.run(shell_string, shell=True, cwd=tmp_path)

    return call


@pytest.fixture
def dog_env():
    if 'win32' in sys.platform:
        return '%DOG%'
    else:
        return '$DOG'


def append_to_dog_config(tmp_path: Path, extra_dog_config: str):
    dog_config = tmp_path / 'dog.config'
    old_config = dog_config.read_text()
    new_config = old_config + extra_dog_config
    dog_config.write_text(new_config)


@pytest.fixture
def system_temp_dir() -> str:
    if sys.platform == 'win32':
        basedir = os.environ['TEMP']
    else:
        basedir = os.getenv('RUNNER_TEMP', '/tmp')
    ret: Path = Path(tempfile.mktemp('dog_tests', 'dog_tests', basedir))
    ret.mkdir(parents=True, exist_ok=False)
    yield str(ret)
    os.removedirs(str(ret))


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
    '''--pull should only be interpreted as an dog argument if it comes before the first argument'''
    call_centos7('echo', '-n', '--pull')
    captured = capstrip.get()
    assert captured == ('--pull', '')


def test_version(call_dog, capfd):
    '''--version should just return the current dog version'''
    call_dog('--version')
    captured = capfd.readouterr()
    assert re.match('dog version [0-9]+', captured.out)


def test_verbose(call_centos7, capfd):
    '''--verbose should report the actual setup'''
    call_centos7('--verbose', 'id')
    captured = capfd.readouterr()
    assert f'Dog Config' in captured.out
    assert "'verbose': True" in captured.out


def test_stdin_testing_works(call_shell, capstrip):
    '''Just verifying that my stdin testing works before testing it with dog.'''
    call_shell('echo hello world | cat -')
    captured = capstrip.get()
    assert captured == ('hello world', '')


def test_stdin(call_shell, capstrip, dog_env):
    '''stdin should be available from inside dog.'''
    call_shell(f'echo hello world | {dog_env} cat')
    captured = capstrip.get()
    assert captured == ('hello world', '')


def test_auto_mount_works(call_centos7, capstrip):
    '''auto-mount is on by default, and should therefore show the files in the current directory.'''

    call_centos7('ls')
    captured = capstrip.get()
    assert captured == ('dog.config', '')


def test_disabled_auto_mount(call_centos7, capstrip, tmp_path):
    '''disable auto-mount and make sure that we do not see the files in the current directory.'''
    append_to_dog_config(tmp_path, 'auto-mount=False\n')
    call_centos7('ls')
    captured = capstrip.get()
    assert captured == ('', '')


def test_volumes(call_centos7, capstrip, tmp_path, system_temp_dir):
    '''Try adding the "system temp dir" as a volume in the dog.config.'''
    append_to_dog_config(tmp_path, f'\n[volumes]\n{system_temp_dir}=/dog_test_of_system_temp\n')
    call_centos7('mountpoint', '/dog_test_of_system_temp')
    captured = capstrip.get()
    assert captured == ('/dog_test_of_system_temp is a mountpoint', '')


def test_dog_is_too_old_for_minimum_version(call_centos7, tmp_path, capstrip):
    append_to_dog_config(tmp_path, f'minimum-version=999999\n')
    call_centos7('ls')
    captured = capstrip.get()
    assert 'Minimum version required (999999) is greater than your dog' in captured[1]


def test_dog_is_minimum_version(call_centos7, tmp_path, capstrip):
    append_to_dog_config(tmp_path, f'minimum-version={ACTUAL_DOG_VERSION}\n')
    call_centos7('echo ok')
    captured = capstrip.get()
    assert captured == ('ok', '')


def test_dog_is_newer_than_minimum_version(call_centos7, tmp_path, capstrip):
    append_to_dog_config(tmp_path, f'minimum-version={ACTUAL_DOG_VERSION - 1}\n')
    call_centos7('echo ok')
    captured = capstrip.get()
    assert captured == ('ok', '')


def test_no_image_given(call_dog, tmp_path, capfd):
    dog_config = tmp_path / 'dog.config'
    dog_config.write_text('[dog]\n\n')
    call_dog('echo ok')
    assert 'No image specified' in capfd.readouterr().err


def test_dog_config_not_found(my_dog, system_temp_dir, capfd):
    """If no dog.config is found, report an error.

    We run this test in the system_temp_dir to be more sure that no-one has a dog.config file somewhere in the parent directories."""

    for parent in Path(system_temp_dir).parents:
        assert not (parent / 'dog.config').exists(), f'Pre-conditions for this test failed - we expect no dog.config files in the parent directories of {system_temp_dir}'

    cmd_line = [DOG_PYTHON_UNDER_TEST, str(my_dog), 'echo', 'ok']
    subprocess.run(cmd_line, cwd=system_temp_dir)
    assert 'ERROR' in capfd.readouterr().err
