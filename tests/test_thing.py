import pytest
from pydantic import ValidationError

from oaltools.schema import OPLType, Thing


class TestThing:
    def test_type_required(self):
        with pytest.raises(ValidationError):
            Thing()

    def test_allows_extra_fields(self):
        thing = Thing(type=OPLType.algorithm, something_extra="value", count=3)
        assert thing.type is OPLType.algorithm
        assert thing.something_extra == "value"
        assert thing.count == 3
