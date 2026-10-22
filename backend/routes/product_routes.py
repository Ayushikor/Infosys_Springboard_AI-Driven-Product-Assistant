"""Product endpoints for the AI-Driven Product Assistant."""

import re
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from db import get_db
from helpers import (
    ok,
    generate_id,
    now_iso,
    mongo_doc_to_dict,
    mongo_docs_to_list,
)

router = APIRouter(prefix="/api/products", tags=["Products"])


def _current_user_id(request: Request) -> str:
    """Return the authenticated user's ID from the session."""
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to access products.",
        )

    return str(user_id)


def _product_filter(product_id: str, user_id: str) -> dict[str, Any]:
    """Restrict product operations to the authenticated user's products."""
    return {"id": product_id, "userId": user_id}


def _search_conditions(search_term: str) -> list[dict[str, Any]]:
    """Build case-insensitive product search conditions."""
    regex = {
        "$regex": re.escape(search_term),
        "$options": "i",
    }

    return [
        {"name": regex},
        {"description": regex},
        {"category": regex},
        {"tags": regex},
    ]


@router.get("")
def get_products(
    request: Request,
    q: str = Query(default=""),
    category: str = Query(default=""),
    status: str = Query(default=""),
):
    """Retrieve the logged-in user's products with optional filters."""
    user_id = _current_user_id(request)

    mongo_filter: dict[str, Any] = {"userId": user_id}

    if category.strip():
        mongo_filter["category"] = category.strip()

    if status.strip():
        mongo_filter["status"] = status.strip()

    if q.strip():
        mongo_filter["$or"] = _search_conditions(q.strip())

    try:
        products = mongo_docs_to_list(
            get_db()["products"]
            .find(mongo_filter)
            .sort("createdAt", -1)
        )
        return ok(products)

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Database query failed.",
        )


@router.get("/search")
def search_products(
    request: Request,
    q: str = Query(default=""),
    query: str = Query(default=""),
):
    """Search the logged-in user's products."""
    user_id = _current_user_id(request)
    search_term = q.strip() or query.strip()

    if not search_term:
        raise HTTPException(
            status_code=400,
            detail="Search query parameter 'q' or 'query' is required.",
        )

    mongo_filter = {
        "userId": user_id,
        "$or": _search_conditions(search_term),
    }

    try:
        results = mongo_docs_to_list(
            get_db()["products"].find(mongo_filter).limit(50)
        )

        return ok(
            results,
            message=f"Found {len(results)} matching product(s)",
        )

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Database search failed.",
        )


@router.get("/{product_id}")
def get_product_by_id(product_id: str, request: Request):
    """Retrieve a product belonging to the logged-in user."""
    user_id = _current_user_id(request)

    try:
        product = get_db()["products"].find_one(
            _product_filter(product_id.strip(), user_id)
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found.",
            )

        return ok(mongo_doc_to_dict(product))

    except HTTPException:
        raise

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Database query failed.",
        )


@router.post("")
def create_product(
    request: Request,
    body: dict[str, Any] = Body(default={}),
):
    """Create a product for the logged-in user."""
    user_id = _current_user_id(request)
    name = str(body.get("name") or "").strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Product name is required.",
        )

    product_doc = {
        "id": generate_id("prod-"),
        "userId": user_id,
        "name": name,
        "description": str(body.get("description") or "").strip(),
        "category": str(body.get("category") or "General").strip(),
        "status": str(body.get("status") or "Active").strip(),
        "tags": (
            body.get("tags")
            if isinstance(body.get("tags"), list)
            else []
        ),
        "attributes": (
            body.get("attributes")
            if isinstance(body.get("attributes"), dict)
            else {}
        ),
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }

    try:
        get_db()["products"].insert_one(product_doc)

        return ok(
            mongo_doc_to_dict(product_doc),
            message="Product created successfully",
        )

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Failed to create product.",
        )


@router.put("/{product_id}")
def update_product(
    product_id: str,
    request: Request,
    body: dict[str, Any] = Body(default={}),
):
    """Update a product belonging to the logged-in user."""
    user_id = _current_user_id(request)
    db = get_db()
    product_filter = _product_filter(product_id.strip(), user_id)

    try:
        existing = db["products"].find_one(product_filter)

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Product not found.",
            )

        updates: dict[str, Any] = {"updatedAt": now_iso()}

        for field in (
            "name",
            "description",
            "category",
            "status",
            "tags",
            "attributes",
        ):
            if field in body:
                updates[field] = body[field]

        if "name" in updates:
            updates["name"] = str(updates["name"] or "").strip()

            if not updates["name"]:
                raise HTTPException(
                    status_code=400,
                    detail="Product name cannot be empty.",
                )

        db["products"].update_one(
            product_filter,
            {"$set": updates},
        )

        updated = db["products"].find_one(product_filter)

        return ok(
            mongo_doc_to_dict(updated),
            message="Product updated successfully",
        )

    except HTTPException:
        raise

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Failed to update product.",
        )


@router.delete("/{product_id}")
def delete_product(product_id: str, request: Request):
    """Delete a product belonging to the logged-in user."""
    user_id = _current_user_id(request)
    product_filter = _product_filter(product_id.strip(), user_id)

    try:
        result = get_db()["products"].delete_one(product_filter)

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Product not found.",
            )

        return ok(
            {"id": product_id},
            message="Product deleted successfully",
        )

    except HTTPException:
        raise

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete product.",
        )