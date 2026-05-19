#!/usr/bin/env python3
import pandas as pd
import re
import shutil
from html import escape

from pydantic_yaml import parse_yaml_raw_as

from oaltools.schema import Algorithm, Implementation, Library, recommended_tags

URL_RE = re.compile(r"\b((?:https?://|www\.)[^\s<>\"']+)", re.IGNORECASE)

COLUMN_DISPLAY_NAMES = {
    "algorithm_id": "ID",
    "name": "Name",
    "long_name": "Full Name",
    "description": "Description",
    "objectives": "Objectives",
    "Variable Types": "Variable Types",
    "number_variables": "# Variables",
    "Constraint Types": "Constraint Types",
    "recommended_budget": "Budget",
    "Dynamics": "Dynamics",
    "Noise": "Noise",
    "Modality": "Modality",
    "partial_evaluation": "Partial Eval.",
    "can_evaluate_objectives_independently": "Indep. Objectives",
    "fidelity_levels": "Fidelity Levels",
    "tags": "Tags",
    "references": "References",
    "implementations": "Implementations",
    "code_examples": "Code Examples",
    "source": "Source",
}

DEFAULT_VISIBLE_COLUMNS = {
    "Name",
    "Objectives",
    "Variable Types",
    "# Variables",
    "Constraint Types",
    "Dynamics",
    "Noise",
    "Modality",
    "Tags",
    "Partial Eval.",
    "Indep. Objectives",
    "Budget",
}

