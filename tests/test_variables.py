from oaltools.schema import Variable, VariableType, Supports


class TestVariable:
    def test_defaults(self):
        v = Variable(type=VariableType.continuous)
        assert v.type is VariableType.continuous
        assert v.supports is None
        assert v.description is None

    def test_explicit_values(self):
        v = Variable(type=VariableType.continuous, supports=Supports.default, description="A continuous variable")
        assert v.type is VariableType.continuous
        assert v.supports is Supports.default
        assert v.description == "A continuous variable"

    def test_integer_type(self):
        v = Variable(type=VariableType.integer)
        assert v.type is VariableType.integer

    def test_binary_type(self):
        v = Variable(type=VariableType.binary)
        assert v.type is VariableType.binary
