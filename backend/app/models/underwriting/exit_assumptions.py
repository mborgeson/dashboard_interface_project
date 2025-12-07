"""
ExitAssumptions - Exit timing and disposition assumptions (3 fields).

Maps to: 'Assumptions (Summary)'!$D$23, $D$30, $D$31 range
Cell Reference Category: "Exit Assumptions"
"""
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.underwriting_model import UnderwritingModel


class ExitAssumptions(Base, TimestampMixin, SourceTrackingMixin):
    """
    Exit assumptions for property disposition.

    Contains: Exit timing, cap rate assumptions, and transaction costs.
    """

    __tablename__ = "uw_exit_assumptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Parent relationship
    underwriting_model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("underwriting_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    underwriting_model: Mapped["UnderwritingModel"] = relationship(
        "UnderwritingModel",
        back_populates="exit_assumptions",
    )

    # Exit Timing (D23)
    exit_period_months: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="EXIT_PERIOD_MONTHS - 'Assumptions (Summary)'!$D$23"
    )

    # Exit Cap Rate (D30)
    exit_cap_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="EXIT_CAP_RATE - 'Assumptions (Summary)'!$D$30"
    )

    # Transaction Costs (D31)
    sales_transaction_costs: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="SALES_TRANSACTION_COSTS - 'Assumptions (Summary)'!$D$31"
    )

    def __repr__(self) -> str:
        return f"<ExitAssumptions {self.exit_period_months} months @ {self.exit_cap_rate} cap>"
