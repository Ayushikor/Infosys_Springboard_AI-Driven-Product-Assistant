"""API tests for the FastAPI application using an in-memory mock database."""

import os
import re
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure the backend package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class MockCursor(list):
    """Mock MongoDB cursor supporting sort and limit."""

    def sort(self, key, direction=1):
        return MockCursor(
            sorted(
                self,
                key=lambda doc: str(doc.get(key, "")),
                reverse=(direction == -1),
            )
        )

    def limit(self, n):
        return MockCursor(self[:n])


class MockCollection:
    """Simple in-memory MongoDB collection."""

    def __init__(self):
        self._docs = []

    def _matches(self, doc, query):
        if not query:
            return True
        if "$or" in query:
            return any(self._matches(doc, branch) for branch in query["$or"])
        if "$and" in query:
            return all(self._matches(doc, branch) for branch in query["$and"])

        for key, value in query.items():
            if key in ("$or", "$and"):
                continue
            if isinstance(value, dict):
                if "$regex" in value:
                    flags = re.IGNORECASE if value.get("$options") == "i" else 0
                    if not re.search(value["$regex"], str(doc.get(key, "")), flags):
                        return False
                elif "$exists" in value:
                    if (key in doc) != value["$exists"]:
                        return False
                elif "$in" in value:
                    if doc.get(key) not in value["$in"]:
                        return False
                else:
                    return False
            elif doc.get(key) != value:
                return False
        return True

    def find(self, query=None, projection=None):
        return MockCursor([
            dict(doc) for doc in self._docs if self._matches(doc, query or {})
        ])

    def find_one(self, query=None, projection=None):
        for doc in self._docs:
            if self._matches(doc, query or {}):
                return dict(doc)
        return None

    def insert_one(self, doc):
        self._docs.append(dict(doc))
        return MagicMock(inserted_id="mock_id")

    def insert_many(self, docs):
        self._docs.extend(dict(doc) for doc in docs)
        return MagicMock(inserted_ids=["mock_id"] * len(docs))

    def update_one(self, query, update, upsert=False):
        for index, doc in enumerate(self._docs):
            if self._matches(doc, query):
                updated = dict(doc)
                if "$set" in update:
                    updated.update(update["$set"])
                self._docs[index] = updated
                return MagicMock(matched_count=1, modified_count=1)

        if upsert:
            new_doc = {
                key: value for key, value in query.items() if not key.startswith("$")
            }
            if "$set" in update:
                new_doc.update(update["$set"])
            self._docs.append(new_doc)
            return MagicMock(matched_count=0, modified_count=0, upserted_id="mock_id")

        return MagicMock(matched_count=0, modified_count=0)

    def delete_one(self, query):
        for index, doc in enumerate(self._docs):
            if self._matches(doc, query):
                self._docs.pop(index)
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)

    def delete_many(self, query):
        original_count = len(self._docs)
        self._docs = [doc for doc in self._docs if not self._matches(doc, query)]
        return MagicMock(deleted_count=original_count - len(self._docs))

    def count_documents(self, query=None):
        return sum(1 for doc in self._docs if self._matches(doc, query or {}))


class MockDB:
    """In-memory database with lazily created collections."""

    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection()
        return self._collections[name]


@pytest.fixture
def mock_db():
    database = MockDB()

    with (
        patch("db.get_db", return_value=database),
        patch("db.get_client") as mock_client,
    ):
        mock_client.return_value.admin.command = MagicMock(return_value={"ok": 1})
        yield database


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
            "ENSURE_INDEXES": False,
        })
        yield application


