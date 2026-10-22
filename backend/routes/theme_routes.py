"""Theme routes using FastAPI."""

from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail, mongo_doc_to_dict, mongo_docs_to_list

router = APIRouter(
    prefix="/api/themes",
    tags=["Themes"],
)


def _error_response(message: str, status: int = 400, data=None):
    """Return a consistent API error response."""
    body, status_code = fail(message, data=data, status=status)
    return JSONResponse(
        content=body,
        status_code=status_code,
    )


@router.get("")
def get_all(request: Request):
    """Get all themes belonging to the authenticated user."""

    uid = request.session.get("user_id")

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    items = mongo_docs_to_list(
        get_db()["themes"].find({"userId": uid})
    )

    return ok(items)


@router.put("/{theme_id}/keywords")
def save_keywords(
    theme_id: str,
    request: Request,
    body: dict = Body(default={}),
):
    """Save keywords for an existing theme."""

    uid = request.session.get("user_id")

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    db = get_db()

    theme = db["themes"].find_one({
        "id": theme_id,
        "userId": uid,
    })

    if not theme:
        return _error_response(
            "Theme not found.",
            status=404,
        )

    keywords = body.get("keywords", [])

    if not isinstance(keywords, list):
        return _error_response(
            "keywords must be an array."
        )

    db["themes"].update_one(
        {
            "id": theme_id,
            "userId": uid,
        },
        {
            "$set": {
                "keywords": keywords,
            }
        },
    )

    updated = db["themes"].find_one({
        "id": theme_id,
        "userId": uid,
    })

    return ok(
        mongo_doc_to_dict(updated),
        "Theme keywords saved",
    )