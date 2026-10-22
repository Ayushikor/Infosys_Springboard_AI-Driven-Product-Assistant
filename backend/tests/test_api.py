"""Basic API tests using Flask's test client.

These tests mock the MongoDB database layer so they can run reliably in any
environment without requiring an active external MongoDB instance.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# In-Memory Mock Database
# ---------------------------------------------------------------------------

class MockCursor(list):
    """Iterable mock cursor that supports sort() and limit()."""

    def __init__(self, docs):
        super().__init__(docs)

    def sort(self, key, direction=1):
        return MockCursor(sorted(self, key=lambda d: d.get(key, ""), reverse=(direction == -1)))

    def limit(self, n):
        return MockCursor(self[:n])


class MockCollection:
    """In-memory mock of a MongoDB collection."""

    def __init__(self):
        self._docs = []

    def _matches(self, doc, query):
        import re
        if not query:
            return True

        if "$or" in query:
            return any(self._matches(doc, branch) for branch in query["$or"])

        if "$and" in query:
            return all(self._matches(doc, branch) for branch in query["$and"])

        for k, v in query.items():
            if k in ("$or", "$and"):
                continue

            if isinstance(v, dict):
                if "$regex" in v:
                    flags = re.IGNORECASE if v.get("$options") == "i" else 0
                    val = str(doc.get(k, ""))
                    if not re.search(v["$regex"], val, flags):
                        return False
                elif "$exists" in v:
                    exists = k in doc
                    if exists != v["$exists"]:
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    def find(self, query=None, projection=None):
        results = [dict(doc) for doc in self._docs if self._matches(doc, query or {})]
        return MockCursor(results)

    def find_one(self, query=None, projection=None):
        for doc in self._docs:
            if self._matches(doc, query or {}):
                return dict(doc)
        return None

    def insert_one(self, doc):
        self._docs.append(dict(doc))
        return MagicMock(inserted_id="mock_id")

    def insert_many(self, docs):
        for d in docs:
            self._docs.append(dict(d))

    def update_one(self, query, update, upsert=False):
        for i, doc in enumerate(self._docs):
            if self._matches(doc, query):
                updated = dict(doc)
                if "$set" in update:
                    updated.update(update["$set"])
                self._docs[i] = updated
                return MagicMock(modified_count=1)

        if upsert:
            new_doc = dict(query)
            if "$set" in update:
                new_doc.update(update["$set"])
            self._docs.append(new_doc)
            return MagicMock(modified_count=1)

        return MagicMock(modified_count=0)

    def delete_one(self, query):
        for i, doc in enumerate(self._docs):
            if self._matches(doc, query):
                self._docs.pop(i)
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)

    def delete_many(self, query):
        initial = len(self._docs)
        self._docs = [doc for doc in self._docs if not self._matches(doc, query)]
        return MagicMock(deleted_count=initial - len(self._docs))


class MockDB:
    """Mock database with named collections."""

    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection()
        return self._collections[name]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    db = MockDB()
    with patch("db.get_db", return_value=db), \
         patch("db.get_client") as mock_client:
        mock_client.return_value.admin.command = MagicMock(return_value=True)
        yield db


@pytest.fixture
def app(mock_db):
    """Create a test application instance."""
    with patch("db.init_db"):
        from app import create_app
        application = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-123",
            "MONGO_URI": "mongodb://localhost:27017",
            "MONGO_DB_NAME": "test_db",
        })
        yield application


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Tests: Health Check
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_check(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


# ---------------------------------------------------------------------------
# Tests: Authentication
# ---------------------------------------------------------------------------

class TestAuth:
    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "name": "Jane Doe",
            "username": "janedoe",
            "email": "jane@example.com",
            "password": "Password123!",
            "confirmPassword": "Password123!",
            "role": "Product Manager",
        })
        data = res.get_json()
        assert data["success"] is True
        assert data["data"]["user"]["email"] == "jane@example.com"
        assert data["data"]["user"]["username"] == "janedoe"

    def test_register_invalid_email(self, client):
        res = client.post("/api/auth/register", json={
            "name": "Jane Doe",
            "username": "janedoe",
            "email": "invalid-email",
            "password": "Password123!",
            "confirmPassword": "Password123!",
        })
        data = res.get_json()
        assert data["success"] is False
        assert "email" in data["data"]["errors"]

    def test_login_and_logout(self, client):
        # Register user
        client.post("/api/auth/register", json={
            "name": "Alex",
            "username": "alex",
            "email": "alex@example.com",
            "password": "Password123!",
            "confirmPassword": "Password123!",
        })

        # Successful login
        login_res = client.post("/api/auth/login", json={
            "email": "alex@example.com",
            "password": "Password123!",
        })
        login_data = login_res.get_json()
        assert login_data["success"] is True
        assert login_data["data"]["user"]["email"] == "alex@example.com"

        # Logout
        logout_res = client.post("/api/auth/logout")
        assert logout_res.get_json()["success"] is True


# ---------------------------------------------------------------------------
# Tests: Product Retrieval and Search
# ---------------------------------------------------------------------------

class TestProducts:
    def test_create_and_get_product(self, client):
        res = client.post("/api/products", json={
            "name": "Analytics Dashboard",
            "description": "Real-time metrics viewer",
            "category": "Reporting",
            "status": "Active",
            "tags": ["analytics", "charts"],
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        prod_id = data["data"]["id"]

        # Retrieve by ID
        get_res = client.get(f"/api/products/{prod_id}")
        assert get_res.status_code == 200
        assert get_res.get_json()["data"]["name"] == "Analytics Dashboard"

    def test_missing_product_returns_404(self, client):
        res = client.get("/api/products/non-existent-id")
        assert res.status_code == 404
        data = res.get_json()
        assert data["success"] is False
        assert "not found" in data["message"].lower()

    def test_search_products(self, client):
        client.post("/api/products", json={
            "name": "Payment Gateway",
            "description": "Stripe and PayPal integration",
            "category": "Billing",
        })
        client.post("/api/products", json={
            "name": "User Onboarding",
            "description": "Guided walkthrough widget",
            "category": "UX",
        })

        # Search via /api/products/search
        search_res = client.get("/api/products/search?q=payment")
        search_data = search_res.get_json()
        assert search_data["success"] is True
        assert len(search_data["data"]) == 1
        assert search_data["data"][0]["name"] == "Payment Gateway"

        # Search via /api/products?q=...
        list_search_res = client.get("/api/products?q=onboarding")
        list_data = list_search_res.get_json()
        assert list_data["success"] is True
        assert len(list_data["data"]) == 1
        assert list_data["data"][0]["name"] == "User Onboarding"


# ---------------------------------------------------------------------------
# Tests: Feedback Endpoints
# ---------------------------------------------------------------------------

class TestFeedback:
    def _login(self, client):
        client.post("/api/auth/register", json={
            "name": "FB User",
            "username": "fbuser",
            "email": "fb@test.com",
            "password": "Password123!",
            "confirmPassword": "Password123!",
        })
        client.post("/api/auth/login", json={
            "email": "fb@test.com",
            "password": "Password123!",
        })

    def test_create_and_list_feedback(self, client):
        self._login(client)
        create_res = client.post("/api/feedback", json={
            "title": "Slow export",
            "message": "CSV export takes over 2 minutes",
            "sentiment": "negative",
            "customer": "Acme Corp",
        })
        assert create_res.get_json()["success"] is True

        list_res = client.get("/api/feedback")
        items = list_res.get_json()["data"]
        assert len(items) == 1
        assert items[0]["title"] == "Slow export"

    def test_feedback_validation(self, client):
        self._login(client)
        res = client.post("/api/feedback", json={"title": ""})
        assert res.get_json()["success"] is False


# ---------------------------------------------------------------------------
# Tests: State Endpoint
# ---------------------------------------------------------------------------

class TestState:
    def test_state_requires_auth(self, client):
        res = client.get("/api/state")
        assert res.status_code == 401
        assert res.get_json()["success"] is False

    def test_state_loads_data_when_logged_in(self, client):
        client.post("/api/auth/register", json={
            "name": "State Tester",
            "username": "statetester",
            "email": "state@test.com",
            "password": "Password123!",
            "confirmPassword": "Password123!",
        })
        client.post("/api/auth/login", json={
            "email": "state@test.com",
            "password": "Password123!",
        })

        res = client.get("/api/state")
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert "feedback" in data
        assert "features" in data
        assert "themes" in data
        assert "workspaces" in data
