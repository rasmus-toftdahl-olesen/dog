import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from dog import VERSION  # noqa: E402

ACTUAL_DOG_VERSION = VERSION
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
