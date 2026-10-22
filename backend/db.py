"""Database connection module.

Keeps MongoDB connection logic separate from API routes.
Provides a ``get_db()`` helper that returns the database handle, and
an ``init_db(app)`` function called once at startup.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

_client = None
_db = None


def init_db(app):
    """Initialise the MongoDB client using app configuration.

    Called once from the application factory.  Stores the client and db handle
    in module-level variables so route modules can import ``get_db()``.
    """
    global _client, _db
    mongo_uri = app.config["MONGO_URI"]
    db_name = app.config["MONGO_DB_NAME"]

    _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    _db = _client[db_name]

    # Verify connectivity at startup so mis-configuration is caught early.
    try:
        _client.admin.command("ping")
        print(f"  * Connected to MongoDB: {db_name}")
    except ConnectionFailure as exc:
        print(f"  ! MongoDB connection failed: {exc}")
        print("    The server will start, but database operations will fail.")
        print(f"    Check that MONGO_URI ({mongo_uri}) is correct and the server is running.")


def get_db():
    """Return the database handle.  Raises RuntimeError if init_db was not called."""
    if _db is None:
        raise RuntimeError(
            "Database not initialised. Call init_db(app) before using get_db()."
        )
    return _db


def get_client():
    """Return the raw MongoClient (useful for health checks)."""
    return _client
