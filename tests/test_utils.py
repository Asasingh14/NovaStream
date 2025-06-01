from src import expand_ranges


def test_expand_ranges_single():
    assert expand_ranges("1") == [1]


def test_expand_ranges_range():
    assert expand_ranges("2-4") == [2, 3, 4]


def test_expand_ranges_mixed():
    assert expand_ranges("1,3-5") == [1, 3, 4, 5]


def test_expand_ranges_duplicates():
    assert expand_ranges("1,1,2") == [1, 2] 