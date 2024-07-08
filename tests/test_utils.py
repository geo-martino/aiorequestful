# noinspection PyProtectedMember
from aiorequestful._utils import get_iterator


# noinspection PyTypeChecker
def test_get_iterator():
    # None input always returns empty iterator
    assert list(get_iterator(None)) == []

    # always returns same iterator when given iterator as input
    iterator = iter([1, 2, 3])
    assert id(get_iterator(iterator)) == id(iterator)

    assert list(get_iterator("123")) == ["123"]
    assert list(get_iterator(1)) == [1]
    assert list(get_iterator([1, 2, 3])) == [1, 2, 3]
