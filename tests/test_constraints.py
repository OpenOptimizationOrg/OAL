from oaltools.schema import Constraint, ConstraintType, Supports


class TestConstraint:
    def test_default(self):
        c = Constraint(type=ConstraintType.box)
        assert c.type is ConstraintType.box
        assert c.supports is None
        assert c.hard is None
        assert c.equality is None

    def test_with_supports(self):
        c = Constraint(type=ConstraintType.box, supports=Supports.conditional)
        assert c.supports is Supports.conditional

    def test_linear_constraint(self):
        c = Constraint(type=ConstraintType.linear, hard=True, equality=False)
        assert c.type is ConstraintType.linear
        assert c.hard is True
        assert c.equality is False
