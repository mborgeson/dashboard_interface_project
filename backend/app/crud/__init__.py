"""
CRUD (Create, Read, Update, Delete) operations for database models.
"""

from app.crud.base import CRUDBase
from app.crud.crud_activity import deal_activity, property_activity, watchlist
from app.crud.crud_deal import deal
from app.crud.crud_document import document
from app.crud.crud_property import property
from app.crud.crud_report_template import (
    distribution_schedule,
    queued_report,
    report_template,
)
from app.crud.crud_transaction import transaction
from app.crud.crud_user import user

__all__ = [
    "CRUDBase",
    "deal",
    "document",
    "property",
    "transaction",
    "user",
    "report_template",
    "queued_report",
    "distribution_schedule",
    # Activity CRUD
    "property_activity",
    "deal_activity",
    "watchlist",
]
