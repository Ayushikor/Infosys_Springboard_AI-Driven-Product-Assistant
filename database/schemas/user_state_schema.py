"""``user_state`` collection: one document per user (active workspace + preferences).

Preferences are an embedded object here; there is no separate collection.
"""

from ._validation import document_validator, optional_dict, optional_str, require_str

COLLECTION = "user_state"

FIELDS = {
    "userId": "str, required. References users.id. Unique.",
    "activeWorkspaceId": "str, optional. Soft reference to workspaces.id.",
    "preferences": "object, optional. Known keys: theme (str, default 'light'), "
    "compactTables (bool, default false). Other keys are allowed.",
}

EXAMPLE = {
    "userId": "usr-1a2b3c4d5e",
    "activeWorkspaceId": "ws-0a1b2c3d4e",
    "preferences": {"theme": "light", "compactTables": False},
}


@document_validator
def validate_user_state(doc, errors):
    require_str(doc, "userId", errors)
    optional_str(doc, "activeWorkspaceId", errors)
    optional_dict(doc, "preferences", errors)
    prefs = doc.get("preferences")
    if isinstance(prefs, dict):
        if "theme" in prefs and not isinstance(prefs["theme"], str):
            errors.append("preferences.theme: must be a string")
        if "compactTables" in prefs and not isinstance(prefs["compactTables"], bool):
            errors.append("preferences.compactTables: must be a boolean")
