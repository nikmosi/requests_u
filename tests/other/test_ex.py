import pytest


def test_index():
    data = list(range(20))

    assert data.index(0) == 0
    with pytest.raises(ValueError):
        data.index(-1)
        data.index(-2)
    assert data.index(4) == 4
