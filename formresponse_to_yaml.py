from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from src.oaltools.schema import (
    Algorithm,
    Constraint,
    ConstraintType,
    FeatureSupport,
    Implementation,
    Library,
    Link,
    Objectives,
    Supports,
    ValueRange,
    Variable,
    VariableType,
)


CSV_PATH = Path("AOL_responses.csv")
OUTPUT_YAML_PATH = Path("algorithms.yaml")

COL_NAME = "Short name of algorithm"
COL_INPUT_CONTINUOUS = "Input Variable Support [Continuous]"
COL_INPUT_INTEGER = "Input Variable Support [Integer]"
COL_INPUT_BOOLEAN = "Input Variable Support [Boolean]"
COL_INPUT_CATEGORICAL = "Input Variable Support [Categorical]"
COL_DIM = "Number of Input variables (number(s) or range)"
COL_OBJECTIVES = "Number of Objectives (number(s) or range or 'scalable')"
COL_CONSTRAINTS = "Problem characteristics support [Constraints]"
COL_DYNAMIC = "Problem characteristics support [Dynamic Objective Functions]"
COL_NOISY = "Problem characteristics support [Noisy Evaluations]"
COL_MULTIMODAL = "Problem characteristics support [Multi-Modality]"
COL_PARTIAL_EVAL = "Problem characteristics support [Partial Evaluations]"
COL_MULTI_FIDELITY = "Problem characteristics support [Multiple Fidelities]"
COL_INDEPENDENT_EVALS = "Problem characteristics support [Independent objective evaluations]"
COL_EVAL_COUNT = "Number of evaluations supported (range)"
COL_IMPL_LINK = "Link to implementation"
COL_LANGUAGE = "Programming Language"
COL_REQUIREMENTS = "Requirements"
COL_DESCRIPTION = "Description"
COL_CONSTRAINT_TYPES = "Supported constraint types"
COL_TAG_PERFORMANCE = "Tags: Performance"
COL_TAG_EXECUTION = "Tags: Execution"
COL_TAG_METHODOLOGY = "Tags: Methodology"
COL_TAG_FAMILY = "Tag: Algorithm Family"
COL_TAG_VARIABLE = "Tag: Variable Handling"
COL_TAG_OTHER = "Other Tags"
COL_OTHER_INFO = "Other relevant information"

