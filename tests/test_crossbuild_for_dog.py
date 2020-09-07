import sys
from pathlib import Path
import pytest
from conftest import DOG_PYTHON_UNDER_TEST
import subprocess

RESOURCES = Path(__file__).parent / 'resources' / 'crossbuild-for-dog'

@pytest.fixture
def call_shell(my_dog, monkeypatch):
    if 'win32' in sys.platform:
        monkeypatch.setenv('DOG', f'"{DOG_PYTHON_UNDER_TEST}" "{my_dog}"')
    else:
        monkeypatch.setenv('DOG', f'{DOG_PYTHON_UNDER_TEST} {my_dog}')

    def call(shell_string: str):
        return subprocess.run(shell_string, shell=True, cwd=RESOURCES)

    return call

def test_pull_crossbuild_for_dog(call_shell, capstrip, dog_env):
    call_shell(f'{dog_env} env')
    print(capstrip.get())
    
def test_make_creates_arm_targets(call_shell, capstrip, dog_env):
    call_shell(f'{dog_env} make')
    stdout, stderr = capstrip.get()
    assert stderr == ''
    assert 'CROSS_TRIPLE: aarch64-linux-gnu' in stdout
    assert 'ARM aarch64' in stdout

