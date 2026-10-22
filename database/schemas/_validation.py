"""Small, dependency-free validation helpers shared by the schema modules.

Every ``validate_*`` function returns a list of error strings; an empty list
means the document is valid. Unknown extra fields are always allowed so the
helpers never reject documents the existing routes already store.
"""

import functools
import re
from datetime import datetime

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def document_validator(fn):
    """Wrap ``fn(doc, errors)`` so it returns the list of errors."""

    @functools.wraps(fn)
    def wrapper(doc):
        if not isinstance(doc, dict):
            return ["document must be an object"]
        errors = []
        fn(doc, errors)
        return errors

    return wrapper


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def require_str(doc, field, errors, min_len=1):
    value = doc.get(field)
    if not isinstance(value, str) or len(value.strip()) < min_len:
        suffix = f" (at least {min_len} characters)" if min_len > 1 else ""
        errors.append(f"{field}: required non-empty string{suffix}")


def optional_str(doc, field, errors):
    if field in doc and not isinstance(doc[field], str):
        errors.append(f"{field}: must be a string")


def optional_enum(doc, field, allowed, errors):
    if field in doc and doc[field] not in allowed:
        errors.append(f"{field}: must be one of {sorted(allowed)}")


def optional_number(doc, field, errors, minimum=None, maximum=None):
    if field not in doc:
        return
    value = doc[field]
    if not is_number(value):
        errors.append(f"{field}: must be a number")
    elif minimum is not None and value < minimum:
        errors.append(f"{field}: must be >= {minimum}")
    elif maximum is not None and value > maximum:
        errors.append(f"{field}: must be <= {maximum}")


def optional_list_of_str(doc, field, errors):
    if field in doc:
        value = doc[field]
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(f"{field}: must be a list of strings")


def optional_dict(doc, field, errors):
    if field in doc and not isinstance(doc[field], dict):
        errors.append(f"{field}: must be an object")


def optional_iso(doc, field, errors):
    """ISO-8601 timestamp string, as produced by ``helpers.now_iso()``."""
    if field not in doc:
        return
    value = doc[field]
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if not isinstance(value, str):
            raise ValueError
    except ValueError:
        errors.append(f"{field}: must be an ISO-8601 timestamp string")


def optional_date_or_empty(doc, field, errors):
    """'' (not set) or a YYYY-MM-DD string."""
    if field not in doc:
        return
    value = doc[field]
    if value != "" and not (isinstance(value, str) and _DATE_RE.match(value)):
        errors.append(f"{field}: must be '' or a YYYY-MM-DD string")
