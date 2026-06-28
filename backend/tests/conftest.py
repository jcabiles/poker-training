import pytest
from factories import make_rfi_spot


@pytest.fixture
def rfi_spot():
    return make_rfi_spot()
