from oaltools import (
    Library,
    Algorithm,
    Implementation,
    Reference,
    Link,
    Variable,
    Constraint,
    ValueRange,
)
from oaltools.schema import ConstraintType, FeatureSupport, SupportsType, VariableType
from oaltools.supports import Supports
from pydantic_yaml import to_yaml_str

things = {}

things["impl_integeres"] = Implementation(
    name="impl_integeres",
    description="A Python implementation of NIES",
    language="python",
    links=[Link(url="https://github.com/jacobdenobel/integer-es", type="source code")],
)


things["alg_nies"] = Algorithm(
    name="NIES",
    long_name="Natural Integer Evolutionary Strategies",
    description="A natural-gradient based evolutionary algorithm for integer-space optimization",
    tags={"Anytime", "Gradient-free", "Evolutionary"},
    references=None,
    implementations={"impl_integeres"},
    objectives=1,
    recommended_budget=ValueRange(min=100, max=1e10),
    number_variables=ValueRange(min=1, max=5000),
    constraint_types={Constraint(type=ConstraintType.box)},
    dynamics=None,
    noise=None,
    partial_evaluation=None,
    modality_types={SupportsType(type="unimodal", supports=Supports.default)},
    can_evaluate_objectives_independently=None,
    variable_types={Variable(type=VariableType.integer, supports=Supports.default)},
)

library = Library(things)

# Make sure model is really valid
Library.model_validate(library)

if __name__ == "__main__":
    with open("algorithms.yaml", "w") as fd:
        fd.write(to_yaml_str(library))
