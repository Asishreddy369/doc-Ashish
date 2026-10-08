import calendar
import re
from collections import defaultdict
from datetime import datetime


MONTH_NAMES = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
MONTH_ABBR = {name.lower(): index for index, name in enumerate(calendar.month_abbr) if name}
MONTH_LOOKUP = {**MONTH_NAMES, **MONTH_ABBR}

DEFAULT_STRUCTURE_LEVELS = ["category", "year", "month"]

CATEGORY_ALIASES = {
    "Accounts and Bank Related Documents": "Bank Statements",
    "Accounts and Bank related Documents": "Bank Statements",
    "Bank Statement": "Bank Statements",
    "GST Certificate": "GST",
    "Tax": "Tax Documents",
    "Tax Filing": "Tax Documents",
    "Invoice": "Invoices",
    "Proforma Invoice": "Invoices",
    "Purchase Order": "Purchase Orders",
    "PAN": "PAN",
    "Aadhaar": "Aadhaar",
    "Certificates and Registration": "Certificates",
    "Land And Building": "Land and Building",
    "Land and Building": "Land and Building",
    "Loans and Debt": "Loans and Debt",
    "Share Capital and Other Instruments Issued": "Share Capital",
    "Share Capital and Other Instruments issued": "Share Capital",
    "Insurance": "Insurance",
    "Power": "Power",
    "Other": "Other Documents",
    "Unclassified": "Other Documents",
}

KEYWORD_CATEGORY_PATTERNS = [
    ("Bank Statements", [r"\bbank\b", r"\bacct\b", r"account statement", r"statement"]),
    ("GST", [r"\bgstr?\b", r"gstin", r"challan", r"gstr1", r"gstr2b", r"gstr3b"]),
    ("Invoices", [r"invoice", r"\binv\b", r"\bpi\b", r"proforma"]),
    ("Purchase Orders", [r"purchase order", r"\bpo\b"]),
    ("PAN", [r"\bpan\b"]),
    ("Aadhaar", [r"aadhaar", r"adhar"]),
    ("Certificates", [r"certificate", r"registration", r"licen[cs]e"]),
    ("Employee Documents", [r"employee", r"offer letter", r"salary", r"appointment"]),
    ("Tax Documents", [r"income tax", r"\btds\b", r"26q", r"return"]),
]


def sanitize_folder_name(value, fallback="Other Documents"):
    value = str(value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:120] or fallback


def canonical_category(category):
    category = sanitize_folder_name(category, "Other Documents")
    return CATEGORY_ALIASES.get(category, category)


def _canonical_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _folder_parts(value):
    return [
        sanitize_folder_name(part)
        for part in str(value or "").replace("\\", "/").split("/")
        if str(part).strip()
    ]


def _resolve_user_folder(category, folder_options):
    folder_options = folder_options or {}
    folders = [
        "/".join(_folder_parts(folder))
        for folder in folder_options.get("folders", [])
        if _folder_parts(folder)
    ]
    folder_by_key = {_canonical_key(folder): folder for folder in folders}
    folder_by_leaf_key = {
        _canonical_key(_folder_parts(folder)[-1]): folder
        for folder in folders
        if _folder_parts(folder)
    }
    fallback = "/".join(_folder_parts(folder_options.get("fallback_folder") or "Unclassified")) or "Unclassified"
    category_folder_map = folder_options.get("category_folder_map") or {}

    mapped_folder = (
        category_folder_map.get(category)
        or category_folder_map.get(canonical_category(category))
        or category_folder_map.get(_canonical_key(category))
    )
    mapped_parts = _folder_parts(mapped_folder)
    if mapped_parts:
        mapped_value = "/".join(mapped_parts)
        mapped_key = _canonical_key(mapped_value)
        mapped_leaf_key = _canonical_key(mapped_parts[-1])
        if not folders:
            return mapped_parts, False
        if mapped_key in folder_by_key:
            return _folder_parts(folder_by_key[mapped_key]), False
        if mapped_leaf_key in folder_by_leaf_key:
            return _folder_parts(folder_by_leaf_key[mapped_leaf_key]), False

    category_key = _canonical_key(category)
    canonical_key = _canonical_key(canonical_category(category))
    for candidate_key in (category_key, canonical_key):
        if candidate_key in folder_by_key:
            return _folder_parts(folder_by_key[candidate_key]), False
        if candidate_key in folder_by_leaf_key:
            return _folder_parts(folder_by_leaf_key[candidate_key]), False

    return _folder_parts(fallback), True


