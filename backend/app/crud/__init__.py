"""
CRUD (Create, Read, Update, Delete) operations for database models.
"""

from app.crud.base import CRUDBase
from app.crud.crud_deal import deal
from app.crud.crud_property import property
from app.crud.crud_user import user

__all__ = ["CRUDBase", "deal", "property", "user"]
