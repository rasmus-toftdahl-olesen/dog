import pytest

from conftest import append_to_dog_config


@pytest.fixture
def home_dir_with_perforce_file(home_temp_dir):
    (home_temp_dir / '.p4tickets').write_text('This is a mock p4 tickets file')
    (home_temp_dir / 'p4tickets.txt').write_text('This is a mock p4 tickets file')
    return home_temp_dir


def test_perforce_enabled(call_main, capstrip, tmp_path, home_dir_with_perforce_file):
    append_to_dog_config(tmp_path, '[dog]\nimage=rtol/centos-for-dog\n')
    call_main('cat', '~/.p4tickets')
    stdout, stderr = capstrip.get()
    assert 'This is a mock p4 tickets file' in stdout


def test_perforce_enabled_but_no_file(call_main, tmp_path, home_temp_dir):
    append_to_dog_config(tmp_path, '[dog]\nimage=rtol/centos-for-dog\n')
    assert call_main('env') == 0


def test_perforce_disabled(call_main, capstrip, tmp_path, home_dir_with_perforce_file):
    append_to_dog_config(tmp_path, '[dog]\nimage=rtol/centos-for-dog\n')
    append_to_dog_config(tmp_path, '\nperforce=False')
    call_main('cat', '~/.p4tickets')
    stdout, stderr = capstrip.get()
    assert '.p4tickets: No such file or directory' in stderr