def infer_category_from_name(name, fallback="Other Documents"):
    text = re.sub(r"[_\-./]+", " ", str(name or "").lower())
    for category, patterns in KEYWORD_CATEGORY_PATTERNS:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            return category
    return canonical_category(fallback)


def month_name(month):
    try:
        month = int(month)
    except (TypeError, ValueError):
        return "Other Months"
    if 1 <= month <= 12:
        return calendar.month_name[month]
    return "Other Months"


def infer_date_parts(*values):
    text = " ".join(str(value or "") for value in values)
    normalized = re.sub(r"[_\-]+", " ", text)

    # 1. Look for explicit linked Month Name + Year patterns
    # Sort months by length descending (e.g. "september" before "sep")
    for word, m_val in sorted(MONTH_LOOKUP.items(), key=lambda x: -len(x[0])):
        w_esc = re.escape(word)
        patterns = [
            # Day Month Year (e.g. 12 September 2026, 12th Sept 2026)
            rf"\b(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?[\s,]+{w_esc}[\s,]+(20[0-4][0-9])\b",
            # Month Day, Year (e.g. September 12, 2026)
            rf"\b{w_esc}[\s,]+(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?[\s,]+(20[0-4][0-9])\b",
            # Month Year (e.g. September 2026, Sep 2026)
            rf"\b{w_esc}[\s,]+(20[0-4][0-9])\b",
            # Year Month (e.g. 2026 September)
            rf"\b(20[0-4][0-9])[\s,]+{w_esc}\b",
        ]
        for p in patterns:
            match = re.search(p, normalized, re.IGNORECASE)
            if match:
                return int(match.group(1)), m_val

    # 2. Look for numeric dates: DD/MM/YYYY, YYYY/MM/DD, MM/YYYY, YYYY/MM
    for pattern in (
        r"\b(0?[1-9]|[12][0-9]|3[01])[\s./-](0?[1-9]|1[0-2])[\s./-](20[0-4][0-9])\b",
        r"\b(20[0-4][0-9])[\s./-](0?[1-9]|1[0-2])[\s./-](0?[1-9]|[12][0-9]|3[01])\b",
        r"\b(0?[1-9]|1[0-2])[\s./-](20[0-4][0-9])\b",
        r"\b(20[0-4][0-9])[\s./-](0?[1-9]|1[0-2])\b",
    ):
        match = re.search(pattern, normalized)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 3:
            if groups[0].startswith("20"):
                return int(groups[0]), int(groups[1])
            return int(groups[2]), int(groups[1])
        if len(groups) == 2:
            if groups[0].startswith("20"):
                return int(groups[0]), int(groups[1])
            return int(groups[1]), int(groups[0])

    # 3. Compact dates:
    compact_date = re.search(r"\b(0[1-9]|[12][0-9]|3[01])(0[1-9]|1[0-2])(20[0-4][0-9])\b", normalized)
    if compact_date:
        return int(compact_date.group(3)), int(compact_date.group(2))

    compact_iso = re.search(r"\b(20[0-4][0-9])(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])\b", normalized)
    if compact_iso:
        return int(compact_iso.group(1)), int(compact_iso.group(2))

    compact = re.search(r"\b(0[1-9]|1[0-2])(20[0-4][0-9])\b", normalized)
    if compact:
        return int(compact.group(2)), int(compact.group(1))

    # 4. Fallback: single month word (safeguarding "may" against modal verb usage)
    month_word = None
    for word, value in sorted(MONTH_LOOKUP.items(), key=lambda x: -len(x[0])):
        if word == "may":
            # "may" must be adjacent to numbers or capitalized May, not "may require/may be"
            if re.search(r"\b(?:0?[1-9]|[12][0-9]|3[01])\s+may\b|\bmay\s+(?:0?[1-9]|[12][0-9]|3[01]|20[0-4][0-9])\b|\bMay\b", text):
                month_word = value
                break
        else:
            if re.search(rf"\b{re.escape(word)}\b", normalized, re.IGNORECASE):
                month_word = value
                break

    year_match = re.search(r"\b(20[0-4][0-9])\b", normalized)
    short_year = re.search(r"\b([0-9]{2})\b", normalized)
    if month_word and not year_match and short_year:
        year = 2000 + int(short_year.group(1))
        if 2020 <= year <= 2049:
            return year, month_word

    if year_match and month_word:
        return int(year_match.group(1)), month_word

    if year_match:
        return int(year_match.group(1)), None

    return None, None


