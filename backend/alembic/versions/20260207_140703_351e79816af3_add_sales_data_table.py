"""add sales_data table

Revision ID: 351e79816af3
Revises: c3d4e5f6a7b8
Create Date: 2026-02-07 14:07:03.009076

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "351e79816af3"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        "sales_data",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("market", sa.String(length=100), nullable=True),
        sa.Column("property_name", sa.String(length=500), nullable=True),
        sa.Column("property_id", sa.String(length=100), nullable=True),
        sa.Column("comp_id", sa.String(length=100), nullable=True),
        sa.Column("property_address", sa.String(length=500), nullable=True),
        sa.Column("property_city", sa.String(length=200), nullable=True),
        sa.Column("property_state", sa.String(length=10), nullable=True),
        sa.Column("property_zip_code", sa.String(length=20), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("property_county", sa.String(length=200), nullable=True),
        sa.Column("submarket_cluster", sa.String(length=200), nullable=True),
        sa.Column("submarket_name", sa.String(length=200), nullable=True),
        sa.Column("parcel_number_1_min", sa.String(length=200), nullable=True),
        sa.Column("parcel_number_2_max", sa.String(length=200), nullable=True),
        sa.Column("land_area_ac", sa.Float(), nullable=True),
        sa.Column("land_area_sf", sa.Float(), nullable=True),
        sa.Column("location_type", sa.String(length=200), nullable=True),
        sa.Column("star_rating", sa.String(length=50), nullable=True),
        sa.Column("market_column", sa.String(length=200), nullable=True),
        sa.Column("submarket_code", sa.String(length=50), nullable=True),
        sa.Column("building_class", sa.String(length=10), nullable=True),
        sa.Column("affordable_type", sa.String(length=200), nullable=True),
        sa.Column("buyer_true_company", sa.String(length=500), nullable=True),
        sa.Column("buyer_true_contact", sa.String(length=500), nullable=True),
        sa.Column("acquisition_fund_name", sa.String(length=500), nullable=True),
        sa.Column("buyer_contact", sa.String(length=500), nullable=True),
        sa.Column("seller_true_company", sa.String(length=500), nullable=True),
        sa.Column("disposition_fund_name", sa.String(length=500), nullable=True),
        sa.Column("listing_broker_company", sa.String(length=500), nullable=True),
        sa.Column(
            "listing_broker_agent_first_name", sa.String(length=200), nullable=True
        ),
        sa.Column(
            "listing_broker_agent_last_name", sa.String(length=200), nullable=True
        ),
        sa.Column("buyers_broker_company", sa.String(length=500), nullable=True),
        sa.Column(
            "buyers_broker_agent_first_name", sa.String(length=200), nullable=True
        ),
        sa.Column(
            "buyers_broker_agent_last_name", sa.String(length=200), nullable=True
        ),
        sa.Column("construction_begin", sa.String(length=100), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("property_type", sa.String(length=200), nullable=True),
        sa.Column("building_sf", sa.Float(), nullable=True),
        sa.Column("building_materials", sa.String(length=500), nullable=True),
        sa.Column("building_condition", sa.String(length=200), nullable=True),
        sa.Column("construction_material", sa.String(length=500), nullable=True),
        sa.Column("roof_type", sa.String(length=200), nullable=True),
        sa.Column("ceiling_height", sa.String(length=100), nullable=True),
        sa.Column("secondary_type", sa.String(length=200), nullable=True),
        sa.Column("number_of_floors", sa.Integer(), nullable=True),
        sa.Column("number_of_units", sa.Integer(), nullable=True),
        sa.Column("number_of_parking_spaces", sa.Integer(), nullable=True),
        sa.Column("number_of_tenants", sa.Integer(), nullable=True),
        sa.Column("land_sf_gross", sa.Float(), nullable=True),
        sa.Column("land_sf_net", sa.Float(), nullable=True),
        sa.Column("flood_risk", sa.String(length=100), nullable=True),
        sa.Column("flood_zone", sa.String(length=100), nullable=True),
        sa.Column("avg_unit_sf", sa.Float(), nullable=True),
        sa.Column("sale_date", sa.Date(), nullable=True),
        sa.Column("sale_price", sa.Float(), nullable=True),
        sa.Column("price_per_unit", sa.Float(), nullable=True),
        sa.Column("price_per_sf_net", sa.Float(), nullable=True),
        sa.Column("price_per_sf", sa.Float(), nullable=True),
        sa.Column("hold_period", sa.String(length=200), nullable=True),
        sa.Column("document_number", sa.String(length=200), nullable=True),
        sa.Column("down_payment", sa.Float(), nullable=True),
        sa.Column("sale_type", sa.String(length=200), nullable=True),
        sa.Column("sale_condition", sa.String(length=200), nullable=True),
        sa.Column("sale_price_comment", sa.Text(), nullable=True),
        sa.Column("sale_status", sa.String(length=100), nullable=True),
        sa.Column("sale_category", sa.String(length=100), nullable=True),
        sa.Column("actual_cap_rate", sa.Float(), nullable=True),
        sa.Column("units_per_acre", sa.Float(), nullable=True),
        sa.Column("zoning", sa.String(length=200), nullable=True),
        sa.Column("number_of_beds", sa.Integer(), nullable=True),
        sa.Column("gross_income", sa.Float(), nullable=True),
        sa.Column("grm", sa.Float(), nullable=True),
        sa.Column("gim", sa.Float(), nullable=True),
        sa.Column("building_operating_expenses", sa.Text(), nullable=True),
        sa.Column("total_expense_amount", sa.Float(), nullable=True),
        sa.Column("vacancy", sa.Float(), nullable=True),
        sa.Column("assessed_improved", sa.Float(), nullable=True),
        sa.Column("assessed_land", sa.Float(), nullable=True),
        sa.Column("assessed_value", sa.Float(), nullable=True),
        sa.Column("assessed_year", sa.Integer(), nullable=True),
        sa.Column("number_of_studios_units", sa.Integer(), nullable=True),
        sa.Column("number_of_1_bedrooms_units", sa.Integer(), nullable=True),
        sa.Column("number_of_2_bedrooms_units", sa.Integer(), nullable=True),
        sa.Column("number_of_3_bedrooms_units", sa.Integer(), nullable=True),
        sa.Column("number_of_other_bedrooms_units", sa.Integer(), nullable=True),
        sa.Column("first_trust_deed_terms", sa.String(length=500), nullable=True),
        sa.Column("first_trust_deed_balance", sa.Float(), nullable=True),
        sa.Column("first_trust_deed_lender", sa.String(length=500), nullable=True),
        sa.Column("first_trust_deed_payment", sa.Float(), nullable=True),
        sa.Column("second_trust_deed_balance", sa.Float(), nullable=True),
        sa.Column("second_trust_deed_lender", sa.String(length=500), nullable=True),
        sa.Column("second_trust_deed_payment", sa.Float(), nullable=True),
        sa.Column("second_trust_deed_terms", sa.String(length=500), nullable=True),
        sa.Column("title_company", sa.String(length=500), nullable=True),
        sa.Column("amenities", sa.Text(), nullable=True),
        sa.Column("sewer", sa.String(length=200), nullable=True),
        sa.Column("transaction_notes", sa.Text(), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column("research_status", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales_data")),
        sa.UniqueConstraint(
            "comp_id", "source_file", name="uq_sales_data_comp_id_source"
        ),
    )
    op.create_index("ix_sales_data_comp_id", "sales_data", ["comp_id"], unique=False)
    op.create_index("ix_sales_data_market", "sales_data", ["market"], unique=False)
    op.create_index(
        "ix_sales_data_sale_date", "sales_data", ["sale_date"], unique=False
    )
    op.create_index(
        "ix_sales_data_submarket", "sales_data", ["submarket_name"], unique=False
    )
    op.create_index(
        "ix_sales_data_buyer", "sales_data", ["buyer_true_company"], unique=False
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index("ix_sales_data_buyer", table_name="sales_data")
    op.drop_index("ix_sales_data_submarket", table_name="sales_data")
    op.drop_index("ix_sales_data_sale_date", table_name="sales_data")
    op.drop_index("ix_sales_data_market", table_name="sales_data")
    op.drop_index("ix_sales_data_comp_id", table_name="sales_data")
    op.drop_table("sales_data")
