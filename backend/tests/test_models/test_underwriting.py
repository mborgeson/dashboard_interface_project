"""Tests for the 12 underwriting models in backend/app/models/underwriting/."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.underwriting import (
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
    UnderwritingStatus,
    UnitMix,
)

# =============================================================================
# Helper: create a parent UnderwritingModel
# =============================================================================


async def _create_uw_model(
    db_session,
    name: str = "Test UW Model",
    **kwargs,
) -> UnderwritingModel:
    """Create and persist a minimal UnderwritingModel."""
    now = datetime.now(UTC)
    model = UnderwritingModel(
        name=name,
        version=kwargs.pop("version", 1),
        status=kwargs.pop("status", UnderwritingStatus.DRAFT),
        created_at=now,
        updated_at=now,
        is_deleted=False,
        **kwargs,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


# =============================================================================
# UnderwritingModel
# =============================================================================


class TestUnderwritingModel:
    """Tests for the parent UnderwritingModel entity."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data(self, db_session):
        model = await _create_uw_model(db_session, name="Clubhouse at Arcadia")
        assert model.id is not None
        assert model.name == "Clubhouse at Arcadia"
        assert model.version == 1
        assert model.status == UnderwritingStatus.DRAFT

    @pytest.mark.asyncio
    async def test_default_values(self, db_session):
        model = await _create_uw_model(db_session)
        assert model.version == 1
        assert model.status == UnderwritingStatus.DRAFT
        assert model.is_deleted is False
        assert model.scenario_name is None
        assert model.property_id is None
        assert model.deal_id is None
        assert model.description is None

    @pytest.mark.asyncio
    async def test_all_statuses(self, db_session):
        for status in UnderwritingStatus:
            model = await _create_uw_model(
                db_session,
                name=f"Model - {status.value}",
                status=status,
            )
            assert model.status == status

    @pytest.mark.asyncio
    async def test_underwriting_status_values(self):
        assert UnderwritingStatus.DRAFT.value == "draft"
        assert UnderwritingStatus.IN_PROGRESS.value == "in_progress"
        assert UnderwritingStatus.UNDER_REVIEW.value == "under_review"
        assert UnderwritingStatus.APPROVED.value == "approved"
        assert UnderwritingStatus.REJECTED.value == "rejected"
        assert UnderwritingStatus.ARCHIVED.value == "archived"

    @pytest.mark.asyncio
    async def test_soft_delete(self, db_session):
        model = await _create_uw_model(db_session)
        assert model.is_deleted is False
        assert model.deleted_at is None

        model.soft_delete()
        await db_session.commit()
        await db_session.refresh(model)
        assert model.is_deleted is True
        assert model.deleted_at is not None

    @pytest.mark.asyncio
    async def test_restore_after_soft_delete(self, db_session):
        model = await _create_uw_model(db_session)
        model.soft_delete()
        await db_session.commit()

        model.restore()
        await db_session.commit()
        await db_session.refresh(model)
        assert model.is_deleted is False
        assert model.deleted_at is None

    @pytest.mark.asyncio
    async def test_scenario_name(self, db_session):
        model = await _create_uw_model(
            db_session,
            name="Scenario Test",
            scenario_name="Upside Case",
        )
        assert model.scenario_name == "Upside Case"

    @pytest.mark.asyncio
    async def test_version_tracking(self, db_session):
        model = await _create_uw_model(db_session, version=3)
        assert model.version == 3

    @pytest.mark.asyncio
    async def test_repr(self, db_session):
        model = await _create_uw_model(db_session, name="Park on Bell")
        assert "Park on Bell" in repr(model)
        assert "draft" in repr(model)

    @pytest.mark.asyncio
    async def test_source_tracking_mixin(self, db_session):
        now = datetime.now(UTC)
        model = await _create_uw_model(db_session)
        model.source_file_name = "Park_on_Bell_UW.xlsx"
        model.source_file_path = "/SharePoint/B&R/Models/Park_on_Bell_UW.xlsx"
        model.extracted_at = now
        model.extraction_status = "success"
        await db_session.commit()
        await db_session.refresh(model)

        assert model.source_file_name == "Park_on_Bell_UW.xlsx"
        assert model.extraction_status == "success"

    @pytest.mark.asyncio
    async def test_timestamp_mixin(self, db_session):
        model = await _create_uw_model(db_session)
        assert model.created_at is not None
        assert model.updated_at is not None


# =============================================================================
# GeneralAssumptions
# =============================================================================