def build_tree(paths):
    tree = {}
    for path in paths:
        node = tree
        for part in path:
            node = node.setdefault(part, {})
    return tree


def flatten_tree(tree, depth=0, sort_names=True):
    lines = []
    items = sorted(tree.items()) if sort_names else tree.items()
    for name, child in items:
        lines.append({"name": name, "depth": depth})
        lines.extend(flatten_tree(child, depth + 1, sort_names=sort_names))
    return lines


def user_defined_template_paths(folder_options):
    folder_options = folder_options or {}
    root_parts = _folder_parts(folder_options.get("root_folder"))
    folders = folder_options.get("folders") or []
    paths = []
    seen = set()

    def add_path(parts):
        if not parts:
            return
        key = "/".join(parts)
        if key in seen:
            return
        seen.add(key)
        paths.append(parts)

    add_path(root_parts)
    for folder in folders:
        full_parts = root_parts + _folder_parts(folder)
        for depth in range(1, len(full_parts) + 1):
            add_path(full_parts[:depth])

    return paths


def plan_document_route(item, structure_levels=None, category_map=None, mode="auto", folder_options=None):
    structure_levels = structure_levels or DEFAULT_STRUCTURE_LEVELS
    category_map = category_map or {}
    folder_options = folder_options or {}

    name = item.get("name") or item.get("original_name") or ""
    relative_path = item.get("relative_path") or item.get("webkitRelativePath") or ""
    detected_category = item.get("category") or item.get("detected_category") or item.get("classifier_category")
    raw_category = detected_category if mode == "user_defined" else category_map.get(detected_category, detected_category)
    if mode == "user_defined":
        category = sanitize_folder_name(raw_category or infer_category_from_name(f"{relative_path} {name}"), "Unclassified")
    else:
        category = canonical_category(raw_category or infer_category_from_name(f"{relative_path} {name}"))

    now = datetime.now()
    year = item.get("year") or now.year
    month = item.get("month") or now.month

    relative_parts = [part for part in str(relative_path or "").replace("\\", "/").split("/") if part]

    route_context = {
        "category": category,
        "year": str(year) if year else "Unknown Year",
        "month": month_name(month),
        "document_type": category,
        "source_folder": sanitize_folder_name(relative_parts[0] if relative_parts else "", "Uploaded Documents"),
        "original_folder": sanitize_folder_name(relative_parts[1] if len(relative_parts) > 1 else "", "Unsorted"),
    }

    custom_unmatched = False
    if mode == "user_defined":
        root_parts = _folder_parts(folder_options.get("root_folder"))
        mapped_parts, custom_unmatched = _resolve_user_folder(category, folder_options)
        path = root_parts + mapped_parts
    else:
        path = []
        for level in structure_levels:
            value = route_context.get(level, level)
            if value:
                path.append(sanitize_folder_name(value))

    if not path:
        path = ["Other Documents"]

    return {
        "file": name,
        "relative_path": relative_path,
        "target_parts": path,
        "target_folder": "/".join(path),
        "category": category,
        "year": year,
        "month": month,
        "custom_unmatched": custom_unmatched,
    }


def build_folder_plan(items, mode="auto", structure_levels=None, category_map=None, folder_options=None):
    # BUG-B04 FIX: Both if/else branches were identical — collapsed into one line.
    structure_levels = structure_levels or DEFAULT_STRUCTURE_LEVELS

    routes = [
        plan_document_route(
            item,
            structure_levels,
            category_map,
            mode=mode,
            folder_options=folder_options,
        )
        for item in items
    ]
    tree_paths = []
    if mode == "user_defined":
        tree_paths.extend(user_defined_template_paths(folder_options))
    tree_paths.extend(route["target_parts"] for route in routes)
    tree = build_tree(tree_paths)

    category_counts = defaultdict(int)
    year_counts = defaultdict(int)
    unmatched_count = 0
    for route in routes:
        category_counts[route["category"]] += 1
        if route["year"]:
            year_counts[str(route["year"])] += 1
        if route.get("custom_unmatched"):
            unmatched_count += 1

    return {
        "mode": mode,
        "structure_levels": structure_levels,
        "folder_options": folder_options or {},
        "tree": tree,
        "tree_lines": flatten_tree(tree, sort_names=mode != "user_defined"),
        "routes": routes,
        "summary": {
            "document_count": len(routes),
            "category_counts": dict(sorted(category_counts.items())),
            "year_counts": dict(sorted(year_counts.items())),
            "unmatched_count": unmatched_count,
        },
    }
