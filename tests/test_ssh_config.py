import os
import subprocess
import sys

import pytest

from conftest import DOG_PYTHON_UNDER_TEST
from conftest import append_to_dog_config


@pytest.fixture
def call_shell(my_dog, monkeypatch, tmp_path):
    if 'win32' in sys.platform:
        monkeypatch.setenv('DOG', f'"{DOG_PYTHON_UNDER_TEST}" "{my_dog}"')
    else:
        monkeypatch.setenv('DOG', f'{DOG_PYTHON_UNDER_TEST} {my_dog}')

    (tmp_path / 'dog.config').write_text('[dog]\nimage=rtol/git-for-dog')

    def call(shell_string: str):
        return subprocess.run(shell_string, shell=True, cwd=tmp_path)

    return call


def test_pull_git_for_dog(call_shell, capstrip, dog_env):
    call_shell(f'{dog_env} env')
    print(capstrip.get())


@pytest.mark.skipif('GITHUB_ACTIONS' in os.environ, reason='This test does not work on GitHub actions since it uses SSH authentication')
def test_ssh_enabled(call_shell, capstrip, dog_env):
    call_shell(f'{dog_env} git clone git@github.com:rasmus-toftdahl-olesen/dog.git')
    stdout, stderr = capstrip.get()
    assert 'Could not read from remote repository' not in stderr


def test_ssh_disabled(call_shell, capstrip, dog_env, tmp_path):
    append_to_dog_config(tmp_path, '\nssh=False')
    call_shell(f'{dog_env} git clone git@github.com:rasmus-toftdahl-olesen/dog.git')
    stdout, stderr = capstrip.get()
    assert 'Could not read from remote repository' in stderr
