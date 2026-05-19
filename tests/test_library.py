from oaltools.schema import (
    Algorithm,
    Implementation,
    Library,
    Variable,
    VariableType,
    Constraint,
    ConstraintType,
)


class TestLibrary:
    def test_empty(self):
        lib = Library(root={})
        assert lib.root == {}

    def test_single_algorithm(self):
        alg = Algorithm(
            name="Algo1",
            variable_types={Variable(type=VariableType.continuous)},
            constraint_types={Constraint(type=ConstraintType.box)},
        )
        lib = Library(root={"algo1": alg})
        assert "algo1" in lib.root
        assert isinstance(lib.root["algo1"], Algorithm)

    def test_single_implementation(self):
        impl = Implementation(name="impl1", description="An implementation")
        lib = Library(root={"impl1": impl})
        assert "impl1" in lib.root
        assert isinstance(lib.root["impl1"], Implementation)

    def test_mixed_algorithms_and_implementations(self):
        alg1 = Algorithm(
            name="Algo1",
            variable_types={Variable(type=VariableType.continuous)},
            constraint_types={Constraint(type=ConstraintType.box)},
        )
        alg2 = Algorithm(
            name="Algo2",
            variable_types={Variable(type=VariableType.integer)},
            constraint_types={Constraint(type=ConstraintType.linear)},
        )
        impl1 = Implementation(name="impl1", description="d1")
        impl2 = Implementation(name="impl2", description="d2")
        
        lib = Library(
            root={
                "algo1": alg1,
                "algo2": alg2,
                "impl1": impl1,
                "impl2": impl2,
            }
        )
        assert len(lib.root) == 4
        assert isinstance(lib.root["algo1"], Algorithm)
        assert isinstance(lib.root["algo2"], Algorithm)
        assert isinstance(lib.root["impl1"], Implementation)
        assert isinstance(lib.root["impl2"], Implementation)


