import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from dog import VERSION, main  # noqa: E402

ACTUAL_DOG_VERSION = VERSION
DOG_PYTHON_UNDER_TEST = os.getenv('DOG_PYTHON_UNDER_TEST', sys.executable)


def is_windows() -> bool:
    return 'win32' in sys.platform


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
    if is_windows():
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
    dog_config.write_text('[dog]\nimage=rtol/centos-for-dog\n')
    return call_dog


@pytest.fixture
def call_main(my_dog, tmp_path, monkeypatch):
    '''Call dog without using a sub-process'''

    def call(*args: object):
        cmd_line = [str(my_dog)]
        for arg in args:
            cmd_line.append(str(arg))
        with monkeypatch.context() as m:
            m.chdir(tmp_path)
            return main(cmd_line)

    yield call


@pytest.fixture
def dog_env():
    if is_windows():
        return '%DOG%'
    else:
        return '$DOG'


def append_to_dog_config(tmp_path: Path, extra_dog_config: str):
    dog_config = tmp_path / 'dog.config'
    if dog_config.exists():
        old_config = dog_config.read_text()
    else:
        old_config = ''
    new_config = old_config + extra_dog_config
    dog_config.write_text(new_config)


@pytest.fixture
def system_temp_dir() -> str:
    if is_windows():
        basedir = os.environ['TEMP']
    else:
        basedir = os.getenv('RUNNER_TEMP', '/tmp')
    ret: Path = Path(tempfile.mktemp('dog_tests', 'dog_tests', basedir))
    ret.mkdir(parents=True, exist_ok=False)
    yield str(ret)
    os.removedirs(str(ret))


@pytest.fixture
def home_temp_dir(tmp_path_factory, monkeypatch) -> Path:
    tmphome = tmp_path_factory.mktemp('home')
    monkeypatch.setattr(Path, 'home', lambda: tmphome)
    return tmphome
