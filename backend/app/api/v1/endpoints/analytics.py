"""
Analytics endpoints for data visualization and ML predictions.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Deal, DealStage, Property
from app.services.ml import get_rent_growth_predictor

router = APIRouter()


def _decimal_to_float(value: Decimal | None) -> float | None:
    """Convert Decimal to float, returning None if input is None."""
    return float(value) if value is not None else None


def _get_time_period_start(time_period: str) -> datetime:
    """Calculate the start date based on time period."""
    now = datetime.now(UTC)
    if time_period == "mtd":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_period == "qtd":
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        return now.replace(
            month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    elif time_period == "ytd":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_period == "1y":
        return now - timedelta(days=365)
    elif time_period == "3y":
        return now - timedelta(days=365 * 3)
    elif time_period == "5y":
        return now - timedelta(days=365 * 5)
    else:  # all
        return datetime(1970, 1, 1, tzinfo=UTC)


@router.get("/dashboard")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated metrics for the main dashboard.

    Returns:
    - Portfolio summary statistics
    - Key performance indicators
    - Recent activity
    """
    # Query portfolio summary from Property table
    property_stats = await db.execute(
        select(
            func.count(Property.id).label("total_properties"),
            func.coalesce(func.sum(Property.total_units), 0).label("total_units"),
            func.coalesce(func.sum(Property.total_sf), 0).label("total_sf"),
            func.coalesce(func.sum(Property.current_value), 0).label("total_value"),
            func.avg(Property.occupancy_rate).label("avg_occupancy"),
            func.avg(Property.cap_rate).label("avg_cap_rate"),
        )
    )
    prop_row = property_stats.fetchone()

    # Get YTD start date
    ytd_start = _get_time_period_start("ytd")

    # Query deal pipeline metrics
    deal_pipeline_stats = await db.execute(
        select(func.count(Deal.id)).where(
            Deal.stage.notin_([DealStage.CLOSED, DealStage.DEAD])
        )
    )
    deals_in_pipeline = deal_pipeline_stats.scalar() or 0

    # Query deals closed YTD
    deals_closed_ytd_result = await db.execute(
        select(
            func.count(Deal.id).label("count"),
            func.coalesce(func.sum(Deal.final_price), 0).label("capital_deployed"),
        ).where(
            Deal.stage == DealStage.CLOSED,
            Deal.actual_close_date >= ytd_start.date(),
        )
    )
    closed_row = deals_closed_ytd_result.fetchone()
    deals_closed_ytd = closed_row.count if closed_row else 0
    capital_deployed_ytd = _decimal_to_float(
        closed_row.capital_deployed if closed_row else 0
    )

    # Query properties with low occupancy (alerts)
    low_occupancy_count_result = await db.execute(
        select(func.count(Property.id)).where(
            Property.occupancy_rate < 90.0,
            Property.occupancy_rate.isnot(None),
        )
    )
    low_occupancy_count = low_occupancy_count_result.scalar() or 0

    # Query deals entering due diligence this week
    week_start = datetime.now(UTC) - timedelta(days=7)
    dd_deals_result = await db.execute(
        select(func.count(Deal.id)).where(
            Deal.stage == DealStage.DUE_DILIGENCE,
            Deal.stage_updated_at >= week_start,
        )
    )
    dd_deals_count = dd_deals_result.scalar() or 0

    # Query recent deal activity (last 10 stage changes)
    recent_deals_result = await db.execute(
        select(Deal.name, Deal.stage, Deal.stage_updated_at)
        .where(Deal.stage_updated_at.isnot(None))
        .order_by(Deal.stage_updated_at.desc())
        .limit(5)
    )
    recent_deals = recent_deals_result.fetchall()

    # Query recent property updates
    recent_properties_result = await db.execute(
        select(Property.name, Property.updated_at)
        .where(Property.updated_at.isnot(None))
        .order_by(Property.updated_at.desc())
        .limit(5)
    )
    recent_properties = recent_properties_result.fetchall()

    # Build recent activity list
    recent_activity = []
    for deal in recent_deals:
        stage_display = deal.stage.value.replace("_", " ").title() if deal.stage else ""
        recent_activity.append(
            {
                "type": "deal_update",
                "message": f"{deal.name} moved to {stage_display}",
                "timestamp": deal.stage_updated_at.isoformat()
                if deal.stage_updated_at
                else None,
            }
        )
    for prop in recent_properties:
        recent_activity.append(
            {
                "type": "property_update",
                "message": f"{prop.name} updated",
                "timestamp": prop.updated_at.isoformat() if prop.updated_at else None,
            }
        )

    # Sort by timestamp and take top 5
    recent_activity.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    recent_activity = recent_activity[:5]

    # Build response with database values, falling back to defaults if no data
    total_properties = prop_row.total_properties if prop_row else 0

    # Use mock data as fallback when database is empty
    if total_properties == 0:
        return {
            "portfolio_summary": {
                "total_properties": 45,
                "total_units": 5240,
                "total_sf": 1250000,
                "total_value": 425000000,
                "avg_occupancy": 94.5,
                "avg_cap_rate": 5.8,
            },
            "kpis": {
                "ytd_noi_growth": 4.2,
                "ytd_rent_growth": 3.8,
                "deals_in_pipeline": 12,
                "deals_closed_ytd": 5,
                "capital_deployed_ytd": 85000000,
            },
            "alerts": [
                {
                    "type": "warning",
                    "message": "3 properties below 90% occupancy",
                    "count": 3,
                },
                {
                    "type": "info",
                    "message": "2 deals entering due diligence this week",
                    "count": 2,
                },
            ],
            "recent_activity": [
                {
                    "type": "deal_update",
                    "message": "Phoenix Multifamily moved to Underwriting",
                    "timestamp": "2024-12-05T14:30:00Z",
                },
                {
                    "type": "property_update",
                    "message": "Sunset Apartments rent roll updated",
                    "timestamp": "2024-12-05T10:15:00Z",
                },
            ],
        }

    # Build alerts based on actual data
    alerts = []
    if low_occupancy_count > 0:
        alerts.append(
            {
                "type": "warning",
                "message": f"{low_occupancy_count} properties below 90% occupancy",
                "count": low_occupancy_count,
            }
        )
    if dd_deals_count > 0:
        alerts.append(
            {
                "type": "info",
                "message": f"{dd_deals_count} deals entering due diligence this week",
                "count": dd_deals_count,
            }
        )

    return {
        "portfolio_summary": {
            "total_properties": total_properties,
            "total_units": prop_row.total_units if prop_row else 0,
            "total_sf": prop_row.total_sf if prop_row else 0,
            "total_value": _decimal_to_float(prop_row.total_value) if prop_row else 0,
            "avg_occupancy": round(_decimal_to_float(prop_row.avg_occupancy) or 0, 1),
            "avg_cap_rate": round(_decimal_to_float(prop_row.avg_cap_rate) or 0, 1),
        },
        "kpis": {
            "ytd_noi_growth": 0.0,  # Would need historical NOI data to calculate
            "ytd_rent_growth": 0.0,  # Would need historical rent data to calculate
            "deals_in_pipeline": deals_in_pipeline,
            "deals_closed_ytd": deals_closed_ytd,
            "capital_deployed_ytd": capital_deployed_ytd or 0,
        },
        "alerts": alerts
        if alerts
        else [{"type": "info", "message": "No alerts at this time", "count": 0}],
        "recent_activity": recent_activity
        if recent_activity
        else [{"type": "info", "message": "No recent activity", "timestamp": None}],
    }


