from enum import Enum
from typing_extensions import Self
from pydantic import BaseModel, RootModel, ConfigDict

from .supports import Supports
from .yesnosome import YesNoSome
from .utils import ValueRange, union_range


class OPLType(Enum):
    algorithm = "algorithm"
    implementation = "implementation"


class Link(BaseModel):
    type: str | None = None
    url: str

    def __hash__(self):
        return hash(self.type) + hash(self.url)


class Thing(BaseModel):
    type: OPLType
    model_config = ConfigDict(extra="allow")

class Objectives(RootModel):
    root: int | set[int] | ValueRange = 0

    def union(self, other: Self) -> Self:
        self.root = union_range(self.root, other.root)
        return self

class Reference(BaseModel):
    title: str
    authors: list[str]
    link: Link | None = None

    def __hash__(self):
        return (
            hash(self.title)
            + sum([hash(author) for author in self.authors])
            + hash(self.link)
        )


class Usage(BaseModel):
    language: str
    code: str


class Implementation(Thing):
    type: OPLType = OPLType.implementation
    name: str
    description: str
    links: list[Link] | None = None
    language: str | None = None
    requirements: str | list[str] | None = None

class FeatureSupport(BaseModel):
    supports: Supports 
    description: str | None = None


class VariableType(Enum):
    continuous = "continuous"
    integer = "integer"
    binary = "binary"
    categorical = "categorical"

class Variable(BaseModel):
    type: VariableType
    supports: Supports | None = None
    description: str | None = None

    def __hash__(self):
        return hash((self.type, self.supports, self.description))

class ConstraintType(Enum):
    box = "box"
    linear = "linear"
    function = "function"

class Constraint(BaseModel):
    type: ConstraintType
    supports: Supports | None = None
    hard: bool | None = None
    equality: bool | None = None
    description: str | None = None

    def __hash__(self):
        return hash((self.type, self.supports, self.hard, self.equality, self.description))

class SupportsType(BaseModel):
    type: str
    supports: Supports | None = None
    description: str | None = None

    def __hash__(self):
        return hash((self.type, self.supports, self.description))

class Algorithm(Thing):
    type: OPLType = OPLType.algorithm
    name: str
    long_name: str | None = None
    description: str | None = None
    tags: set[str] | None = None
    references: set[Reference] | None = None
    implementations: set[str] | None = None
    objectives: Objectives | None = None
    recommended_budget: ValueRange | None = None
    number_variables: ValueRange | None = None
    variable_types: set[Variable]
    constraint_types: set[Constraint]
    dynamics: set[SupportsType] | None = None
    noise: set[SupportsType] | None = None
    partial_evaluation: FeatureSupport | None = None
    can_evaluate_objectives_independently: FeatureSupport | None = None
    modality_types: set[SupportsType] | None = None
    fidelity_levels: ValueRange | None = None
    code_examples: set[str] | None = None
    source: set[str] | None = None

    def __hash__(self):
        return hash((self.type, self.name))

recommended_tags = [
    {"performance" : {"Anytime", "Budget-Aware"}},
    {"execution" : {"Parallel", "Sequential", "Expensive"}},
    {"methodology" : {"Gradient-based", "Gradient-free", "Surrogate Model", "Covariance Update", "Population-based", "Single Solution"}},
    {"families" : {"Evolutionary", "Bayesian Optimization", "Simulated Annealing", "Particle Swarm Optimization"}},
    {"variable" : {"Permutation", "Hierarchical", "Mixed"}}
]


class Library(RootModel):
    root: dict[str, Algorithm | Implementation] = {}

    def _check_id_references(self, ids, type: OPLType) -> None:
        for id in ids:
            if id in self.root:
                if self.root[id].type != type:
                    raise ValueError(
                        f"ID {id} is a {self.root[id].name}, expected a {type.name}"
                    )
            else:
                raise ValueError(f"Missing {type.name} with id '{id}'")


__all__ = [
    "Constraint",
    "Algorithm",
    "Implementation",
    "Library",
    "Link",
    "Reference",
    "Variable",
    "YesNoSome",
    "Supports",
    "SupportsType",
    "FeatureSupport",
    "Constraint",
]
