"""MongoDB connection module for the FastAPI application."""

from pymongo import MongoClient
from pymongo.errors import PyMongoError

_client = None
_db = None


def init_db(mongo_uri: str, db_name: str):
    """Initialize the MongoDB connection."""
    global _client, _db

    if not mongo_uri:
        raise ValueError("MONGO_URI is not configured.")

    if not db_name:
        raise ValueError("MONGO_DB_NAME is not configured.")

    close_client()

    _client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
    )
    _db = _client[db_name]

    try:
        _client.admin.command("ping")
        print(f"Connected to MongoDB: {db_name}")

    except PyMongoError:
        close_client()
        print("MongoDB connection failed.")
        raise


def get_db():
    """Return the initialized MongoDB database."""
    if _db is None:
        raise RuntimeError(
            "Database is not initialized. Call init_db() first."
        )

    return _db


def get_client():
    """Return the MongoDB client."""
    return _client


def close_client():
    """Close the MongoDB connection and reset its references."""
    global _client, _db

    if _client is not None:
        _client.close()

    _client = None
    _db = None