@pytest.fixture
def client(app):
    """Create a FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


def response_json(response):
    """Decode a JSON HTTP response."""
    return response.json()


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response_json(response)
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


class TestAuth:
    def test_register_success(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Jane Doe",
                "username": "janedoe",
                "email": "jane@example.com",
                "password": "Password123!",
                "confirmPassword": "Password123!",
                "role": "Product Manager",
            },
        )

        data = response_json(response)
        assert data["success"] is True
        assert data["data"]["user"]["email"] == "jane@example.com"
        assert data["data"]["user"]["username"] == "janedoe"

    def test_register_invalid_email(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Jane Doe",
                "username": "janedoe",
                "email": "invalid-email",
                "password": "Password123!",
                "confirmPassword": "Password123!",
            },
        )
        data = response_json(response)
        assert data["success"] is False
        assert "email" in data["data"]["errors"]

    def test_login_and_logout(self, client):
        client.post(
            "/api/auth/register",
            json={
                "name": "Alex",
                "username": "alex",
                "email": "alex@example.com",
                "password": "Password123!",
                "confirmPassword": "Password123!",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "alex@example.com",
                "password": "Password123!",
            },
        )
        login_data = response_json(login_response)
        assert login_data["success"] is True
        assert login_data["data"]["user"]["email"] == "alex@example.com"

        logout_response = client.post("/api/auth/logout")
        assert response_json(logout_response)["success"] is True


class TestProducts:
    def _login(self, client):
        """Register and log in a test user using a unique email."""
        import uuid

        unique_id = uuid.uuid4().hex[:10]
        email = f"product_{unique_id}@test.com"
        username = f"product_{unique_id}"

        register_response = client.post(
            "/api/auth/register",
            json={
                "name": "Product Tester",
                "username": username,
                "email": email,
                "password": "Password123!",
                "confirmPassword": "Password123!",
            },
        )

        assert register_response.status_code == 200, (
            f"Registration failed: {register_response.text}"
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Password123!",
            },
        )

        assert login_response.status_code == 200, (
            f"Login failed: {login_response.text}"
        )
        assert response_json(login_response)["success"] is True

    def test_create_and_get_product(self, client):
        self._login(client)

        response = client.post(
            "/api/products",
            json={
                "name": "Analytics Dashboard",
                "description": "Real-time metrics viewer",
                "category": "Reporting",
                "status": "Active",
                "tags": ["analytics", "charts"],
            },
        )

        assert response.status_code == 200
        data = response_json(response)
        assert data["success"] is True

        product_id = data["data"]["id"]

        get_response = client.get(f"/api/products/{product_id}")

        assert get_response.status_code == 200
        assert (
            response_json(get_response)["data"]["name"]
            == "Analytics Dashboard"
        )

    def test_missing_product_returns_404(self, client):
        self._login(client)

        response = client.get(
            "/api/products/non-existent-id"
        )

        assert response.status_code == 404

        data = response_json(response)
        assert data["success"] is False
        assert "not found" in data["message"].lower()

    def test_search_products(self, client):
        self._login(client)

        first_response = client.post(
            "/api/products",
            json={
                "name": "Payment Gateway",
                "description": "Stripe and PayPal integration",
                "category": "Billing",
            },
        )

        assert first_response.status_code == 200

        second_response = client.post(
            "/api/products",
            json={
                "name": "User Onboarding",
                "description": "Guided walkthrough widget",
                "category": "UX",
            },
        )

        assert second_response.status_code == 200

        search_response = client.get(
            "/api/products/search?q=payment"
        )

        assert search_response.status_code == 200

        search_data = response_json(search_response)
        assert search_data["success"] is True
        assert len(search_data["data"]) == 1
        assert search_data["data"][0]["name"] == "Payment Gateway"

        list_response = client.get(
            "/api/products?q=onboarding"
        )

        assert list_response.status_code == 200

        list_data = response_json(list_response)
        assert list_data["success"] is True
        assert len(list_data["data"]) == 1
        assert list_data["data"][0]["name"] == "User Onboarding"


class TestFeedback:
    def _login(self, client):
        client.post(
            "/api/auth/register",
            json={
                "name": "FB User",
                "username": "fbuser",
                "email": "fb@test.com",
                "password": "Password123!",
                "confirmPassword": "Password123!",
            },
        )
        client.post(
            "/api/auth/login",
            json={
                "email": "fb@test.com",
                "password": "Password123!",
            },
        )

    def test_create_and_list_feedback(self, client):
        self._login(client)
        create_response = client.post(
            "/api/feedback",
            json={
                "title": "Slow export",
                "message": "CSV export takes over 2 minutes",
                "sentiment": "negative",
                "customer": "Acme Corp",
            },
        )
        assert response_json(create_response)["success"] is True

        list_response = client.get("/api/feedback")
        items = response_json(list_response)["data"]
        assert len(items) == 1
        assert items[0]["title"] == "Slow export"

    def test_feedback_validation(self, client):
        self._login(client)
        response = client.post(
            "/api/feedback",
            json={"title": ""},
        )
        assert response_json(response)["success"] is False


class TestState:
    def test_state_requires_auth(self, client):
        response = client.get("/api/state")

        assert response.status_code == 401
        assert response_json(response)["success"] is False

    def test_state_loads_data_when_logged_in(self, client):
        client.post(
            "/api/auth/register",
            json={
                "name": "State Tester",
                "username": "statetester",
                "email": "state@test.com",
                "password": "Password123!",
                "confirmPassword": "Password123!",
            },
        )
        client.post(
            "/api/auth/login",
            json={
                "email": "state@test.com",
                "password": "Password123!",
            },
        )
        response = client.get("/api/state")
        assert response.status_code == 200
        data = response_json(response)["data"]
        assert "feedback" in data
        assert "features" in data
        assert "themes" in data
        assert "workspaces" in data