@router.get("/portfolio")
async def get_portfolio_analytics(
    time_period: str = Query("ytd", pattern="^(mtd|qtd|ytd|1y|3y|5y|all)$"),
    property_type: str | None = None,
    market: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio-level analytics and trends.

    - **time_period**: Analysis period (mtd, qtd, ytd, 1y, 3y, 5y, all)
    - **property_type**: Filter by property type
    - **market**: Filter by market
    """
    # Build base query with optional filters
    base_filter = []
    if property_type:
        base_filter.append(Property.property_type == property_type)
    if market:
        base_filter.append(func.lower(Property.market) == func.lower(market))

    # Query composition by property type
    by_type_result = await db.execute(
        select(
            Property.property_type,
            func.count(Property.id).label("count"),
            func.coalesce(func.sum(Property.current_value), 0).label("value"),
        )
        .where(*base_filter if base_filter else [True])
        .group_by(Property.property_type)
    )
    by_type_rows = by_type_result.fetchall()

    # Query composition by market
    by_market_result = await db.execute(
        select(
            Property.market,
            func.count(Property.id).label("count"),
            func.coalesce(func.sum(Property.current_value), 0).label("value"),
        )
        .where(Property.market.isnot(None), *base_filter if base_filter else [])
        .group_by(Property.market)
    )
    by_market_rows = by_market_result.fetchall()

    # Calculate total value for percentage calculations
    total_value_result = await db.execute(
        select(func.coalesce(func.sum(Property.current_value), 0)).where(
            *base_filter if base_filter else [True]
        )
    )
    total_value = (
        _decimal_to_float(total_value_result.scalar()) or 1
    )  # Avoid division by zero

    # Check if we have any data
    total_count_result = await db.execute(
        select(func.count(Property.id)).where(*base_filter if base_filter else [True])
    )
    total_count = total_count_result.scalar() or 0

    # Return mock data if no properties exist
    if total_count == 0:
        return {
            "time_period": time_period,
            "performance": {
                "total_return": 12.5,
                "income_return": 6.2,
                "appreciation_return": 6.3,
                "benchmark_return": 10.8,
                "alpha": 1.7,
            },
            "composition": {
                "by_type": {
                    "multifamily": {"count": 25, "value": 250000000, "pct": 58.8},
                    "office": {"count": 10, "value": 100000000, "pct": 23.5},
                    "retail": {"count": 6, "value": 50000000, "pct": 11.8},
                    "industrial": {"count": 4, "value": 25000000, "pct": 5.9},
                },
                "by_market": {
                    "Phoenix Metro": {"count": 30, "value": 320000000, "pct": 75.3},
                    "Tucson": {"count": 10, "value": 70000000, "pct": 16.5},
                    "Other AZ": {"count": 5, "value": 35000000, "pct": 8.2},
                },
            },
            "trends": {
                "noi": {
                    "values": [1200000, 1250000, 1280000, 1320000, 1350000, 1400000],
                    "periods": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                    "growth_rate": 3.7,
                },
                "occupancy": {
                    "values": [93.5, 94.0, 94.2, 94.5, 94.8, 94.5],
                    "periods": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                },
                "rent_psf": {
                    "values": [1.85, 1.88, 1.90, 1.92, 1.95, 1.98],
                    "periods": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                    "growth_rate": 7.0,
                },
            },
        }

    # Build composition by type
    composition_by_type = {}
    for row in by_type_rows:
        if row.property_type:
            value = _decimal_to_float(row.value) or 0
            composition_by_type[row.property_type] = {
                "count": row.count,
                "value": value,
                "pct": round((value / total_value) * 100, 1) if total_value > 0 else 0,
            }

    # Build composition by market
    composition_by_market = {}
    for row in by_market_rows:
        if row.market:
            value = _decimal_to_float(row.value) or 0
            composition_by_market[row.market] = {
                "count": row.count,
                "value": value,
                "pct": round((value / total_value) * 100, 1) if total_value > 0 else 0,
            }

    # Query current averages for trends (using current data as single point)
    avg_metrics_result = await db.execute(
        select(
            func.avg(Property.noi).label("avg_noi"),
            func.avg(Property.occupancy_rate).label("avg_occupancy"),
            func.avg(Property.avg_rent_per_sf).label("avg_rent_psf"),
        ).where(*base_filter if base_filter else [True])
    )
    avg_metrics = avg_metrics_result.fetchone()

    # Current values for trends (would need historical data for actual trends)
    current_noi = _decimal_to_float(avg_metrics.avg_noi) if avg_metrics else 0
    current_occupancy = (
        _decimal_to_float(avg_metrics.avg_occupancy) if avg_metrics else 0
    )
    current_rent_psf = _decimal_to_float(avg_metrics.avg_rent_psf) if avg_metrics else 0

    return {
        "time_period": time_period,
        "performance": {
            "total_return": 0.0,  # Would need historical value data
            "income_return": 0.0,  # Would need historical NOI data
            "appreciation_return": 0.0,  # Would need historical value data
            "benchmark_return": 0.0,  # Would need external benchmark data
            "alpha": 0.0,
        },
        "composition": {
            "by_type": composition_by_type,
            "by_market": composition_by_market,
        },
        "trends": {
            "noi": {
                "values": [current_noi] if current_noi else [],
                "periods": ["Current"],
                "growth_rate": 0.0,  # Would need historical data
            },
            "occupancy": {
                "values": [round(current_occupancy, 1)] if current_occupancy else [],
                "periods": ["Current"],
            },
            "rent_psf": {
                "values": [round(current_rent_psf, 2)] if current_rent_psf else [],
                "periods": ["Current"],
                "growth_rate": 0.0,  # Would need historical data
            },
        },
    }


@router.get("/market-data")
async def get_market_data(
    market: str = Query(..., description="Market name"),
    property_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get market-level data and comparisons.

    - **market**: Market name (e.g., "Phoenix Metro")
    - **property_type**: Filter by property type
    """
    # Build filters for market-specific property data
    market_filters = [func.lower(Property.market) == func.lower(market)]
    if property_type:
        market_filters.append(Property.property_type == property_type)

    # Query market metrics from our property data
    market_metrics_result = await db.execute(
        select(
            func.avg(Property.avg_rent_per_sf).label("avg_rent_psf"),
            func.avg(Property.cap_rate).label("avg_cap_rate"),
            func.avg(Property.occupancy_rate).label("avg_occupancy"),
            func.count(Property.id).label("property_count"),
            func.sum(Property.total_units).label("total_units"),
        ).where(*market_filters)
    )
    metrics_row = market_metrics_result.fetchone()

    # Check if we have data for this market
    property_count = metrics_row.property_count if metrics_row else 0

    # If no properties in market, return mock data as fallback
    if property_count == 0:
        return {
            "market": market,
            "property_type": property_type or "all",
            "data_source": "mock",
            "metrics": {
                "avg_rent_psf": 1.95,
                "avg_cap_rate": 5.5,
                "vacancy_rate": 6.2,
                "absorption_12m_units": 8500,
                "new_supply_12m_units": 6200,
                "rent_growth_12m": 4.5,
            },
            "economic_indicators": {
                "unemployment_rate": 3.8,
                "population_growth_yoy": 1.9,
                "job_growth_yoy": 2.1,
                "median_household_income": 72500,
            },
            "forecast": {
                "rent_growth_1y": 3.5,
                "rent_growth_3y": 3.0,
                "cap_rate_trend": "stable",
                "supply_risk": "moderate",
            },
        }

    # Calculate vacancy rate from occupancy
    avg_occupancy = _decimal_to_float(metrics_row.avg_occupancy) or 0
    vacancy_rate = 100 - avg_occupancy if avg_occupancy > 0 else None

    # Note: Economic indicators would come from external data sources
    # Placeholder for future market data integration (CoStar, RealPage, Census, BLS, etc.)
    # This is a placeholder that can be extended with real market data APIs
    economic_data = _get_market_economic_placeholder(market)

    return {
        "market": market,
        "property_type": property_type or "all",
        "data_source": "internal_portfolio",
        "metrics": {
            "avg_rent_psf": round(_decimal_to_float(metrics_row.avg_rent_psf) or 0, 2),
            "avg_cap_rate": round(_decimal_to_float(metrics_row.avg_cap_rate) or 0, 2),
            "vacancy_rate": round(vacancy_rate, 1)
            if vacancy_rate is not None
            else None,
            "property_count": property_count,
            "total_units": metrics_row.total_units or 0,
            # Placeholder: would need external data for market-wide metrics
            "absorption_12m_units": None,
            "new_supply_12m_units": None,
            "rent_growth_12m": None,
        },
        "economic_indicators": economic_data,
        "forecast": {
            "rent_growth_1y": None,  # Would need predictive model or external forecast
            "rent_growth_3y": None,
            "cap_rate_trend": "unknown",
            "supply_risk": "unknown",
        },
    }


def _get_market_economic_placeholder(market: str) -> dict:
    """
    Placeholder for market economic indicators.

    In production, this would integrate with external data sources:
    - Bureau of Labor Statistics (BLS) API for employment data
    - Census Bureau API for population and income data
    - CoStar/RealPage for real estate market data
    - State/local government data portals

    Args:
        market: Market name to look up

    Returns:
        Dictionary of economic indicators (currently returns None/placeholder values)
    """
    # Placeholder structure - would be populated from external APIs
    return {
        "unemployment_rate": None,  # BLS API integration placeholder
        "population_growth_yoy": None,  # Census API integration placeholder
        "job_growth_yoy": None,  # BLS API integration placeholder
        "median_household_income": None,  # Census API integration placeholder
        "data_source_note": "External market data integration pending",
    }


@router.post("/rent-prediction")
async def predict_rent_growth(
    property_data: dict,
    prediction_months: int = Query(12, ge=1, le=60),
):
    """
    Get ML-powered rent growth prediction for a property.

    - **property_data**: Property attributes for prediction
    - **prediction_months**: Forecast horizon in months (1-60)
    """
    predictor = await get_rent_growth_predictor()
    prediction = predictor.predict(property_data, prediction_months)

    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed",
        )

    return {
        "property_id": prediction.property_id,
        "current_rent": prediction.current_rent,
        "predicted_rent": prediction.predicted_rent,
        "predicted_growth_rate": prediction.predicted_growth_rate,
        "confidence_interval": {
            "lower": prediction.confidence_interval[0],
            "upper": prediction.confidence_interval[1],
        },
        "prediction_period_months": prediction.prediction_period_months,
        "model_version": prediction.model_version,
        "prediction_date": prediction.prediction_date,
    }


