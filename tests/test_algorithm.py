from oaltools.schema import (
    Algorithm,
    OPLType,
    Variable,
    VariableType,
    Constraint,
    ConstraintType,
    Supports,
)


class TestAlgorithm:
    def test_defaults(self):
        alg = Algorithm(
            name="SimpleAlgo",
            variable_types={Variable(type=VariableType.continuous)},
            constraint_types={Constraint(type=ConstraintType.box)},
        )
        assert alg.type is OPLType.algorithm
        assert alg.name == "SimpleAlgo"
        assert alg.long_name is None
        assert alg.description is None

    def test_with_optional_fields(self):
        alg = Algorithm(
            name="AdvancedAlgo",
            long_name="Advanced Algorithm",
            description="A sophisticated optimization algorithm",
            tags={"gradient-free", "population-based"},
            variable_types={Variable(type=VariableType.integer)},
            constraint_types={Constraint(type=ConstraintType.linear)},
        )
        assert alg.name == "AdvancedAlgo"
        assert alg.long_name == "Advanced Algorithm"
        assert alg.tags == {"gradient-free", "population-based"}

    def test_variable_types_set(self):
        var1 = Variable(type=VariableType.continuous)
        var2 = Variable(type=VariableType.binary)
        alg = Algorithm(
            name="MultiVarAlgo",
            variable_types={var1, var2},
            constraint_types={Constraint(type=ConstraintType.box)},
        )
        assert len(alg.variable_types) == 2

    def test_constraint_types_set(self):
        con1 = Constraint(type=ConstraintType.box)
        con2 = Constraint(type=ConstraintType.linear)
        alg = Algorithm(
            name="MultiConAlgo",
            variable_types={Variable(type=VariableType.continuous)},
            constraint_types={con1, con2},
        )
        assert len(alg.constraint_types) == 2

    def test_algorithm_hashable(self):
        alg1 = Algorithm(
            name="Algo1",
            variable_types={Variable(type=VariableType.continuous)},
            constraint_types={Constraint(type=ConstraintType.box)},
        )
        alg2 = Algorithm(
            name="Algo1",
            variable_types={Variable(type=VariableType.continuous)},
            constraint_types={Constraint(type=ConstraintType.box)},
        )
        # Algorithms with same name and type should hash the same
        assert hash(alg1) == hash(alg2)
