"""
MongoDB connection — shared collections used by FastAPI routes and chat.
"""

from pymongo import MongoClient
from src.config import settings

_mongo = MongoClient(settings.mongodb_uri)
_db = _mongo[settings.mongodb_db]

faqs_col = _db[settings.mongodb_collection]
registry_col = _db["document_registry"]
users_col = _db["users"]
