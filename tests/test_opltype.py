import pytest

from oaltools.schema import OPLType


class TestOPLType:
    def test_from_string(self):
        # Only algorithm and implementation exist in current schema
        assert OPLType("algorithm") is OPLType.algorithm
        assert OPLType("implementation") is OPLType.implementation

    def test_bad_string(self):
        with pytest.raises(ValueError):
            OPLType("foo")

