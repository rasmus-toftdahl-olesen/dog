import os

import pytest
from conftest import ACTUAL_DOG_VERSION


@pytest.mark.skipif('DOG_RELEASE_TAG' not in os.environ, reason='Not on a release tag')
def test_dog_release_tag():
    """
    Simple test to verify that when the package is released on github
    (and automatically published using github actions) - then the
    dog.VERSION is the same as the release tag - which is expsed as
    DOG_RELEASE_TAG.
    """
    assert os.getenv('DOG_RELEASE_TAG') == f'refs/tags/v{ACTUAL_DOG_VERSION}'
