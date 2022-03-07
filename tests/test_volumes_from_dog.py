import subprocess
import sys
from pathlib import Path

import pytest

from conftest import DOG_PYTHON_UNDER_TEST

RESOURCES = Path(__file__).parent / 'resources' / 'volumes-from-test'


@pytest.fixture
def call_shell(my_dog, monkeypatch):
    if 'win32' in sys.platform:
        monkeypatch.setenv('DOG', f'"{DOG_PYTHON_UNDER_TEST}" "{my_dog}"')
    else:
        monkeypatch.setenv('DOG', f'{DOG_PYTHON_UNDER_TEST} {my_dog}')

    def call(shell_string: str):
        return subprocess.run(shell_string, shell=True, cwd=RESOURCES)

    return call


def test_run_tool1(call_shell, capstrip, dog_env):
    call_shell(f'{dog_env} /opt/tool1/tool1.sh')
    stdout, stderr = capstrip.get()
    assert stderr == ''
    assert 'tool1 ran' in stdout


def test_run_tool2(call_shell, capstrip, dog_env):
    call_shell(f'{dog_env} /opt/tool2/tool2.sh')
    stdout, stderr = capstrip.get()
    assert stderr == ''
    assert 'tool2 ran' in stdout
