"""
SQLAlchemy declarative base and model imports.
Import all models here for Alembic migrations to detect them.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming convention for constraints (helps with migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    metadata = metadata


# Import all models here for Alembic to detect them  # noqa: E402
# noqa comments prevent unused import warnings
from app.models.deal import Deal  # noqa: E402, F401

# Extraction Models (SharePoint UW Model Integration)
from app.models.extraction import (  # noqa: E402, F401
    ExtractedValue,
    ExtractionRun,
)

# File Monitoring Models
from app.models.file_monitor import (  # noqa: E402, F401
    FileChangeLog,
    MonitoredFile,
)
from app.models.property import Property  # noqa: E402, F401

# Underwriting Models
from app.models.underwriting import (  # noqa: E402, F401
    AnnualCashflow,
    BudgetAssumptions,
    EquityReturns,
    ExitAssumptions,
    FinancingAssumptions,
    GeneralAssumptions,
    NOIAssumptions,
    PropertyReturns,
    RentComp,
    SalesComp,
    UnderwritingModel,
    UnitMix,
)
from app.models.user import User  # noqa: E402, F401

# Wave 1: Transaction and Document Models
from app.models.transaction import Transaction  # noqa: E402, F401
from app.models.document import Document  # noqa: E402, F401
