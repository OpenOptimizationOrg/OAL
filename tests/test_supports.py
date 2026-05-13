import pytest

from oaltools.schema import Supports
from oaltools.supports import union


class TestSupports:
    def test_from_string(self):
        assert Supports("no") == Supports.no
        assert Supports("default") == Supports.default
        assert Supports("conditional") == Supports.conditional
        assert Supports("unknown") == Supports.unknown

    def test_bad_string(self):
        with pytest.raises(ValueError):
            Supports("foo")