@router.post("/rent-prediction/batch")
async def predict_rent_growth_batch(
    properties: list[dict],
    prediction_months: int = Query(12, ge=1, le=60),
):
    """
    Get rent growth predictions for multiple properties.
    """
    predictor = await get_rent_growth_predictor()
    predictions = predictor.predict_batch(properties, prediction_months)

    return {
        "predictions": [
            {
                "property_id": p.property_id,
                "predicted_rent": p.predicted_rent,
                "predicted_growth_rate": p.predicted_growth_rate,
                "confidence_interval": {
                    "lower": p.confidence_interval[0],
                    "upper": p.confidence_interval[1],
                },
            }
            for p in predictions
        ],
        "count": len(predictions),
        "model_version": predictions[0].model_version if predictions else "unknown",
    }


@router.get("/deal-pipeline")
async def get_deal_pipeline_analytics(
    time_period: str = Query("ytd", pattern="^(mtd|qtd|ytd|1y|all)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get deal pipeline analytics and metrics.
    """
    # Get time period start date
    period_start = _get_time_period_start(time_period)

    # Query funnel counts by stage
    funnel_result = await db.execute(
        select(
            Deal.stage,
            func.count(Deal.id).label("count"),
        )
        .where(Deal.created_at >= period_start)
        .group_by(Deal.stage)
    )
    funnel_rows = funnel_result.fetchall()

    # Build funnel dict
    funnel = {stage.value: 0 for stage in DealStage}
    for row in funnel_rows:
        stage_value = row.stage.value if hasattr(row.stage, "value") else str(row.stage)
        funnel[stage_value] = row.count

    # Check if we have any deals
    total_deals = sum(funnel.values())

    # Return mock data if no deals exist
    if total_deals == 0:
        return {
            "time_period": time_period,
            "funnel": {
                "leads": 45,
                "initial_review": 28,
                "underwriting": 15,
                "due_diligence": 8,
                "loi_submitted": 4,
                "under_contract": 2,
                "closed": 5,
                "dead": 12,
            },
            "conversion_rates": {
                "lead_to_review": 62.2,
                "review_to_underwriting": 53.6,
                "underwriting_to_dd": 53.3,
                "dd_to_loi": 50.0,
                "loi_to_contract": 50.0,
                "contract_to_close": 71.4,
                "overall": 11.1,
            },
            "cycle_times_days": {
                "avg_lead_to_close": 95,
                "avg_underwriting": 14,
                "avg_due_diligence": 28,
                "avg_loi_to_close": 45,
            },
            "volume": {
                "total_reviewed": 73,
                "total_value_reviewed": 1250000000,
                "avg_deal_size": 17123288,
                "deals_closed": 5,
                "capital_deployed": 85000000,
            },
        }

    # Calculate conversion rates (deals that moved past each stage)
    # Count cumulative deals that reached each stage or beyond
    def calc_conversion(from_count: int, to_count: int) -> float:
        if from_count == 0:
            return 0.0
        return round((to_count / from_count) * 100, 1)

    leads = funnel.get("lead", 0)
    initial_review = funnel.get("initial_review", 0)
    underwriting = funnel.get("underwriting", 0)
    due_diligence = funnel.get("due_diligence", 0)
    loi_submitted = funnel.get("loi_submitted", 0)
    under_contract = funnel.get("under_contract", 0)
    closed = funnel.get("closed", 0)
    dead = funnel.get("dead", 0)

    # Cumulative counts for conversion calculation
    # (deals currently in or past each stage, excluding dead)
    past_lead = (
        initial_review
        + underwriting
        + due_diligence
        + loi_submitted
        + under_contract
        + closed
    )
    past_review = underwriting + due_diligence + loi_submitted + under_contract + closed
    past_underwriting = due_diligence + loi_submitted + under_contract + closed
    past_dd = loi_submitted + under_contract + closed
    past_loi = under_contract + closed
    past_contract = closed

    conversion_rates = {
        "lead_to_review": calc_conversion(leads + past_lead, past_lead),
        "review_to_underwriting": calc_conversion(
            initial_review + past_review, past_review
        ),
        "underwriting_to_dd": calc_conversion(
            underwriting + past_underwriting, past_underwriting
        ),
        "dd_to_loi": calc_conversion(due_diligence + past_dd, past_dd),
        "loi_to_contract": calc_conversion(loi_submitted + past_loi, past_loi),
        "contract_to_close": calc_conversion(
            under_contract + past_contract, past_contract
        ),
        "overall": calc_conversion(total_deals - dead, closed)
        if (total_deals - dead) > 0
        else 0.0,
    }

    # Query volume metrics
    volume_result = await db.execute(
        select(
            func.count(Deal.id).label("total_reviewed"),
            func.coalesce(func.sum(Deal.asking_price), 0).label("total_value_reviewed"),
        ).where(
            Deal.created_at >= period_start,
            Deal.stage != DealStage.LEAD,  # Exclude raw leads from "reviewed"
        )
    )
    volume_row = volume_result.fetchone()

    # Query closed deals metrics
    closed_result = await db.execute(
        select(
            func.count(Deal.id).label("deals_closed"),
            func.coalesce(func.sum(Deal.final_price), 0).label("capital_deployed"),
        ).where(
            Deal.stage == DealStage.CLOSED,
            Deal.actual_close_date >= period_start.date(),
        )
    )
    closed_row = closed_result.fetchone()

    total_reviewed = volume_row.total_reviewed if volume_row else 0
    total_value = (
        _decimal_to_float(volume_row.total_value_reviewed) if volume_row else 0
    )
    avg_deal_size = total_value / total_reviewed if total_reviewed > 0 else 0

    # Cycle time calculations would need tracking of stage transition timestamps
    # For now, returning placeholder values (would need stage history tracking)
    cycle_times = {
        "avg_lead_to_close": None,  # Would need stage transition history
        "avg_underwriting": None,
        "avg_due_diligence": None,
        "avg_loi_to_close": None,
    }

    return {
        "time_period": time_period,
        "funnel": funnel,
        "conversion_rates": conversion_rates,
        "cycle_times_days": cycle_times,
        "volume": {
            "total_reviewed": total_reviewed,
            "total_value_reviewed": total_value,
            "avg_deal_size": round(avg_deal_size, 0) if avg_deal_size else 0,
            "deals_closed": closed_row.deals_closed if closed_row else 0,
            "capital_deployed": _decimal_to_float(closed_row.capital_deployed)
            if closed_row
            else 0,
        },
    }