NO_VALUE_MARKERS = {
    "",
    "-",
    "n/a",
    "na",
    "none",
    "not found",
    "unknown",
    "not public",
    "implementation not freely available",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.lower() in NO_VALUE_MARKERS:
        return ""
    return text


def is_meaningful(value: Any) -> bool:
    return bool(normalize_text(value))


def split_values(value: Any) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    parts = re.split(r"[,;\n|]+", text)
    return [part.strip() for part in parts if part.strip()]


def extract_urls(value: Any) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    urls = re.findall(r'https?://[^\s,\]\)"\']+', text)
    if not urls and text.lower().startswith("www."):
        urls = [f"https://{text}"]
    seen: set[str] = set()
    ordered_urls: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered_urls.append(url)
    return ordered_urls


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_") or "entry"


def unique_id(prefix: str, name: str, used_ids: set[str]) -> str:
    base = f"{prefix}{slugify(name)}"
    if base not in used_ids:
        used_ids.add(base)
        return base

    suffix = 2
    while True:
        candidate = f"{base}_{suffix}"
        if candidate not in used_ids:
            used_ids.add(candidate)
            return candidate
        suffix += 1


def parse_support(value: Any) -> Supports | None:
    text = normalize_text(value)
    if not text:
        return None

    lowered = re.sub(r"[\s_-]+", " ", text).strip().lower()
    if lowered in {"yes", "y", "true", "present", "available", "supported", "supported by default"}:
        return Supports.default
    if lowered in {"some", "partial", "mixed", "depends", "conditional"}:
        return Supports.conditional
    if lowered in {"no", "n", "false", "not present", "absent", "unsupported", "not supported"}:
        return Supports.no
    if lowered in {"unknown", "?"}:
        return Supports.unknown
    return Supports.unknown


def parse_ints(value: Any) -> list[int]:
    text = normalize_text(value)
    if not text:
        return []
    return [int(num) for num in re.findall(r"\d+", text)]


def parse_value_range(value: Any) -> ValueRange | None:
    text = normalize_text(value)
    if not text:
        return None

    lowered = text.lower()
    numbers = parse_ints(text)
    if not numbers:
        return None

    if "scalable" in lowered:
        if len(numbers) >= 2:
            return ValueRange(min=min(numbers), max=max(numbers))
        return ValueRange(min=numbers[0], max=None)

    if (" to " in lowered or "-" in lowered or "–" in lowered or "—" in lowered) and len(numbers) >= 2:
        return ValueRange(min=min(numbers), max=max(numbers))

    if len(numbers) == 1:
        return ValueRange(min=numbers[0], max=numbers[0])

    return ValueRange(min=min(numbers), max=max(numbers))


def parse_objectives(value: Any) -> Objectives | None:
    text = normalize_text(value)
    if not text:
        return None

    lowered = text.lower()
    numbers = sorted(set(parse_ints(text)))
    if not numbers:
        return None

    if "scalable" in lowered or " to " in lowered or "-" in lowered or "–" in lowered or "—" in lowered:
        return Objectives(root=parse_value_range(text))

    if len(numbers) == 1:
        return Objectives(root=numbers[0])

    return Objectives(root=set(numbers))


def parse_variable_type(token: str) -> VariableType | None:
    lowered = token.strip().lower()
    if any(term in lowered for term in ("continuous", "real")):
        return VariableType.continuous
    if any(term in lowered for term in ("integer", "ordinal", "int")):
        return VariableType.integer
    if any(term in lowered for term in ("boolean", "binary", "bool")):
        return VariableType.binary
    if any(term in lowered for term in ("categorical", "nominal", "category")):
        return VariableType.categorical
    return None


def parse_variable_types(row: dict[str, Any]) -> set[Variable]:
    mapping = (
        (COL_INPUT_CONTINUOUS, VariableType.continuous),
        (COL_INPUT_INTEGER, VariableType.integer),
        (COL_INPUT_BOOLEAN, VariableType.binary),
        (COL_INPUT_CATEGORICAL, VariableType.categorical),
    )

    variables: set[Variable] = set()
    for column, variable_type in mapping:
        support = parse_support(row.get(column))
        if support is None or support == Supports.no:
            continue
        variables.add(Variable(type=variable_type, supports=support))
    return variables


def parse_constraint_type(token: str) -> ConstraintType | None:
    lowered = token.strip().lower()
    if "box" in lowered:
        return ConstraintType.box
    if "linear" in lowered:
        return ConstraintType.linear
    if "function" in lowered or "nonlinear" in lowered:
        return ConstraintType.function
    return None


def parse_constraint_types(row: dict[str, Any]) -> set[Constraint]:
    support = parse_support(row.get(COL_CONSTRAINTS))
    if support == Supports.no:
        return set()

    types = {parse_constraint_type(token) for token in split_values(row.get(COL_CONSTRAINT_TYPES))}
    constraints = {Constraint(type=ctype, supports=support) for ctype in types if ctype is not None}

    if constraints:
        return constraints

    if support is None:
        return set()

    return {Constraint(type=ConstraintType.function, supports=support)}


def parse_feature_support(value: Any) -> FeatureSupport | None:
    support = parse_support(value)
    if support is None:
        return None
    return FeatureSupport(supports=support, description=normalize_text(value) or None)

def parse_fidelity_levels(value: Any) -> ValueRange | None:
    support = parse_support(value)
    if support is None or support == Supports.no:
        return None
    return ValueRange(min=2, max=None)


def parse_links(value: Any) -> list[Link] | None:
    urls = extract_urls(value)
    if not urls:
        return None
    return [Link(type="source code", url=url) for url in urls]


def parse_requirements(value: Any) -> str | list[str] | None:
    items = split_values(value)
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    return items


def append_if_present(parts: list[str], label: str, value: Any) -> None:
    text = normalize_text(value)
    if text:
        parts.append(f"{label}: {text}")


def build_description(row: dict[str, Any]) -> str:
    description = normalize_text(row.get(COL_DESCRIPTION))
    extra_bits: list[str] = []
    append_if_present(extra_bits, "Other relevant information", row.get(COL_OTHER_INFO))

    if extra_bits:
        if description:
            return "\n\n".join([description, *extra_bits])
        return "\n\n".join(extra_bits)
    return description


def collect_tags(row: dict[str, Any]) -> set[str] | None:
    tags: set[str] = set()
    for column in (
        COL_TAG_PERFORMANCE,
        COL_TAG_EXECUTION,
        COL_TAG_METHODOLOGY,
        COL_TAG_FAMILY,
        COL_TAG_VARIABLE,
        COL_TAG_OTHER,
    ):
        for token in split_values(row.get(column)):
            if token:
                tags.add(token)

    if parse_support(row.get(COL_DYNAMIC)) is not None:
        tags.add("dynamic-objective-functions")
    if parse_support(row.get(COL_NOISY)) is not None:
        tags.add("noisy-evaluations")

    multimodal_support = parse_support(row.get(COL_MULTIMODAL))
    if multimodal_support == Supports.no:
        tags.add("unimodal")
    elif multimodal_support is not None:
        tags.add("multimodal")

    if parse_support(row.get(COL_PARTIAL_EVAL)) is not None:
        tags.add("partial-evaluations")
    if parse_support(row.get(COL_MULTI_FIDELITY)) is not None:
        tags.add("multiple-fidelities")
    if parse_support(row.get(COL_INDEPENDENT_EVALS)) is not None:
        tags.add("independent-objective-evaluations")

    return tags or None


def build_implementation(row: dict[str, Any], name: str, used_ids: set[str]) -> tuple[str, Implementation] | None:
    links = parse_links(row.get(COL_IMPL_LINK))
    language = normalize_text(row.get(COL_LANGUAGE)) or None
    requirements = parse_requirements(row.get(COL_REQUIREMENTS))
    description = build_description(row) or f"Implementation for {name}"

    if not any([links, language, requirements]):
        return None

    impl = Implementation(
        name=f"{name} implementation",
        description=description,
        links=links,
        language=language,
        requirements=requirements,
    )
    impl_id = unique_id("impl_", name, used_ids)
    return impl_id, impl


def build_algorithm(row: dict[str, Any], used_ids: set[str]) -> tuple[str, Algorithm, tuple[str, Implementation] | None] | None:
    name = normalize_text(row.get(COL_NAME))
    if not name:
        return None

    description = build_description(row) or None
    variable_types = parse_variable_types(row)
    constraint_types = parse_constraint_types(row)
    objectives = parse_objectives(row.get(COL_OBJECTIVES))
    number_variables = parse_value_range(row.get(COL_DIM))
    recommended_budget = parse_value_range(row.get(COL_EVAL_COUNT))
    tags = collect_tags(row)
    partial_evaluation_support = parse_feature_support(row.get(COL_PARTIAL_EVAL))
    independent_evals_support = parse_feature_support(row.get(COL_INDEPENDENT_EVALS))
    fidelity_levels = parse_fidelity_levels(row.get(COL_MULTI_FIDELITY))

    implementation = build_implementation(row, name, used_ids)
    implementations = {implementation[0]} if implementation else None

    algorithm = Algorithm(
        name=name,
        description=description,
        tags=tags,
        implementations=implementations,
        objectives=objectives,
        recommended_budget=recommended_budget,
        number_variables=number_variables,
        variable_types=variable_types,
        constraint_types=constraint_types,
        partial_evaluation=(
            None if partial_evaluation_support is None else partial_evaluation_support
        ),
        can_evaluate_objectives_independently=(
            None if independent_evals_support is None else independent_evals_support
        ),
        fidelity_levels=fidelity_levels,
    )

    alg_id = unique_id("alg_", name, used_ids)
    return alg_id, algorithm, implementation


def load_rows(csv_path: Path) -> list[dict[str, Any]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def build_library(rows: list[dict[str, Any]]) -> tuple[Library, int, int, int]:
    root: dict[str, Algorithm | Implementation] = {}
    used_ids: set[str] = set()
    seen_names: set[str] = set()

    added_algorithms = 0
    added_implementations = 0
    skipped_rows = 0

    for row in rows:
        name = normalize_text(row.get(COL_NAME))
        if not name:
            skipped_rows += 1
            continue

        key_name = name.casefold()
        if key_name in seen_names:
            skipped_rows += 1
            continue

        result = build_algorithm(row, used_ids)
        if result is None:
            skipped_rows += 1
            continue

        alg_id, algorithm, implementation = result
        root[alg_id] = algorithm
        seen_names.add(key_name)
        added_algorithms += 1

        if implementation is not None:
            impl_id, impl = implementation
            root[impl_id] = impl
            added_implementations += 1

    library = Library(root=root)
    return library, added_algorithms, added_implementations, skipped_rows


def dump_library(path: Path, library: Library) -> None:
    payload = library.model_dump(mode="json")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(serialize_yaml(payload))


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if re.search(r"[\n:\\#{}\[\],&*?|<>=!%@`'\"]", text) or text.strip() != text:
        return json.dumps(text)
    return text


def serialize_yaml(value: Any, indent: int = 0) -> str:
    prefix = "  " * indent

    if isinstance(value, dict):
        if not value:
            return f"{prefix}{{}}\n"
        lines: list[str] = []
        for key, item in value.items():
            key_text = yaml_scalar(key)
            if isinstance(item, dict):
                if item:
                    lines.append(f"{prefix}{key_text}:")
                    lines.append(serialize_yaml(item, indent + 1).rstrip("\n"))
                else:
                    lines.append(f"{prefix}{key_text}: {{}}")
            elif isinstance(item, list):
                if item:
                    lines.append(f"{prefix}{key_text}:")
                    lines.append(serialize_yaml(item, indent + 1).rstrip("\n"))
                else:
                    lines.append(f"{prefix}{key_text}: []")
            else:
                lines.append(f"{prefix}{key_text}: {yaml_scalar(item)}")
        return "\n".join(lines) + "\n"

    if isinstance(value, list):
        if not value:
            return f"{prefix}[]\n"
        lines = []
        for item in value:
            if isinstance(item, dict):
                if item:
                    lines.append(f"{prefix}-")
                    lines.append(serialize_yaml(item, indent + 1).rstrip("\n"))
                else:
                    lines.append(f"{prefix}- {{}}")
            elif isinstance(item, list):
                if item:
                    lines.append(f"{prefix}-")
                    lines.append(serialize_yaml(item, indent + 1).rstrip("\n"))
                else:
                    lines.append(f"{prefix}- []")
            else:
                lines.append(f"{prefix}- {yaml_scalar(item)}")
        return "\n".join(lines) + "\n"

    return f"{prefix}{yaml_scalar(value)}\n"


def convert(csv_path: Path, output_yaml_path: Path, dry_run: bool) -> tuple[int, int, int]:
    rows = load_rows(csv_path)
    library, added_algorithms, added_implementations, skipped_rows = build_library(rows)

    if not dry_run:
        output_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        dump_library(output_yaml_path, library)

    return added_algorithms, added_implementations, skipped_rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert OAL survey responses into oaltools Algorithm and Implementation records."
    )
    parser.add_argument("--csv", default=str(CSV_PATH), help="Input CSV file")
    parser.add_argument("--output-yaml", default=str(OUTPUT_YAML_PATH), help="Output YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing output")
    args = parser.parse_args()

    added_algorithms, added_implementations, skipped_rows = convert(
        csv_path=Path(args.csv),
        output_yaml_path=Path(args.output_yaml),
        dry_run=args.dry_run,
    )

    print(f"Added algorithms: {added_algorithms}")
    print(f"Added implementations: {added_implementations}")
    print(f"Skipped rows: {skipped_rows}")
    if args.dry_run:
        print("Dry-run mode: output file was not written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
