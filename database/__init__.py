"""Database definitions for the backend: schemas, validators and indexes.

This package does not open connections. The backend's ``db.get_db()`` remains
the single source of the MongoDB handle and passes it in where needed.
"""

from .indexes import INDEX_SPECS, create_indexes
from .schemas import VALIDATORS, validate

__all__ = ["INDEX_SPECS", "VALIDATORS", "create_indexes", "validate"]
