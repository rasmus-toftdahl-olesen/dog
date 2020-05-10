import sys
from pathlib import Path
from typing import Sequence
import subprocess
import getpass
import re
import pytest


@pytest.fixture
def capstrip(capfd):
    class CapStrip:
        def get(self):
            return tuple(a.strip() for a in capfd.readouterr())

    return CapStrip()


@pytest.fixture
def my_dog():
    return (Path(__file__).parent.parent / 'dog.py').absolute()


@pytest.fixture
def call_dog(my_dog, tmp_path):
    def call(*args: Sequence[object]):
        cmd_line = [sys.executable, str(my_dog)]
        for arg in args:
            cmd_line.append(str(arg))
        return subprocess.run(cmd_line, cwd=tmp_path).returncode

    yield call


@pytest.fixture
def call_centos7(call_dog, tmp_path):
    dog_config = tmp_path / 'dog.config'
    dog_config.write_text('[dog]\nimage=teamtc/dog/centos-for-dog\n')
    return call_dog


@pytest.fixture
def call_shell(call_centos7, tmp_path, my_dog, monkeypatch):
    monkeypatch.setenv('DOG', f'"{sys.executable}" "{my_dog}"')

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


def test_user_is_me(call_centos7, capfd):
    assert call_centos7('id') == 0
    captured = capfd.readouterr()
    assert f'uid=1000({getpass.getuser()})' in captured.out


def test_as_root(call_centos7, capfd):
    call_centos7('--as-root', 'id')
    captured = capfd.readouterr()
    assert 'uid=0(root)' in captured.out


def test_pull_as_echo_argument(call_centos7, capstrip):
    '''--pull should only be interpreted as an dog argument if it comes before the first argument'''
    call_centos7('echo', '-n', '--pull')
    captured = capstrip.get()
    assert ('--pull', '') == captured


def test_version(call_dog, capfd):
    '''--version should just return the current dog version'''
    call_dog('--version')
    captured = capfd.readouterr()
    assert re.match('dog version [0-9]+', captured.out)


def test_stdin_testing_works(call_shell, capstrip):
    '''Just verifying that my stdin testing works before testing it with dog.'''
    call_shell('echo hello world | cat -')
    captured = capstrip.get()
    assert ('hello world', '') == captured


def test_stdin(call_shell, capstrip):
    '''stdin should be available from inside dog.'''
    call_shell('echo hello world| %DOG% cat')
    captured = capstrip.get()
    assert ('hello world', '') == captured
