import os
import pytest
from conftest import append_to_dog_config


@pytest.fixture
def home_dir_with_perforce_file(home_temp_dir, monkeypatch, tmp_path):
    (home_temp_dir / '.p4tickets').write_text('This is a mock p4 tickets file')
    (home_temp_dir / 'p4tickets.txt').write_text('This is a mock p4 tickets file')

    # Make the tmp_path (cwd) look like a mount point
    real_os_path_is_mount = os.path.ismount

    def my_is_mount(s):
        if s == str(tmp_path):
            return True
        else:
            return real_os_path_is_mount(s)

    monkeypatch.setattr(os.path, 'ismount', my_is_mount)

    return home_temp_dir


def test_perforce_enabled(
    basic_dog_config, call_main, capstrip, tmp_path, home_dir_with_perforce_file
):
    append_to_dog_config(
        tmp_path,
        [
            'image=rtol/centos-for-dog',
            '[volumes]',
            '$home/.p4tickets:ro = ~/.p4tickets',
        ],
    )
    call_main('cat', '~/.p4tickets')
    stdout, stderr = capstrip.get()
    assert (
        'This is a mock p4 tickets file' in stdout
    ), f'stdout:\n{stdout}\n\nstderr:\n{stderr}'


def test_perforce_enabled_but_no_file(
    basic_dog_config, call_main, tmp_path, home_temp_dir
):
    append_to_dog_config(
        tmp_path,
        [
            'image=rtol/centos-for-dog',
            '[volumes]',
            '$home/.p4tickets:ro = ~/.p4tickets',
        ],
    )
    assert call_main('env') == 0


def test_perforce_disabled(
    basic_dog_config, call_main, capstrip, tmp_path, home_dir_with_perforce_file
):
    append_to_dog_config(tmp_path, ['image=rtol/centos-for-dog'])
    call_main('cat', '~/.p4tickets')
    stdout, stderr = capstrip.get()
    assert (
        '.p4tickets: No such file or directory' in stderr
    ), f'stdout:\n{stdout}\n\nstderr:\n{stderr}'
