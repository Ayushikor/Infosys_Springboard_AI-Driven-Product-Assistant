
"""Dashboard / activity routes using FastAPI."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail, mongo_docs_to_list


router = APIRouter(prefix="/api", tags=["Dashboard"])


def _error_response(message, status_code=400):
    """Convert the existing Flask-style fail() result to a FastAPI response."""

    body, status = fail(message, status=status_code)
    return JSONResponse(content=body, status_code=status)


@router.get("/activity")
def get_activity(request: Request):
    uid = request.session.get("user_id")

    if not uid:
        return _error_response("Not authenticated.", 401)

    items = mongo_docs_to_list(
        get_db()["activity"]
        .find({"userId": uid})
        .sort("at", -1)
        .limit(50)
    )

    return ok(items)