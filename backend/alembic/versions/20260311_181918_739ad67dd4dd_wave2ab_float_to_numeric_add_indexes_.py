"""wave2ab: Float to Numeric, add indexes and ondelete policies

Revision ID: 739ad67dd4dd
Revises: c5d6e7f8a9b0
Create Date: 2026-03-11 18:19:18.053493

Changes:
  D-01: SalesData Float→Numeric for financial columns
  D-02: ConstructionProject Float→Numeric for financial columns
  D-03: Property cap_rate Numeric(5,3)→Numeric(6,3)
  D-04: Add indexes on construction FK source_log_id columns
  D-05: Add indexes on underwriting user FK columns
  D-06: Add ondelete="SET NULL" to FK definitions
  D-07: Add index on sales_data.property_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '739ad67dd4dd'
down_revision: Union[str, None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # ── D-01: SalesData Float→Numeric (financial columns) ──────────────
    # Dollar amounts → Numeric(15,2)
    op.alter_column('sales_data', 'sale_price',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'price_per_unit',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'price_per_sf_net',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'price_per_sf',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'down_payment',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'gross_income',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'total_expense_amount',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'assessed_improved',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'assessed_land',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'assessed_value',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'first_trust_deed_balance',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'first_trust_deed_payment',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'second_trust_deed_balance',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('sales_data', 'second_trust_deed_payment',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    # Rates/ratios → Numeric(8,4)
    op.alter_column('sales_data', 'actual_cap_rate',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('sales_data', 'grm',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('sales_data', 'gim',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('sales_data', 'vacancy',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)

    # ── D-07: Add index on sales_data.property_id ──────────────────────
    op.create_index(op.f('ix_sales_data_property_id'), 'sales_data', ['property_id'], unique=False)

    # ── D-02: ConstructionProject Float→Numeric (financial columns) ────
    # Dollar amounts → Numeric(15,2)
    op.alter_column('construction_projects', 'for_sale_price',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'for_sale_price_per_unit',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'for_sale_price_per_sf',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'last_sale_price',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'origination_amount',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'taxes_total',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_asking_per_unit',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_asking_per_sf',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_effective_per_unit',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_effective_per_sf',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=15, scale=2),
               existing_nullable=True)
    # Rates/ratios → Numeric(8,4)
    op.alter_column('construction_projects', 'cap_rate',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('construction_projects', 'interest_rate',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_concessions_pct',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('construction_projects', 'vacancy_pct',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_leased',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('construction_projects', 'taxes_per_sf',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('construction_projects', 'parking_ratio',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    op.alter_column('construction_projects', 'parking_spaces_per_unit',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=8, scale=4),
               existing_nullable=True)
    # Percentages (unit mix) → Numeric(5,2)
    op.alter_column('construction_projects', 'pct_studio',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=5, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_1bed',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=5, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_2bed',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=5, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_3bed',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=5, scale=2),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_4bed',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=5, scale=2),
               existing_nullable=True)

    # ── D-03: Property cap_rate precision Numeric(5,3)→Numeric(6,3) ────
    op.alter_column('properties', 'cap_rate',
               existing_type=sa.NUMERIC(precision=5, scale=3),
               type_=sa.Numeric(precision=6, scale=3),
               existing_nullable=True)

    # ── D-04: Add indexes on construction FK source_log_id columns ─────
    op.create_index(op.f('ix_construction_permit_data_source_log_id'), 'construction_permit_data', ['source_log_id'], unique=False)
    op.create_index(op.f('ix_construction_employment_data_source_log_id'), 'construction_employment_data', ['source_log_id'], unique=False)
    op.create_index(op.f('ix_construction_brokerage_metrics_source_log_id'), 'construction_brokerage_metrics', ['source_log_id'], unique=False)

    # ── D-05: Add indexes on underwriting user FK columns ──────────────
    op.create_index(op.f('ix_underwriting_models_created_by_user_id'), 'underwriting_models', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_underwriting_models_approved_by_user_id'), 'underwriting_models', ['approved_by_user_id'], unique=False)

    # ── D-06: Add ondelete="SET NULL" to FK definitions ────────────────
    # Construction tables
    op.drop_constraint(op.f('fk_construction_permit_data_source_log_id_construction__f6c4'), 'construction_permit_data', type_='foreignkey')
    op.create_foreign_key(op.f('fk_construction_permit_data_source_log_id_construction_source_logs'), 'construction_permit_data', 'construction_source_logs', ['source_log_id'], ['id'], ondelete='SET NULL')

    op.drop_constraint(op.f('fk_construction_employment_data_source_log_id_construct_7685'), 'construction_employment_data', type_='foreignkey')
    op.create_foreign_key(op.f('fk_construction_employment_data_source_log_id_construction_source_logs'), 'construction_employment_data', 'construction_source_logs', ['source_log_id'], ['id'], ondelete='SET NULL')

    op.drop_constraint(op.f('fk_construction_brokerage_metrics_source_log_id_constru_0814'), 'construction_brokerage_metrics', type_='foreignkey')
    op.create_foreign_key(op.f('fk_construction_brokerage_metrics_source_log_id_construction_source_logs'), 'construction_brokerage_metrics', 'construction_source_logs', ['source_log_id'], ['id'], ondelete='SET NULL')

    # Underwriting tables
    op.drop_constraint(op.f('fk_underwriting_models_created_by_user_id_users'), 'underwriting_models', type_='foreignkey')
    op.create_foreign_key(op.f('fk_underwriting_models_created_by_user_id_users'), 'underwriting_models', 'users', ['created_by_user_id'], ['id'], ondelete='SET NULL')

    op.drop_constraint(op.f('fk_underwriting_models_approved_by_user_id_users'), 'underwriting_models', type_='foreignkey')
    op.create_foreign_key(op.f('fk_underwriting_models_approved_by_user_id_users'), 'underwriting_models', 'users', ['approved_by_user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade database schema."""
    # ── Undo D-06: Remove ondelete from FKs ────────────────────────────
    op.drop_constraint(op.f('fk_underwriting_models_approved_by_user_id_users'), 'underwriting_models', type_='foreignkey')
    op.create_foreign_key(op.f('fk_underwriting_models_approved_by_user_id_users'), 'underwriting_models', 'users', ['approved_by_user_id'], ['id'])

    op.drop_constraint(op.f('fk_underwriting_models_created_by_user_id_users'), 'underwriting_models', type_='foreignkey')
    op.create_foreign_key(op.f('fk_underwriting_models_created_by_user_id_users'), 'underwriting_models', 'users', ['created_by_user_id'], ['id'])

    op.drop_constraint(op.f('fk_construction_brokerage_metrics_source_log_id_construction_source_logs'), 'construction_brokerage_metrics', type_='foreignkey')
    op.create_foreign_key(op.f('fk_construction_brokerage_metrics_source_log_id_constru_0814'), 'construction_brokerage_metrics', 'construction_source_logs', ['source_log_id'], ['id'])

    op.drop_constraint(op.f('fk_construction_employment_data_source_log_id_construction_source_logs'), 'construction_employment_data', type_='foreignkey')
    op.create_foreign_key(op.f('fk_construction_employment_data_source_log_id_construct_7685'), 'construction_employment_data', 'construction_source_logs', ['source_log_id'], ['id'])

    op.drop_constraint(op.f('fk_construction_permit_data_source_log_id_construction_source_logs'), 'construction_permit_data', type_='foreignkey')
    op.create_foreign_key(op.f('fk_construction_permit_data_source_log_id_construction__f6c4'), 'construction_permit_data', 'construction_source_logs', ['source_log_id'], ['id'])

    # ── Undo D-05: Drop underwriting user FK indexes ───────────────────
    op.drop_index(op.f('ix_underwriting_models_approved_by_user_id'), table_name='underwriting_models')
    op.drop_index(op.f('ix_underwriting_models_created_by_user_id'), table_name='underwriting_models')

    # ── Undo D-04: Drop construction FK indexes ────────────────────────
    op.drop_index(op.f('ix_construction_brokerage_metrics_source_log_id'), table_name='construction_brokerage_metrics')
    op.drop_index(op.f('ix_construction_employment_data_source_log_id'), table_name='construction_employment_data')
    op.drop_index(op.f('ix_construction_permit_data_source_log_id'), table_name='construction_permit_data')

    # ── Undo D-03: Property cap_rate Numeric(6,3)→Numeric(5,3) ────────
    op.alter_column('properties', 'cap_rate',
               existing_type=sa.Numeric(precision=6, scale=3),
               type_=sa.NUMERIC(precision=5, scale=3),
               existing_nullable=True)

    # ── Undo D-02: ConstructionProject Numeric→Float ───────────────────
    op.alter_column('construction_projects', 'pct_4bed',
               existing_type=sa.Numeric(precision=5, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_3bed',
               existing_type=sa.Numeric(precision=5, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_2bed',
               existing_type=sa.Numeric(precision=5, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_1bed',
               existing_type=sa.Numeric(precision=5, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_studio',
               existing_type=sa.Numeric(precision=5, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'parking_spaces_per_unit',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'parking_ratio',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'taxes_per_sf',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'pct_leased',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'vacancy_pct',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_concessions_pct',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'interest_rate',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'cap_rate',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_effective_per_sf',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_effective_per_unit',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_asking_per_sf',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'avg_asking_per_unit',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'taxes_total',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'origination_amount',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'last_sale_price',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'for_sale_price_per_sf',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'for_sale_price_per_unit',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('construction_projects', 'for_sale_price',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)

    # ── Undo D-07: Drop sales_data.property_id index ──────────────────
    op.drop_index(op.f('ix_sales_data_property_id'), table_name='sales_data')

    # ── Undo D-01: SalesData Numeric→Float ─────────────────────────────
    op.alter_column('sales_data', 'vacancy',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'gim',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'grm',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'actual_cap_rate',
               existing_type=sa.Numeric(precision=8, scale=4),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'second_trust_deed_payment',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'second_trust_deed_balance',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'first_trust_deed_payment',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'first_trust_deed_balance',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'assessed_value',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'assessed_land',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'assessed_improved',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'total_expense_amount',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'gross_income',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'down_payment',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'price_per_sf',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'price_per_sf_net',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'price_per_unit',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.alter_column('sales_data', 'sale_price',
               existing_type=sa.Numeric(precision=15, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
