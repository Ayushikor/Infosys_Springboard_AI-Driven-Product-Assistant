"""Product endpoints for retrieving and searching product information.

Provides endpoints to list, search, retrieve by ID, create, update, and delete
product records stored in the configured MongoDB 'products' collection.
"""

import re
from flask import Blueprint, request, session
from db import get_db
from helpers import (
    ok, fail, generate_id, now_iso,
    mongo_doc_to_dict, mongo_docs_to_list,
)

product_bp = Blueprint("products", __name__, url_prefix="/api/products")


def _user_id():
    """Optional user context if logged in."""
    return session.get("user_id")


@product_bp.route("", methods=["GET"])
def get_products():
    """Retrieve product records with optional query search.

    Query parameters supported:
      - q: Search string matching name, description, category, or tags
      - category: Filter by exact category
      - status: Filter by status (e.g., Active, In Development, Archived)
    """
    db = get_db()
    query_param = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()

    mongo_filter = {}

    # If the user is logged in, optionally scope to user or allow public/shared products
    uid = _user_id()
    if uid:
        # Include records matching this user OR records without a specific userId (shared/catalog)
        mongo_filter["$or"] = [{"userId": uid}, {"userId": {"$exists": False}}]

    if category:
        mongo_filter["category"] = category

    if status:
        mongo_filter["status"] = status

    if query_param:
        search_regex = {"$regex": re.escape(query_param), "$options": "i"}
        text_clause = [
            {"name": search_regex},
            {"description": search_regex},
            {"category": search_regex},
            {"tags": search_regex},
        ]
        if "$or" in mongo_filter:
            mongo_filter = {"$and": [mongo_filter, {"$or": text_clause}]}
        else:
            mongo_filter["$or"] = text_clause

    try:
        cursor = db["products"].find(mongo_filter).sort("createdAt", -1)
        products = mongo_docs_to_list(cursor)
        return ok(products)
    except Exception as exc:
        return fail(f"Database query failed: {str(exc)}", status=500)


@product_bp.route("/search", methods=["GET"])
def search_products():
    """Dedicated search endpoint for product information."""
    query = request.args.get("q", "").strip() or request.args.get("query", "").strip()
    if not query:
        return fail("Search query parameter 'q' or 'query' is required.", status=400)

    db = get_db()
    regex = {"$regex": re.escape(query), "$options": "i"}
    mongo_filter = {
        "$or": [
            {"name": regex},
            {"description": regex},
            {"category": regex},
            {"tags": regex},
        ]
    }

    try:
        results = mongo_docs_to_list(db["products"].find(mongo_filter).limit(50))
        return ok(results, message=f"Found {len(results)} matching product(s)")
    except Exception as exc:
        return fail(f"Database search failed: {str(exc)}", status=500)


@product_bp.route("/<product_id>", methods=["GET"])
def get_product_by_id(product_id):
    """Retrieve a single product by ID. Returns 404 for missing products."""
    if not product_id or not product_id.strip():
        return fail("Invalid product ID.", status=400)

    db = get_db()
    try:
        product = db["products"].find_one({"id": product_id.strip()})
        if not product:
            return fail("Product not found.", status=404)
        return ok(mongo_doc_to_dict(product))
    except Exception as exc:
        return fail(f"Database query failed: {str(exc)}", status=500)


@product_bp.route("", methods=["POST"])
def create_product():
    """Create a new product record."""
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return fail("Product name is required.", status=400)

    uid = _user_id()
    product_doc = {
        "id": generate_id("prod-"),
        "name": name,
        "description": (body.get("description") or "").strip(),
        "category": (body.get("category") or "General").strip(),
        "status": (body.get("status") or "Active").strip(),
        "tags": body.get("tags") if isinstance(body.get("tags"), list) else [],
        "attributes": body.get("attributes") if isinstance(body.get("attributes"), dict) else {},
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    if uid:
        product_doc["userId"] = uid

    db = get_db()
    try:
        db["products"].insert_one(product_doc)
        return ok(mongo_doc_to_dict(product_doc), message="Product created successfully")
    except Exception as exc:
        return fail(f"Failed to create product: {str(exc)}", status=500)


@product_bp.route("/<product_id>", methods=["PUT"])
def update_product(product_id):
    """Update an existing product record."""
    db = get_db()
    existing = db["products"].find_one({"id": product_id})
    if not existing:
        return fail("Product not found.", status=404)

    body = request.get_json(silent=True) or {}
    updates = {"updatedAt": now_iso()}

    for field in ("name", "description", "category", "status", "tags", "attributes"):
        if field in body:
            updates[field] = body[field]

    try:
        db["products"].update_one({"id": product_id}, {"$set": updates})
        updated = db["products"].find_one({"id": product_id})
        return ok(mongo_doc_to_dict(updated), message="Product updated successfully")
    except Exception as exc:
        return fail(f"Failed to update product: {str(exc)}", status=500)


@product_bp.route("/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    """Delete a product by ID."""
    db = get_db()
    existing = db["products"].find_one({"id": product_id})
    if not existing:
        return fail("Product not found.", status=404)

    try:
        db["products"].delete_one({"id": product_id})
        return ok({"id": product_id}, message="Product deleted successfully")
    except Exception as exc:
        return fail(f"Failed to delete product: {str(exc)}", status=500)
