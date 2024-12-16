from utils.trim import in_bound_trim


def test_in_bound_trim():
    chapters = list(range(10))
    trimmed = list(in_bound_trim(chapters, 1, 3))
    assert trimmed == [1, 2]
