import sys
from pathlib import Path
from typing import Sequence
import subprocess
import getpass
import pytest


@pytest.fixture
def my_dog():
    return (Path(__file__).parent.parent / 'dog.py').absolute()


@pytest.fixture
def call_dog(my_dog, tmp_path):
    def call(*args: Sequence[object]):
        cmd_line = [sys.executable, str(my_dog)]
        for arg in args:
            cmd_line.append(str(arg))
        subprocess.run(cmd_line, cwd=tmp_path)

    yield call


@pytest.fixture
def call_centos7(call_dog, tmp_path):
    dog_config = tmp_path / 'dog.config'
    dog_config.write_text('[dog]\nimage=esw/serverscripts/forge\n')
    return call_dog


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


def test_user_is_me(call_centos7, capfd):
    call_centos7('id')
    captured = capfd.readouterr()
    assert f'uid=1000({getpass.getuser()})' in captured.out


def test_as_root(call_centos7, capfd):
    call_centos7('--as-root', 'id')
    captured = capfd.readouterr()
    assert 'uid=0(root)' in captured.out


def test_pull_as_echo_argument(call_centos7, capfd):
    '''--pull should only be interpreted as an dog argument if it comes before the first argument'''
    call_centos7('echo', '-n', '--pull')
    captured = capfd.readouterr()
    assert '--pull' == captured.out
