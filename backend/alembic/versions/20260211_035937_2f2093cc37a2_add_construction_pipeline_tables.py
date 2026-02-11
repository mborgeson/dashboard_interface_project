"""add construction pipeline tables

Revision ID: 2f2093cc37a2
Revises: b1e88c02306b
Create Date: 2026-02-11 03:59:37.505372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f2093cc37a2'
down_revision: Union[str, None] = 'b1e88c02306b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table('construction_projects',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('costar_property_id', sa.String(length=100), nullable=True),
    sa.Column('property_type', sa.String(length=200), nullable=True),
    sa.Column('project_name', sa.String(length=500), nullable=True),
    sa.Column('project_address', sa.String(length=500), nullable=True),
    sa.Column('city', sa.String(length=200), nullable=True),
    sa.Column('state', sa.String(length=10), nullable=True),
    sa.Column('zip_code', sa.String(length=20), nullable=True),
    sa.Column('county', sa.String(length=200), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('market_name', sa.String(length=200), nullable=True),
    sa.Column('submarket_name', sa.String(length=200), nullable=True),
    sa.Column('submarket_cluster', sa.String(length=200), nullable=True),
    sa.Column('pipeline_status', sa.String(length=50), nullable=False),
    sa.Column('constr_status_raw', sa.String(length=100), nullable=True),
    sa.Column('building_status_raw', sa.String(length=100), nullable=True),
    sa.Column('primary_classification', sa.String(length=50), nullable=False),
    sa.Column('secondary_tags', sa.String(length=500), nullable=True),
    sa.Column('number_of_units', sa.Integer(), nullable=True),
    sa.Column('building_sf', sa.Float(), nullable=True),
    sa.Column('number_of_stories', sa.Integer(), nullable=True),
    sa.Column('total_buildings', sa.Integer(), nullable=True),
    sa.Column('star_rating', sa.String(length=50), nullable=True),
    sa.Column('building_class', sa.String(length=10), nullable=True),
    sa.Column('style', sa.String(length=100), nullable=True),
    sa.Column('secondary_type', sa.String(length=200), nullable=True),
    sa.Column('construction_material', sa.String(length=500), nullable=True),
    sa.Column('is_condo', sa.Boolean(), nullable=False),
    sa.Column('number_of_elevators', sa.Integer(), nullable=True),
    sa.Column('ceiling_height', sa.String(length=100), nullable=True),
    sa.Column('sprinklers', sa.String(length=100), nullable=True),
    sa.Column('pct_studio', sa.Float(), nullable=True),
    sa.Column('pct_1bed', sa.Float(), nullable=True),
    sa.Column('pct_2bed', sa.Float(), nullable=True),
    sa.Column('pct_3bed', sa.Float(), nullable=True),
    sa.Column('pct_4bed', sa.Float(), nullable=True),
    sa.Column('num_studios', sa.Integer(), nullable=True),
    sa.Column('num_1bed', sa.Integer(), nullable=True),
    sa.Column('num_2bed', sa.Integer(), nullable=True),
    sa.Column('num_3bed', sa.Integer(), nullable=True),
    sa.Column('num_4bed', sa.Integer(), nullable=True),
    sa.Column('num_beds_total', sa.Integer(), nullable=True),
    sa.Column('avg_unit_sf', sa.Float(), nullable=True),
    sa.Column('rent_type', sa.String(length=100), nullable=True),
    sa.Column('affordable_type', sa.String(length=200), nullable=True),
    sa.Column('market_segment', sa.String(length=200), nullable=True),
    sa.Column('avg_asking_per_unit', sa.Float(), nullable=True),
    sa.Column('avg_asking_per_sf', sa.Float(), nullable=True),
    sa.Column('avg_effective_per_unit', sa.Float(), nullable=True),
    sa.Column('avg_effective_per_sf', sa.Float(), nullable=True),
    sa.Column('avg_concessions_pct', sa.Float(), nullable=True),
    sa.Column('vacancy_pct', sa.Float(), nullable=True),
    sa.Column('pct_leased', sa.Float(), nullable=True),
    sa.Column('pre_leasing', sa.String(length=200), nullable=True),
    sa.Column('construction_begin', sa.String(length=100), nullable=True),
    sa.Column('year_built', sa.Integer(), nullable=True),
    sa.Column('month_built', sa.Integer(), nullable=True),
    sa.Column('year_renovated', sa.Integer(), nullable=True),
    sa.Column('month_renovated', sa.Integer(), nullable=True),
    sa.Column('estimated_delivery_date', sa.Date(), nullable=True),
    sa.Column('developer_name', sa.String(length=500), nullable=True),
    sa.Column('owner_name', sa.String(length=500), nullable=True),
    sa.Column('owner_contact', sa.String(length=500), nullable=True),
    sa.Column('architect_name', sa.String(length=500), nullable=True),
    sa.Column('property_manager_name', sa.String(length=500), nullable=True),
    sa.Column('for_sale_price', sa.Float(), nullable=True),
    sa.Column('for_sale_status', sa.String(length=100), nullable=True),
    sa.Column('for_sale_price_per_unit', sa.Float(), nullable=True),
    sa.Column('for_sale_price_per_sf', sa.Float(), nullable=True),
    sa.Column('cap_rate', sa.Float(), nullable=True),
    sa.Column('last_sale_date', sa.Date(), nullable=True),
    sa.Column('last_sale_price', sa.Float(), nullable=True),
    sa.Column('days_on_market', sa.Integer(), nullable=True),
    sa.Column('land_area_ac', sa.Float(), nullable=True),
    sa.Column('land_area_sf', sa.Float(), nullable=True),
    sa.Column('zoning', sa.String(length=200), nullable=True),
    sa.Column('parking_spaces', sa.Integer(), nullable=True),
    sa.Column('parking_spaces_per_unit', sa.Float(), nullable=True),
    sa.Column('parking_ratio', sa.Float(), nullable=True),
    sa.Column('fema_flood_zone', sa.String(length=100), nullable=True),
    sa.Column('flood_risk_area', sa.String(length=200), nullable=True),
    sa.Column('in_sfha', sa.String(length=50), nullable=True),
    sa.Column('origination_amount', sa.Float(), nullable=True),
    sa.Column('origination_date', sa.String(length=100), nullable=True),
    sa.Column('originator', sa.String(length=500), nullable=True),
    sa.Column('interest_rate', sa.Float(), nullable=True),
    sa.Column('interest_rate_type', sa.String(length=100), nullable=True),
    sa.Column('loan_type', sa.String(length=200), nullable=True),
    sa.Column('maturity_date', sa.String(length=100), nullable=True),
    sa.Column('tax_year', sa.Integer(), nullable=True),
    sa.Column('taxes_per_sf', sa.Float(), nullable=True),
    sa.Column('taxes_total', sa.Float(), nullable=True),
    sa.Column('amenities', sa.Text(), nullable=True),
    sa.Column('features', sa.Text(), nullable=True),
    sa.Column('closest_transit_stop', sa.String(length=500), nullable=True),
    sa.Column('closest_transit_dist_mi', sa.Float(), nullable=True),
    sa.Column('university', sa.String(length=500), nullable=True),
    sa.Column('energy_star', sa.String(length=50), nullable=True),
    sa.Column('leed_certified', sa.String(length=50), nullable=True),
    sa.Column('source_type', sa.String(length=50), nullable=False),
    sa.Column('source_file', sa.String(length=500), nullable=True),
    sa.Column('imported_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_construction_projects')),
    sa.UniqueConstraint('costar_property_id', 'source_file', name='uq_construction_projects_costar_source')
    )
    op.create_index('ix_construction_projects_city', 'construction_projects', ['city'], unique=False)
    op.create_index('ix_construction_projects_classification', 'construction_projects', ['primary_classification'], unique=False)
    op.create_index('ix_construction_projects_status', 'construction_projects', ['pipeline_status'], unique=False)
    op.create_index('ix_construction_projects_submarket', 'construction_projects', ['submarket_cluster'], unique=False)

    op.create_table('construction_source_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('source_name', sa.String(length=100), nullable=False),
    sa.Column('fetch_type', sa.String(length=50), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('records_fetched', sa.Integer(), nullable=False),
    sa.Column('records_inserted', sa.Integer(), nullable=False),
    sa.Column('records_updated', sa.Integer(), nullable=False),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('api_response_code', sa.Integer(), nullable=True),
    sa.Column('data_period_start', sa.Date(), nullable=True),
    sa.Column('data_period_end', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_construction_source_logs'))
    )
    op.create_index('ix_construction_source_logs_fetched', 'construction_source_logs', ['fetched_at'], unique=False)
    op.create_index('ix_construction_source_logs_source', 'construction_source_logs', ['source_name'], unique=False)

    op.create_table('construction_brokerage_metrics',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('report_source', sa.String(length=200), nullable=False),
    sa.Column('report_quarter', sa.String(length=10), nullable=False),
    sa.Column('report_year', sa.Integer(), nullable=False),
    sa.Column('metric_name', sa.String(length=200), nullable=False),
    sa.Column('metric_value', sa.Float(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('entered_by', sa.String(length=200), nullable=True),
    sa.Column('source_log_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['source_log_id'], ['construction_source_logs.id'], name=op.f('fk_construction_brokerage_metrics_source_log_id_construction_source_logs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_construction_brokerage_metrics')),
    sa.UniqueConstraint('report_source', 'report_quarter', 'metric_name', name='uq_brokerage_source_quarter_metric')
    )

    op.create_table('construction_employment_data',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('series_id', sa.String(length=200), nullable=False),
    sa.Column('series_title', sa.String(length=500), nullable=True),
    sa.Column('period_date', sa.Date(), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('period_type', sa.String(length=20), nullable=False),
    sa.Column('source_log_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['source_log_id'], ['construction_source_logs.id'], name=op.f('fk_construction_employment_data_source_log_id_construction_source_logs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_construction_employment_data')),
    sa.UniqueConstraint('series_id', 'period_date', name='uq_employment_series_period')
    )
    op.create_index('ix_employment_series_date', 'construction_employment_data', ['series_id', 'period_date'], unique=False)

    op.create_table('construction_permit_data',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('series_id', sa.String(length=200), nullable=False),
    sa.Column('geography', sa.String(length=200), nullable=True),
    sa.Column('period_date', sa.Date(), nullable=False),
    sa.Column('period_type', sa.String(length=20), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('unit', sa.String(length=100), nullable=True),
    sa.Column('structure_type', sa.String(length=100), nullable=True),
    sa.Column('raw_json', sa.Text(), nullable=True),
    sa.Column('source_log_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['source_log_id'], ['construction_source_logs.id'], name=op.f('fk_construction_permit_data_source_log_id_construction_source_logs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_construction_permit_data')),
    sa.UniqueConstraint('source', 'series_id', 'period_date', name='uq_permit_data_source_series_period')
    )
    op.create_index('ix_construction_permit_period', 'construction_permit_data', ['period_date'], unique=False)
    op.create_index('ix_construction_permit_source_series', 'construction_permit_data', ['source', 'series_id'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index('ix_construction_permit_source_series', table_name='construction_permit_data')
    op.drop_index('ix_construction_permit_period', table_name='construction_permit_data')
    op.drop_table('construction_permit_data')
    op.drop_index('ix_employment_series_date', table_name='construction_employment_data')
    op.drop_table('construction_employment_data')
    op.drop_table('construction_brokerage_metrics')
    op.drop_index('ix_construction_source_logs_source', table_name='construction_source_logs')
    op.drop_index('ix_construction_source_logs_fetched', table_name='construction_source_logs')
    op.drop_table('construction_source_logs')
    op.drop_index('ix_construction_projects_submarket', table_name='construction_projects')
    op.drop_index('ix_construction_projects_status', table_name='construction_projects')
    op.drop_index('ix_construction_projects_classification', table_name='construction_projects')
    op.drop_index('ix_construction_projects_city', table_name='construction_projects')
    op.drop_table('construction_projects')
