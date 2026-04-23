from enum import Enum


class Supports(Enum):
    no = "no"
    default = "default"
    conditional = "conditional"
    unknown = "unknown"


def union(
    a: Supports | set[Supports], b: Supports | set[Supports]
) -> Supports | set[Supports]:
    result = set()
    if isinstance(a, Supports):
        result.add(a)
    else:
        result.update(a)

    if isinstance(b, Supports):
        result.add(b)
    else:
        result.update(b)

    if len(result) == 1:
        return result.pop()
    else:
        return result