# Preferred column order in the rendered table
COLUMN_ORDER = [
    "algorithm_id",
    "name",
    "objectives",
    "Variable Types",
    "number_variables",
    "Constraint Types",
    "Dynamics",
    "Noise",
    "Modality",
    "partial_evaluation",
    "can_evaluate_objectives_independently",
    "recommended_budget",
    "fidelity_levels",
    "long_name",
    "description",
    "tags",
    "references",
    "implementations",
    "code_examples",
    "source",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def display_column_name(column):
    mapped = COLUMN_DISPLAY_NAMES.get(column)
    if mapped:
        return mapped
    text = str(column or "").replace("_", " ").strip()
    return " ".join(
        "ID" if word.lower() == "id" else word.capitalize()
        for word in text.split()
    ) if text else str(column)


def unique_preserve_order(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def linkify_cell(value):
    if not isinstance(value, str):
        return value

    def repl(match):
        url = match.group(1)
        href = url if url.lower().startswith(("http://", "https://")) else f"https://{url}"
        return f'<a href="{href}">{url}</a>'

    return URL_RE.sub(repl, value)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_value_range(vr):
    if vr is None:
        return ""
    if hasattr(vr, "model_dump"):
        vr = vr.model_dump()
    if isinstance(vr, dict):
        vmin, vmax = vr.get("min"), vr.get("max")
        if vmin is not None and vmax is not None:
            return str(vmin) if vmin == vmax else f"{vmin}\u2013{vmax}"
        if vmin is not None:
            return f">={vmin}"
        if vmax is not None:
            return f"<={vmax}"
    return str(vr)


def format_objectives(obj):
    if obj is None:
        return ""
    root = obj.root if hasattr(obj, "root") else obj
    if isinstance(root, int):
        return str(root)
    if isinstance(root, set):
        items = sorted(root)
        return str(items[0]) if len(items) == 1 else "{" + ", ".join(str(i) for i in items) + "}"
    return format_value_range(root)


def _supports_text(supports):
    """Return a short readable label for a Supports enum value, empty for unknown."""
    if supports is None:
        return ""
    text = str(supports).lower().split(".")[-1].strip()
    return "" if text in {"unknown", "none", "null", ""} else text


def format_supports_type_set(items):
    """Format a set of SupportsType objects.
    Shows 'type' for default support, 'type (supports)' otherwise.
    """
    if not items:
        return ""
    parts = []
    for item in items:
        d = item.model_dump() if hasattr(item, "model_dump") else item
        if not isinstance(d, dict):
            continue
        type_text = str(d.get("type") or "").strip()
        sup = _supports_text(d.get("supports"))
        if not type_text:
            continue
        parts.append(f"{type_text} ({sup})" if sup and sup != "default" else type_text)
    return " | ".join(unique_preserve_order(parts))


def format_feature_support(item):
    """Format a FeatureSupport as a short human-readable string."""
    if item is None:
        return ""
    d = item.model_dump() if hasattr(item, "model_dump") else item
    if not isinstance(d, dict):
        return ""
    sup = _supports_text(d.get("supports"))
    if not sup:
        return ""
    return "yes" if sup == "default" else sup


def list_variable_types(variable_types):
    if not variable_types:
        return ""
    types = []
    for v in variable_types:
        vd = v.model_dump() if hasattr(v, "model_dump") else v
        if isinstance(vd, dict):
            t = str(vd.get("type") or "").lower().split(".")[-1].strip()
            if t:
                types.append(t)
    return " | ".join(t for t in unique_preserve_order(types) if t)


def list_constraint_types(constraint_types):
    if not constraint_types:
        return ""
    types = []
    for c in constraint_types:
        cd = c.model_dump() if hasattr(c, "model_dump") else c
        if isinstance(cd, dict):
            t = str(cd.get("type") or "").lower().split(".")[-1].strip()
            if t:
                types.append(t)
    return " | ".join(t for t in unique_preserve_order(types) if t)


def format_references(refs):
    if not refs:
        return ""
    parts = []
    for ref in refs:
        rd = ref.model_dump() if hasattr(ref, "model_dump") else ref
        if not isinstance(rd, dict):
            parts.append(str(rd))
            continue
        title = str(rd.get("title") or "").strip()
        authors = rd.get("authors") or []
        authors_txt = "; ".join(str(a) for a in authors if a)
        link = rd.get("link") or {}
        if hasattr(link, "model_dump"):
            link = link.model_dump()
        url = str(link.get("url") or "").strip() if isinstance(link, dict) else ""
        triplet = ", ".join(p for p in [title, authors_txt, url] if p)
        if triplet:
            parts.append(triplet)
    return " | ".join(parts)


def format_implementations(impl_ids, library_items):
    if not impl_ids:
        return ""
    names = []
    for impl_id in impl_ids:
        impl = library_items.get(impl_id)
        if isinstance(impl, Implementation) and impl.name:
            names.append(impl.name)
        elif impl_id:
            names.append(impl_id)
    return " | ".join(unique_preserve_order(names))


def format_tags(tags):
    if not tags:
        return ""
    chips = []
    for tag in sorted(tags, key=str.lower):
        safe_tag = escape(tag, quote=True)
        chips.append(
            f'<button type="button" class="table-tag" data-tag="{safe_tag}">{safe_tag}</button>'
        )
    return " ".join(chips)


def build_tag_groups(algorithms):
    tag_to_category = {}
    tag_to_category_lower = {}
    category_order = []

    for entry in recommended_tags:
        for category, tags in entry.items():
            category_order.append(category)
            for tag in tags:
                tag_to_category[tag] = category
                tag_to_category_lower[str(tag).lower()] = category

    grouped = {category: [] for category in category_order}
    grouped["other"] = []

    for alg in algorithms.values():
        for tag in sorted(alg.tags or set(), key=str.lower):
            category = tag_to_category.get(tag)
            if category is None:
                category = tag_to_category_lower.get(str(tag).lower(), "other")
            grouped.setdefault(category, []).append(tag)

    # Keep only categories that have tags present in the current table.
    result = {}
    for category in category_order + ["other"]:
        values = unique_preserve_order(grouped.get(category, []))
        if values:
            result[category] = values
    return result


# ---------------------------------------------------------------------------
# DataFrame construction
# ---------------------------------------------------------------------------

def build_algorithm_dataframe(library):
    library_items = library.root if hasattr(library, "root") else {}
    algorithms = {k: v for k, v in library_items.items() if isinstance(v, Algorithm)}

    rows = []
    for alg_id, alg in algorithms.items():
        rows.append({
            "algorithm_id": alg_id,
            "name": alg.name or "",
            "long_name": alg.long_name or "",
            "description": alg.description or "",
            "objectives": format_objectives(alg.objectives),
            "Variable Types": list_variable_types(alg.variable_types),
            "number_variables": format_value_range(alg.number_variables),
            "Constraint Types": list_constraint_types(alg.constraint_types),
            "Dynamics": format_supports_type_set(alg.dynamics),
            "Noise": format_supports_type_set(alg.noise),
            "Modality": format_supports_type_set(alg.modality_types),
            "partial_evaluation": format_feature_support(alg.partial_evaluation),
            "can_evaluate_objectives_independently": format_feature_support(
                alg.can_evaluate_objectives_independently
            ),
            "recommended_budget": format_value_range(alg.recommended_budget),
            "fidelity_levels": format_value_range(alg.fidelity_levels),
            "tags": format_tags(alg.tags),
            "references": format_references(alg.references),
            "implementations": format_implementations(alg.implementations, library_items),
            "code_examples": " | ".join(sorted(alg.code_examples)) if alg.code_examples else "",
            "source": " | ".join(sorted(alg.source)) if alg.source else "",
        })

    dataframe = pd.DataFrame(rows, columns=COLUMN_ORDER)
    dataframe = dataframe.fillna("")
    return dataframe.rename(columns=display_column_name), build_tag_groups(algorithms)


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def render_table(dataframe):
    linked = dataframe.map(linkify_cell)
    table_html = linked.to_html(
        render_links=False,
        escape=False,
        index=False,
        table_id="algorithms",
        classes=["display compact", "display", "styled-table"],
        border=0,
        na_rep="",
    )
    footer = (
        "<tfoot><tr>"
        + " ".join(f"<th>{escape(col)}</th>" for col in dataframe.columns)
        + "</tr></tfoot>"
    )
    idx = table_html.index("</table>")
    return table_html[:idx] + footer + table_html[idx:]


def render_column_toggles(columns):
    return "".join(
        f'<label class="column-chip">'
        f'<input class="col-toggle" type="checkbox" data-column="{i}"'
        f'{" checked" if col in DEFAULT_VISIBLE_COLUMNS else ""}>'
        f'<span>{escape(col)}</span>'
        f'</label>'
        for i, col in enumerate(columns)
    )


def render_tag_filters(tag_groups):
    if not tag_groups:
        return ""

    parts = [
        '<details class="tag-toolbar-disclosure" open>',
        '<summary class="toolbar-title">Filter By Tags</summary>',
        '<div class="tag-toolbar-actions">',
        '<button type="button" class="toolbar-btn" id="clear-tag-filter">Clear tag filter</button>',
        '<span class="tag-filter-status" id="active-tag-filter">No active tag filter</span>',
        '</div>',
        '<div class="tag-groups">',
    ]

    for category, tags in tag_groups.items():
        chips = "".join(
            f'<button type="button" class="tag-filter-chip" data-tag="{escape(tag, quote=True)}">{escape(tag)}</button>'
            for tag in sorted(tags, key=str.lower)
        )
        parts.append(
            '<section class="tag-group">'
            f'<h4 class="tag-group-title">{escape(category.title())}</h4>'
            f'<div class="tag-group-chips">{chips}</div>'
            '</section>'
        )

    parts.append('</div></details>')
    return "".join(parts)


def load_library(path):
    with open(path, encoding="utf-8") as f:
        return parse_yaml_raw_as(Library, f.read())


def build_html_page(table_markup, docs_dir):
    html_table = f"{docs_dir}algorithms.html"
    with open(html_table, "w", encoding="utf-8") as f:
        f.write(table_markup)

    with open(f"{docs_dir}index.html", "wb") as out:
        for part in [
            f"{docs_dir}header.html",
            html_table,
            f"{docs_dir}javascript.html",
            f"{docs_dir}footer.html",
        ]:
            with open(part, "rb") as f:
                shutil.copyfileobj(f, out)


if __name__ == "__main__":
    yaml_file = "algorithms.yaml"
    docs_dir = "docs/"
    table_template_path = f"{docs_dir}table_template.html"

    try:
        library = load_library(yaml_file)
    except Exception as exc:
        raise SystemExit(f"Error parsing '{yaml_file}': {exc}") from exc

    data, tag_groups = build_algorithm_dataframe(library)
    final_table = render_table(data)
    column_toggles = render_column_toggles(data.columns)
    tag_filters = render_tag_filters(tag_groups)

    with open(table_template_path, encoding="utf-8") as f:
        template = f.read()

    table_markup = (
        template
        .replace("__TAG_FILTERS__", tag_filters)
        .replace("__COLUMN_TOGGLES__", column_toggles)
        .replace("__TABLE__", final_table)
    )
    build_html_page(table_markup, docs_dir)