class TestGeneralAssumptions:
    """Tests for GeneralAssumptions model."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ga = GeneralAssumptions(
            underwriting_model_id=parent.id,
            property_name="Clubhouse at Arcadia",
            property_city="Phoenix",
            property_state="AZ",
            year_built=1985,
            units=200,
            total_sf=180000,
            stories=2,
            asset_class="B",
            msa="Phoenix-Mesa-Chandler",
            created_at=now,
            updated_at=now,
        )
        db_session.add(ga)
        await db_session.commit()
        await db_session.refresh(ga)

        assert ga.id is not None
        assert ga.property_name == "Clubhouse at Arcadia"
        assert ga.property_city == "Phoenix"
        assert ga.year_built == 1985
        assert ga.units == 200

    @pytest.mark.asyncio
    async def test_nullable_fields_default_none(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ga = GeneralAssumptions(
            underwriting_model_id=parent.id,
            created_at=now,
            updated_at=now,
        )
        db_session.add(ga)
        await db_session.commit()
        await db_session.refresh(ga)

        assert ga.property_name is None
        assert ga.year_built is None
        assert ga.units is None
        assert ga.property_latitude is None
        assert ga.analysis_date is None

    @pytest.mark.asyncio
    async def test_ownership_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ga = GeneralAssumptions(
            underwriting_model_id=parent.id,
            current_owner="Greystar RE Partners",
            last_sale_date=date(2020, 6, 15),
            last_sale_price=Decimal("22500000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(ga)
        await db_session.commit()
        await db_session.refresh(ga)

        assert ga.current_owner == "Greystar RE Partners"
        assert ga.last_sale_date == date(2020, 6, 15)
        assert ga.last_sale_price == Decimal("22500000.00")

    @pytest.mark.asyncio
    async def test_repr(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ga = GeneralAssumptions(
            underwriting_model_id=parent.id,
            property_name="Element at Tempe North",
            property_city="Tempe",
            property_state="AZ",
            created_at=now,
            updated_at=now,
        )
        db_session.add(ga)
        await db_session.commit()
        assert "Element at Tempe North" in repr(ga)


# =============================================================================
# ExitAssumptions
# =============================================================================


class TestExitAssumptions:
    """Tests for ExitAssumptions model."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ea = ExitAssumptions(
            underwriting_model_id=parent.id,
            exit_period_months=60,
            exit_cap_rate=Decimal("0.0575"),
            sales_transaction_costs=Decimal("0.0200"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(ea)
        await db_session.commit()
        await db_session.refresh(ea)

        assert ea.id is not None
        assert ea.exit_period_months == 60
        assert ea.exit_cap_rate == Decimal("0.0575")
        assert ea.sales_transaction_costs == Decimal("0.0200")

    @pytest.mark.asyncio
    async def test_nullable_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ea = ExitAssumptions(
            underwriting_model_id=parent.id,
            created_at=now,
            updated_at=now,
        )
        db_session.add(ea)
        await db_session.commit()
        await db_session.refresh(ea)

        assert ea.exit_period_months is None
        assert ea.exit_cap_rate is None
        assert ea.sales_transaction_costs is None

    @pytest.mark.asyncio
    async def test_repr(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ea = ExitAssumptions(
            underwriting_model_id=parent.id,
            exit_period_months=60,
            exit_cap_rate=Decimal("0.0575"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(ea)
        await db_session.commit()
        assert "60" in repr(ea)


# =============================================================================
# NOIAssumptions
# =============================================================================


class TestNOIAssumptions:
    """Tests for NOIAssumptions model."""

    @pytest.mark.asyncio
    async def test_create_with_revenue_assumptions(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        noi = NOIAssumptions(
            underwriting_model_id=parent.id,
            market_rent_per_unit=Decimal("1250.00"),
            market_rent_per_sf=Decimal("1.45"),
            in_place_rent_per_unit=Decimal("1150.00"),
            loss_to_lease_pct=Decimal("0.0800"),
            physical_vacancy_pct=Decimal("0.0500"),
            bad_debt_pct=Decimal("0.0200"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(noi)
        await db_session.commit()
        await db_session.refresh(noi)

        assert noi.id is not None
        assert noi.market_rent_per_unit == Decimal("1250.00")
        assert noi.physical_vacancy_pct == Decimal("0.0500")

    @pytest.mark.asyncio
    async def test_rent_growth_projections(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        noi = NOIAssumptions(
            underwriting_model_id=parent.id,
            rent_growth_year_1=Decimal("0.0300"),
            rent_growth_year_2=Decimal("0.0350"),
            rent_growth_year_3=Decimal("0.0350"),
            rent_growth_year_4=Decimal("0.0300"),
            rent_growth_year_5=Decimal("0.0300"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(noi)
        await db_session.commit()
        await db_session.refresh(noi)

        assert noi.rent_growth_year_1 == Decimal("0.0300")
        assert noi.rent_growth_year_5 == Decimal("0.0300")

    @pytest.mark.asyncio
    async def test_expense_assumptions(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        noi = NOIAssumptions(
            underwriting_model_id=parent.id,
            management_fee_pct=Decimal("0.0350"),
            expense_growth_rate=Decimal("0.0300"),
            insurance_per_unit=Decimal("750.00"),
            real_estate_taxes_per_unit=Decimal("1200.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(noi)
        await db_session.commit()
        await db_session.refresh(noi)

        assert noi.management_fee_pct == Decimal("0.0350")
        assert noi.insurance_per_unit == Decimal("750.00")

    @pytest.mark.asyncio
    async def test_t12_reference_values(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        noi = NOIAssumptions(
            underwriting_model_id=parent.id,
            t12_gpr=Decimal("3000000.00"),
            t12_noi=Decimal("1800000.00"),
            t12_egi=Decimal("2700000.00"),
            t12_total_expenses=Decimal("900000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(noi)
        await db_session.commit()
        await db_session.refresh(noi)

        assert noi.t12_noi == Decimal("1800000.00")

    @pytest.mark.asyncio
    async def test_renovation_premium_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        noi = NOIAssumptions(
            underwriting_model_id=parent.id,
            renovation_rent_premium_per_unit=Decimal("150.00"),
            renovation_lease_up_months=3,
            units_to_renovate=100,
            renovation_pace_per_month=8,
            created_at=now,
            updated_at=now,
        )
        db_session.add(noi)
        await db_session.commit()
        await db_session.refresh(noi)

        assert noi.units_to_renovate == 100
        assert noi.renovation_pace_per_month == 8


# =============================================================================
# FinancingAssumptions
# =============================================================================


class TestFinancingAssumptions:
    """Tests for FinancingAssumptions model."""

    @pytest.mark.asyncio
    async def test_create_with_senior_debt(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        fa = FinancingAssumptions(
            underwriting_model_id=parent.id,
            senior_loan_amount=Decimal("15000000.00"),
            senior_ltv=Decimal("0.7000"),
            senior_interest_rate=Decimal("0.055000"),
            senior_rate_type="Fixed",
            senior_term_months=60,
            senior_amortization_months=360,
            senior_io_period_months=24,
            created_at=now,
            updated_at=now,
        )
        db_session.add(fa)
        await db_session.commit()
        await db_session.refresh(fa)

        assert fa.id is not None
        assert fa.senior_loan_amount == Decimal("15000000.00")
        assert fa.senior_ltv == Decimal("0.7000")
        assert fa.senior_term_months == 60

    @pytest.mark.asyncio
    async def test_equity_structure(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        fa = FinancingAssumptions(
            underwriting_model_id=parent.id,
            total_equity_required=Decimal("7500000.00"),
            lp_equity_pct=Decimal("0.9000"),
            gp_equity_pct=Decimal("0.1000"),
            lp_equity_amount=Decimal("6750000.00"),
            gp_equity_amount=Decimal("750000.00"),
            preferred_return=Decimal("0.0800"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(fa)
        await db_session.commit()
        await db_session.refresh(fa)

        assert fa.lp_equity_pct == Decimal("0.9000")
        assert fa.preferred_return == Decimal("0.0800")

    @pytest.mark.asyncio
    async def test_promote_tiers(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        fa = FinancingAssumptions(
            underwriting_model_id=parent.id,
            promote_tier_1_hurdle=Decimal("0.1200"),
            promote_tier_1_gp_split=Decimal("0.2000"),
            promote_tier_2_hurdle=Decimal("0.1800"),
            promote_tier_2_gp_split=Decimal("0.3000"),
            promote_tier_3_hurdle=Decimal("0.2500"),
            promote_tier_3_gp_split=Decimal("0.4000"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(fa)
        await db_session.commit()
        await db_session.refresh(fa)

        assert fa.promote_tier_1_hurdle == Decimal("0.1200")
        assert fa.promote_tier_3_gp_split == Decimal("0.4000")

    @pytest.mark.asyncio
    async def test_mezzanine_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        fa = FinancingAssumptions(
            underwriting_model_id=parent.id,
            mezz_loan_amount=Decimal("2000000.00"),
            mezz_interest_rate=Decimal("0.120000"),
            mezz_term_months=36,
            created_at=now,
            updated_at=now,
        )
        db_session.add(fa)
        await db_session.commit()
        await db_session.refresh(fa)

        assert fa.mezz_loan_amount == Decimal("2000000.00")
        assert fa.mezz_term_months == 36


# =============================================================================
# BudgetAssumptions
# =============================================================================


class TestBudgetAssumptions:
    """Tests for BudgetAssumptions model."""

    @pytest.mark.asyncio
    async def test_create_with_purchase_data(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ba = BudgetAssumptions(
            underwriting_model_id=parent.id,
            purchase_price=Decimal("20000000.00"),
            price_per_unit=Decimal("100000.00"),
            price_per_sf=Decimal("111.11"),
            going_in_cap_rate=Decimal("0.0650"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(ba)
        await db_session.commit()
        await db_session.refresh(ba)

        assert ba.id is not None
        assert ba.purchase_price == Decimal("20000000.00")
        assert ba.going_in_cap_rate == Decimal("0.0650")

    @pytest.mark.asyncio
    async def test_renovation_budget(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ba = BudgetAssumptions(
            underwriting_model_id=parent.id,
            interior_renovation_per_unit=Decimal("8500.00"),
            appliance_package_per_unit=Decimal("2000.00"),
            flooring_per_unit=Decimal("1500.00"),
            total_unit_renovation_per_unit=Decimal("12000.00"),
            total_renovation_budget=Decimal("2400000.00"),
            renovation_contingency_pct=Decimal("0.1000"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(ba)
        await db_session.commit()
        await db_session.refresh(ba)

        assert ba.total_renovation_budget == Decimal("2400000.00")
        assert ba.renovation_contingency_pct == Decimal("0.1000")

    @pytest.mark.asyncio
    async def test_closing_costs(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ba = BudgetAssumptions(
            underwriting_model_id=parent.id,
            title_insurance=Decimal("25000.00"),
            appraisal_costs=Decimal("8000.00"),
            legal_costs=Decimal("15000.00"),
            total_closing_costs=Decimal("150000.00"),
            closing_costs_pct=Decimal("0.0075"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(ba)
        await db_session.commit()
        await db_session.refresh(ba)

        assert ba.total_closing_costs == Decimal("150000.00")

    @pytest.mark.asyncio
    async def test_total_project_costs(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ba = BudgetAssumptions(
            underwriting_model_id=parent.id,
            total_project_cost=Decimal("23000000.00"),
            total_cost_per_unit=Decimal("115000.00"),
            total_cost_per_sf=Decimal("127.78"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(ba)
        await db_session.commit()
        await db_session.refresh(ba)

        assert ba.total_project_cost == Decimal("23000000.00")


# =============================================================================
# PropertyReturns
# =============================================================================


class TestPropertyReturns:
    """Tests for PropertyReturns model."""

    @pytest.mark.asyncio
    async def test_create_with_cap_rates(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        pr = PropertyReturns(
            underwriting_model_id=parent.id,
            going_in_cap_rate=Decimal("0.0650"),
            year_1_cap_rate=Decimal("0.0580"),
            stabilized_cap_rate=Decimal("0.0700"),
            exit_cap_rate=Decimal("0.0575"),
            cap_rate_spread=Decimal("0.0075"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(pr)
        await db_session.commit()
        await db_session.refresh(pr)

        assert pr.id is not None
        assert pr.going_in_cap_rate == Decimal("0.0650")
        assert pr.exit_cap_rate == Decimal("0.0575")

    @pytest.mark.asyncio
    async def test_noi_projections(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        pr = PropertyReturns(
            underwriting_model_id=parent.id,
            t12_noi=Decimal("1500000.00"),
            year_1_noi=Decimal("1600000.00"),
            year_2_noi=Decimal("1750000.00"),
            year_3_noi=Decimal("1850000.00"),
            stabilized_noi=Decimal("2000000.00"),
            exit_noi=Decimal("2100000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(pr)
        await db_session.commit()
        await db_session.refresh(pr)

        assert pr.t12_noi == Decimal("1500000.00")
        assert pr.stabilized_noi == Decimal("2000000.00")

    @pytest.mark.asyncio
    async def test_unlevered_returns(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        pr = PropertyReturns(
            underwriting_model_id=parent.id,
            unlevered_irr=Decimal("0.1250"),
            unlevered_equity_multiple=Decimal("1.850"),
            unlevered_cash_on_cash_year_1=Decimal("0.0580"),
            unlevered_cash_on_cash_avg=Decimal("0.0720"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(pr)
        await db_session.commit()
        await db_session.refresh(pr)

        assert pr.unlevered_irr == Decimal("0.1250")
        assert pr.unlevered_equity_multiple == Decimal("1.850")

    @pytest.mark.asyncio
    async def test_property_value_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        pr = PropertyReturns(
            underwriting_model_id=parent.id,
            purchase_price=Decimal("20000000.00"),
            total_cost_basis=Decimal("23000000.00"),
            exit_value=Decimal("30000000.00"),
            value_creation=Decimal("7000000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(pr)
        await db_session.commit()
        await db_session.refresh(pr)

        assert pr.value_creation == Decimal("7000000.00")


# =============================================================================
# EquityReturns
# =============================================================================


class TestEquityReturns:
    """Tests for EquityReturns model."""

    @pytest.mark.asyncio
    async def test_create_with_levered_returns(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        er = EquityReturns(
            underwriting_model_id=parent.id,
            levered_irr=Decimal("0.1850"),
            levered_equity_multiple=Decimal("2.100"),
            levered_cash_on_cash_year_1=Decimal("0.0800"),
            levered_cash_on_cash_avg=Decimal("0.0950"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(er)
        await db_session.commit()
        await db_session.refresh(er)

        assert er.id is not None
        assert er.levered_irr == Decimal("0.1850")
        assert er.levered_equity_multiple == Decimal("2.100")

    @pytest.mark.asyncio
    async def test_lp_returns(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        er = EquityReturns(
            underwriting_model_id=parent.id,
            lp_irr=Decimal("0.1500"),
            lp_equity_multiple=Decimal("1.850"),
            lp_total_distributions=Decimal("12500000.00"),
            lp_preferred_return=Decimal("4000000.00"),
            lp_profit_share=Decimal("2000000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(er)
        await db_session.commit()
        await db_session.refresh(er)

        assert er.lp_irr == Decimal("0.1500")
        assert er.lp_total_distributions == Decimal("12500000.00")

    @pytest.mark.asyncio
    async def test_gp_returns(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        er = EquityReturns(
            underwriting_model_id=parent.id,
            gp_irr=Decimal("0.3500"),
            gp_equity_multiple=Decimal("4.500"),
            gp_promote_earned=Decimal("1500000.00"),
            gp_fees_earned=Decimal("300000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(er)
        await db_session.commit()
        await db_session.refresh(er)

        assert er.gp_irr == Decimal("0.3500")
        assert er.gp_promote_earned == Decimal("1500000.00")

    @pytest.mark.asyncio
    async def test_promote_tier_achievement(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        er = EquityReturns(
            underwriting_model_id=parent.id,
            promote_tier_achieved=2,
            promote_tier_1_amount=Decimal("500000.00"),
            promote_tier_2_amount=Decimal("300000.00"),
            promote_tier_3_amount=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(er)
        await db_session.commit()
        await db_session.refresh(er)

        assert er.promote_tier_achieved == 2
        assert er.promote_tier_3_amount is None

    @pytest.mark.asyncio
    async def test_waterfall_summary(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        er = EquityReturns(
            underwriting_model_id=parent.id,
            total_equity_invested=Decimal("7500000.00"),
            total_distributions=Decimal("15000000.00"),
            total_profit=Decimal("7500000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(er)
        await db_session.commit()
        await db_session.refresh(er)

        assert er.total_profit == Decimal("7500000.00")

    @pytest.mark.asyncio
    async def test_negative_returns(self, db_session):
        """Negative returns are valid (e.g., Element at Tempe North)."""
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        er = EquityReturns(
            underwriting_model_id=parent.id,
            levered_irr=Decimal("-0.0490"),
            lp_irr=Decimal("-0.0300"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(er)
        await db_session.commit()
        await db_session.refresh(er)

        assert er.levered_irr == Decimal("-0.0490")
        assert er.lp_irr == Decimal("-0.0300")


# =============================================================================
# UnitMix
# =============================================================================


class TestUnitMix:
    """Tests for UnitMix model."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        um = UnitMix(
            underwriting_model_id=parent.id,
            unit_type="2BR/2BA",
            unit_type_code="B2",
            bedrooms=2,
            bathrooms=Decimal("2.0"),
            unit_count=80,
            avg_sf=Decimal("950.00"),
            in_place_rent=Decimal("1200.00"),
            market_rent=Decimal("1350.00"),
            renovation_cost_per_unit=Decimal("12000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(um)
        await db_session.commit()
        await db_session.refresh(um)

        assert um.id is not None
        assert um.unit_type == "2BR/2BA"
        assert um.bedrooms == 2
        assert um.unit_count == 80

    @pytest.mark.asyncio
    async def test_required_unit_type_field(self, db_session):
        """unit_type is NOT NULL."""
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        um = UnitMix(
            underwriting_model_id=parent.id,
            unit_type="Studio",
            created_at=now,
            updated_at=now,
        )
        db_session.add(um)
        await db_session.commit()
        await db_session.refresh(um)
        assert um.unit_type == "Studio"

    @pytest.mark.asyncio
    async def test_loss_to_lease_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        um = UnitMix(
            underwriting_model_id=parent.id,
            unit_type="1BR/1BA",
            in_place_rent=Decimal("1100.00"),
            market_rent=Decimal("1250.00"),
            loss_to_lease=Decimal("150.00"),
            loss_to_lease_pct=Decimal("0.1200"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(um)
        await db_session.commit()
        await db_session.refresh(um)

        assert um.loss_to_lease == Decimal("150.00")
        assert um.loss_to_lease_pct == Decimal("0.1200")

    @pytest.mark.asyncio
    async def test_revenue_calculations(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        um = UnitMix(
            underwriting_model_id=parent.id,
            unit_type="2BR/1BA",
            monthly_gpr=Decimal("108000.00"),
            annual_gpr=Decimal("1296000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(um)
        await db_session.commit()
        await db_session.refresh(um)

        assert um.annual_gpr == Decimal("1296000.00")


# =============================================================================
# RentComp
# =============================================================================


class TestRentComp:
    """Tests for RentComp model."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        rc = RentComp(
            underwriting_model_id=parent.id,
            comp_number=1,
            property_name="The Retreat at Gilbert",
            property_city="Gilbert",
            property_state="AZ",
            year_built=1998,
            total_units=250,
            avg_rent=Decimal("1400.00"),
            avg_rent_per_sf=Decimal("1.55"),
            occupancy_pct=Decimal("0.9600"),
            distance_miles=Decimal("2.50"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(rc)
        await db_session.commit()
        await db_session.refresh(rc)

        assert rc.id is not None
        assert rc.comp_number == 1
        assert rc.property_name == "The Retreat at Gilbert"
        assert rc.occupancy_pct == Decimal("0.9600")

    @pytest.mark.asyncio
    async def test_rent_by_unit_type(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        rc = RentComp(
            underwriting_model_id=parent.id,
            comp_number=2,
            property_name="Avana on Camelback",
            studio_rent=Decimal("900.00"),
            one_br_rent=Decimal("1100.00"),
            two_br_rent=Decimal("1400.00"),
            three_br_rent=Decimal("1700.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(rc)
        await db_session.commit()
        await db_session.refresh(rc)

        assert rc.studio_rent == Decimal("900.00")
        assert rc.three_br_rent == Decimal("1700.00")

    @pytest.mark.asyncio
    async def test_data_source_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        rc = RentComp(
            underwriting_model_id=parent.id,
            comp_number=3,
            data_date=date(2026, 1, 15),
            data_source="CoStar",
            notes="Newly renovated units commanding premium",
            created_at=now,
            updated_at=now,
        )
        db_session.add(rc)
        await db_session.commit()
        await db_session.refresh(rc)

        assert rc.data_source == "CoStar"
        assert rc.data_date == date(2026, 1, 15)


# =============================================================================
# SalesComp
# =============================================================================


class TestSalesComp:
    """Tests for SalesComp model."""

    @pytest.mark.asyncio
    async def test_create_with_transaction_data(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        sc = SalesComp(
            underwriting_model_id=parent.id,
            comp_number=1,
            property_name="Mesa Palms",
            property_city="Mesa",
            property_state="AZ",
            sale_date=date(2025, 9, 15),
            sale_price=Decimal("28000000.00"),
            price_per_unit=Decimal("140000.00"),
            price_per_sf=Decimal("155.56"),
            total_units=200,
            cap_rate=Decimal("0.0600"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(sc)
        await db_session.commit()
        await db_session.refresh(sc)

        assert sc.id is not None
        assert sc.sale_price == Decimal("28000000.00")
        assert sc.cap_rate == Decimal("0.0600")

    @pytest.mark.asyncio
    async def test_buyer_seller_info(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        sc = SalesComp(
            underwriting_model_id=parent.id,
            comp_number=2,
            buyer_name="Starwood Capital",
            buyer_type="Private Equity",
            seller_name="AvalonBay Communities",
            seller_type="REIT",
            broker="CBRE",
            transaction_type="Arm's length",
            created_at=now,
            updated_at=now,
        )
        db_session.add(sc)
        await db_session.commit()
        await db_session.refresh(sc)

        assert sc.buyer_type == "Private Equity"
        assert sc.seller_type == "REIT"

    @pytest.mark.asyncio
    async def test_financing_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        sc = SalesComp(
            underwriting_model_id=parent.id,
            comp_number=3,
            financing_type="Agency",
            loan_amount=Decimal("18000000.00"),
            ltv=Decimal("0.6500"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(sc)
        await db_session.commit()
        await db_session.refresh(sc)

        assert sc.financing_type == "Agency"
        assert sc.ltv == Decimal("0.6500")


# =============================================================================
# AnnualCashflow
# =============================================================================


class TestAnnualCashflow:
    """Tests for AnnualCashflow model."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        cf = AnnualCashflow(
            underwriting_model_id=parent.id,
            year_number=1,
            period_label="Year 1",
            gross_potential_rent=Decimal("3000000.00"),
            vacancy_loss=Decimal("-150000.00"),
            net_rental_income=Decimal("2850000.00"),
            effective_gross_income=Decimal("3050000.00"),
            total_operating_expenses=Decimal("1200000.00"),
            net_operating_income=Decimal("1850000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(cf)
        await db_session.commit()
        await db_session.refresh(cf)

        assert cf.id is not None
        assert cf.year_number == 1
        assert cf.net_operating_income == Decimal("1850000.00")

    @pytest.mark.asyncio
    async def test_debt_service_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        cf = AnnualCashflow(
            underwriting_model_id=parent.id,
            year_number=1,
            senior_debt_service=Decimal("900000.00"),
            senior_interest=Decimal("825000.00"),
            senior_principal=Decimal("75000.00"),
            total_debt_service=Decimal("900000.00"),
            cash_flow_before_debt=Decimal("1750000.00"),
            cash_flow_after_debt=Decimal("850000.00"),
            dscr=Decimal("1.9444"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(cf)
        await db_session.commit()
        await db_session.refresh(cf)

        assert cf.dscr == Decimal("1.9444")
        assert cf.cash_flow_after_debt == Decimal("850000.00")

    @pytest.mark.asyncio
    async def test_expense_line_items(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        cf = AnnualCashflow(
            underwriting_model_id=parent.id,
            year_number=1,
            administrative=Decimal("50000.00"),
            payroll=Decimal("200000.00"),
            utilities=Decimal("180000.00"),
            repairs_maintenance=Decimal("120000.00"),
            insurance=Decimal("150000.00"),
            real_estate_taxes=Decimal("240000.00"),
            management_fee=Decimal("100000.00"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(cf)
        await db_session.commit()
        await db_session.refresh(cf)

        assert cf.insurance == Decimal("150000.00")
        assert cf.real_estate_taxes == Decimal("240000.00")

    @pytest.mark.asyncio
    async def test_distribution_fields(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        cf = AnnualCashflow(
            underwriting_model_id=parent.id,
            year_number=1,
            lp_distribution=Decimal("600000.00"),
            gp_distribution=Decimal("200000.00"),
            total_distributions=Decimal("800000.00"),
            cash_on_cash_return=Decimal("0.1067"),
            created_at=now,
            updated_at=now,
        )
        db_session.add(cf)
        await db_session.commit()
        await db_session.refresh(cf)

        assert cf.total_distributions == Decimal("800000.00")
        assert cf.cash_on_cash_return == Decimal("0.1067")

    @pytest.mark.asyncio
    async def test_period_dates(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        cf = AnnualCashflow(
            underwriting_model_id=parent.id,
            year_number=1,
            period_start_date=date(2026, 1, 1),
            period_end_date=date(2026, 12, 31),
            is_partial_year=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(cf)
        await db_session.commit()
        await db_session.refresh(cf)

        assert cf.period_start_date == date(2026, 1, 1)
        assert cf.is_partial_year is False


# =============================================================================
# Relationship Loading Tests
# =============================================================================


class TestRelationships:
    """Tests for parent-child relationship loading."""

    @pytest.mark.asyncio
    async def test_uw_model_to_general_assumptions(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ga = GeneralAssumptions(
            underwriting_model_id=parent.id,
            property_name="The Northern",
            property_city="Phoenix",
            created_at=now,
            updated_at=now,
        )
        db_session.add(ga)
        await db_session.commit()

        result = await db_session.execute(
            select(UnderwritingModel)
            .options(selectinload(UnderwritingModel.general_assumptions))
            .where(UnderwritingModel.id == parent.id)
        )
        loaded = result.scalar_one()
        assert loaded.general_assumptions is not None
        assert loaded.general_assumptions.property_name == "The Northern"

    @pytest.mark.asyncio
    async def test_uw_model_to_annual_cashflows(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        for year in range(1, 6):
            cf = AnnualCashflow(
                underwriting_model_id=parent.id,
                year_number=year,
                period_label=f"Year {year}",
                net_operating_income=Decimal(str(1500000 + year * 100000)),
                created_at=now,
                updated_at=now,
            )
            db_session.add(cf)
        await db_session.commit()

        result = await db_session.execute(
            select(UnderwritingModel)
            .options(selectinload(UnderwritingModel.annual_cashflows))
            .where(UnderwritingModel.id == parent.id)
        )
        loaded = result.scalar_one()
        assert len(loaded.annual_cashflows) == 5

    @pytest.mark.asyncio
    async def test_uw_model_to_unit_mixes(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        for unit_type in ["Studio", "1BR/1BA", "2BR/2BA", "3BR/2BA"]:
            um = UnitMix(
                underwriting_model_id=parent.id,
                unit_type=unit_type,
                created_at=now,
                updated_at=now,
            )
            db_session.add(um)
        await db_session.commit()

        result = await db_session.execute(
            select(UnderwritingModel)
            .options(selectinload(UnderwritingModel.unit_mixes))
            .where(UnderwritingModel.id == parent.id)
        )
        loaded = result.scalar_one()
        assert len(loaded.unit_mixes) == 4

    @pytest.mark.asyncio
    async def test_uw_model_to_rent_comps(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        for i in range(1, 4):
            rc = RentComp(
                underwriting_model_id=parent.id,
                comp_number=i,
                property_name=f"Rent Comp {i}",
                created_at=now,
                updated_at=now,
            )
            db_session.add(rc)
        await db_session.commit()

        result = await db_session.execute(
            select(UnderwritingModel)
            .options(selectinload(UnderwritingModel.rent_comps))
            .where(UnderwritingModel.id == parent.id)
        )
        loaded = result.scalar_one()
        assert len(loaded.rent_comps) == 3

    @pytest.mark.asyncio
    async def test_uw_model_to_sales_comps(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        for i in range(1, 3):
            sc = SalesComp(
                underwriting_model_id=parent.id,
                comp_number=i,
                created_at=now,
                updated_at=now,
            )
            db_session.add(sc)
        await db_session.commit()

        result = await db_session.execute(
            select(UnderwritingModel)
            .options(selectinload(UnderwritingModel.sales_comps))
            .where(UnderwritingModel.id == parent.id)
        )
        loaded = result.scalar_one()
        assert len(loaded.sales_comps) == 2

    @pytest.mark.asyncio
    async def test_uw_model_one_to_one_children(self, db_session):
        """Test all one-to-one relationships load correctly."""
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)

        # Create all one-to-one children
        db_session.add(ExitAssumptions(
            underwriting_model_id=parent.id,
            exit_period_months=60,
            created_at=now, updated_at=now,
        ))
        db_session.add(NOIAssumptions(
            underwriting_model_id=parent.id,
            market_rent_per_unit=Decimal("1300.00"),
            created_at=now, updated_at=now,
        ))
        db_session.add(FinancingAssumptions(
            underwriting_model_id=parent.id,
            senior_loan_amount=Decimal("15000000.00"),
            created_at=now, updated_at=now,
        ))
        db_session.add(BudgetAssumptions(
            underwriting_model_id=parent.id,
            purchase_price=Decimal("20000000.00"),
            created_at=now, updated_at=now,
        ))
        db_session.add(PropertyReturns(
            underwriting_model_id=parent.id,
            going_in_cap_rate=Decimal("0.0650"),
            created_at=now, updated_at=now,
        ))
        db_session.add(EquityReturns(
            underwriting_model_id=parent.id,
            lp_irr=Decimal("0.1500"),
            created_at=now, updated_at=now,
        ))
        await db_session.commit()

        result = await db_session.execute(
            select(UnderwritingModel)
            .options(
                selectinload(UnderwritingModel.exit_assumptions),
                selectinload(UnderwritingModel.noi_assumptions),
                selectinload(UnderwritingModel.financing_assumptions),
                selectinload(UnderwritingModel.budget_assumptions),
                selectinload(UnderwritingModel.property_returns),
                selectinload(UnderwritingModel.equity_returns),
            )
            .where(UnderwritingModel.id == parent.id)
        )
        loaded = result.scalar_one()

        assert loaded.exit_assumptions is not None
        assert loaded.exit_assumptions.exit_period_months == 60
        assert loaded.noi_assumptions is not None
        assert loaded.financing_assumptions is not None
        assert loaded.budget_assumptions is not None
        assert loaded.property_returns is not None
        assert loaded.equity_returns is not None

    @pytest.mark.asyncio
    async def test_cascade_delete(self, db_session):
        """Deleting parent should cascade to children."""
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        db_session.add(ExitAssumptions(
            underwriting_model_id=parent.id,
            exit_period_months=60,
            created_at=now, updated_at=now,
        ))
        db_session.add(AnnualCashflow(
            underwriting_model_id=parent.id,
            year_number=1,
            created_at=now, updated_at=now,
        ))
        await db_session.commit()

        await db_session.delete(parent)
        await db_session.commit()

        exits = (await db_session.execute(select(ExitAssumptions))).scalars().all()
        cashflows = (await db_session.execute(select(AnnualCashflow))).scalars().all()
        assert len(exits) == 0
        assert len(cashflows) == 0

    @pytest.mark.asyncio
    async def test_child_back_populates_parent(self, db_session):
        """Child can navigate back to parent."""
        parent = await _create_uw_model(db_session, name="Broadstone 7th Street")
        now = datetime.now(UTC)
        ea = ExitAssumptions(
            underwriting_model_id=parent.id,
            created_at=now,
            updated_at=now,
        )
        db_session.add(ea)
        await db_session.commit()

        result = await db_session.execute(
            select(ExitAssumptions)
            .options(selectinload(ExitAssumptions.underwriting_model))
            .where(ExitAssumptions.underwriting_model_id == parent.id)
        )
        loaded_ea = result.scalar_one()
        assert loaded_ea.underwriting_model is not None
        assert loaded_ea.underwriting_model.name == "Broadstone 7th Street"


# =============================================================================
# SourceTrackingMixin (tested via child models)
# =============================================================================


class TestSourceTrackingMixin:
    """Tests for the SourceTrackingMixin fields on child models."""

    @pytest.mark.asyncio
    async def test_source_tracking_on_child(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ga = GeneralAssumptions(
            underwriting_model_id=parent.id,
            property_name="Test Property",
            source_file_name="UW_Model_v3.xlsx",
            source_file_path="/SharePoint/B&R Capital/Models/UW_Model_v3.xlsx",
            source_file_modified_at=now,
            extracted_at=now,
            extraction_version="2.1.0",
            extraction_status="success",
            extraction_errors=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(ga)
        await db_session.commit()
        await db_session.refresh(ga)

        assert ga.source_file_name == "UW_Model_v3.xlsx"
        assert ga.extraction_version == "2.1.0"
        assert ga.extraction_status == "success"
        assert ga.extraction_errors is None

    @pytest.mark.asyncio
    async def test_extraction_error_tracking(self, db_session):
        parent = await _create_uw_model(db_session)
        now = datetime.now(UTC)
        ba = BudgetAssumptions(
            underwriting_model_id=parent.id,
            extraction_status="error",
            extraction_errors="Cell D15 not found in template",
            created_at=now,
            updated_at=now,
        )
        db_session.add(ba)
        await db_session.commit()
        await db_session.refresh(ba)

        assert ba.extraction_status == "error"
        assert "Cell D15" in ba.extraction_errors
