"""
Export endpoints for Excel and PDF generation.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import deal as deal_crud
from app.crud import property as property_crud
from app.db.session import get_db
from app.services.export_service import get_excel_service
from app.services.pdf_service import get_pdf_service

router = APIRouter()


@router.get("/properties/excel")
async def export_properties_excel(
    property_type: str | None = None,
    market: str | None = None,
    include_analytics: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Export properties to Excel format.

    - **property_type**: Filter by property type
    - **market**: Filter by market
    - **include_analytics**: Include analytics summary sheet (default: true)

    Returns a downloadable Excel file.
    """
    try:
        # Get properties from database
        properties = await property_crud.get_multi_filtered(
            db,
            property_type=property_type,
            market=market,
            limit=1000,
        )

        # Convert to dicts for export service
        filtered = []
        for prop in properties:
            filtered.append(
                {
                    "id": prop.id,
                    "name": prop.name,
                    "property_type": prop.property_type,
                    "address": prop.address,
                    "city": prop.city,
                    "state": prop.state,
                    "zip_code": prop.zip_code,
                    "market": prop.market,
                    "total_units": prop.total_units,
                    "total_sf": prop.total_sf,
                    "year_built": prop.year_built,
                    "occupancy_rate": (
                        float(prop.occupancy_rate) if prop.occupancy_rate else None
                    ),
                    "cap_rate": float(prop.cap_rate) if prop.cap_rate else None,
                    "noi": float(prop.noi) if prop.noi else None,
                }
            )

        if not filtered:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No properties match the specified criteria",
            )

        # Generate Excel file
        excel_service = get_excel_service()
        buffer = excel_service.export_properties(
            filtered, include_analytics=include_analytics
        )

        # Return as downloadable file
        filename = f"properties_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Excel export not available: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Excel export",
        ) from e


@router.get("/deals/excel")
async def export_deals_excel(
    stage: str | None = None,
    deal_type: str | None = None,
    include_pipeline: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Export deals to Excel format.

    - **stage**: Filter by deal stage
    - **deal_type**: Filter by deal type
    - **include_pipeline**: Include pipeline summary sheet (default: true)

    Returns a downloadable Excel file.
    """
    try:
        # Fetch deals from database
        deals = await deal_crud.get_multi_filtered(
            db,
            stage=stage,
            deal_type=deal_type,
            limit=1000,  # Export limit
        )

        if not deals:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No deals match the specified criteria",
            )

        # Convert SQLAlchemy models to dicts for export service
        filtered = []
        for deal in deals:
            filtered.append(
                {
                    "id": deal.id,
                    "name": deal.name,
                    "deal_type": deal.deal_type,
                    "stage": (
                        deal.stage.value
                        if hasattr(deal.stage, "value")
                        else str(deal.stage)
                    ),
                    "asking_price": (
                        float(deal.asking_price) if deal.asking_price else None
                    ),
                    "offer_price": (
                        float(deal.offer_price) if deal.offer_price else None
                    ),
                    "final_price": (
                        float(deal.final_price) if deal.final_price else None
                    ),
                    "projected_irr": (
                        float(deal.projected_irr) if deal.projected_irr else None
                    ),
                    "priority": deal.priority,
                    "created_at": (
                        deal.created_at.isoformat() if deal.created_at else None
                    ),
                }
            )

        # Generate Excel file
        excel_service = get_excel_service()
        buffer = excel_service.export_deals(filtered, include_pipeline=include_pipeline)

        # Return as downloadable file
        filename = f"deals_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Excel export not available: {str(e)}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Excel export",
        ) from e


@router.get("/analytics/excel")
async def export_analytics_excel(
    time_period: str = Query("ytd", pattern="^(mtd|qtd|ytd|1y|all)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export analytics report to Excel format.

    - **time_period**: Analysis period (mtd, qtd, ytd, 1y, all)

    Returns a downloadable Excel file with multiple sheets.
    """
    try:
        # Generate mock analytics data (same as analytics endpoint)
        dashboard_metrics = {
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
        }

        portfolio_analytics = {
            "time_period": time_period,
            "performance": {
                "total_return": 12.5,
                "income_return": 6.2,
                "appreciation_return": 6.3,
                "benchmark_return": 10.8,
                "alpha": 1.7,
            },
        }

        deal_pipeline = {
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
        }

        # Generate Excel file
        excel_service = get_excel_service()
        buffer = excel_service.export_analytics_report(
            dashboard_metrics,
            portfolio_analytics,
            deal_pipeline,
        )

        # Return as downloadable file
        filename = f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Excel export not available: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(f"Analytics Excel export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Excel export",
        ) from e


@router.get("/properties/{property_id}/pdf")
async def export_property_pdf(
    property_id: int,
    include_analytics: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a PDF report for a specific property.

    - **property_id**: Property ID
    - **include_analytics**: Include analytics data (default: true)

    Returns a downloadable PDF file.
    """
    try:
        # Get property from database
        prop = await property_crud.get(db, property_id)

        if not prop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {property_id} not found",
            )

        # Convert to dict for PDF service
        property_data = {
            "id": prop.id,
            "name": prop.name,
            "property_type": prop.property_type,
            "address": prop.address,
            "city": prop.city,
            "state": prop.state,
            "zip_code": prop.zip_code,
            "market": prop.market,
            "total_units": prop.total_units,
            "total_sf": prop.total_sf,
            "year_built": prop.year_built,
            "occupancy_rate": (
                float(prop.occupancy_rate) if prop.occupancy_rate else None
            ),
            "cap_rate": float(prop.cap_rate) if prop.cap_rate else None,
            "noi": float(prop.noi) if prop.noi else None,
        }

        # Get analytics if requested
        analytics = None
        if include_analytics:
            analytics = {
                "metrics": {
                    "ytd_rent_growth": 3.2,
                    "ytd_noi_growth": 4.1,
                    "avg_occupancy_12m": 95.2,
                    "rent_vs_market": 1.05,
                },
            }

        # Generate PDF
        pdf_service = get_pdf_service()
        buffer = pdf_service.generate_property_report(property_data, analytics)

        # Return as downloadable file
        filename = (
            f"property_report_{property_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"PDF generation not available: {str(e)}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Property PDF generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report",
        ) from e


@router.get("/deals/{deal_id}/pdf")
async def export_deal_pdf(
    deal_id: int,
    include_property: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a PDF report for a specific deal.

    - **deal_id**: Deal ID
    - **include_property**: Include associated property data (default: true)

    Returns a downloadable PDF file.
    """
    try:
        # Get deal from database
        deal = await deal_crud.get(db, deal_id)

        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deal {deal_id} not found",
            )

        # Convert to dict for PDF service
        deal_data = {
            "id": deal.id,
            "name": deal.name,
            "deal_type": deal.deal_type,
            "stage": (
                deal.stage.value if hasattr(deal.stage, "value") else str(deal.stage)
            ),
            "asking_price": float(deal.asking_price) if deal.asking_price else None,
            "offer_price": float(deal.offer_price) if deal.offer_price else None,
            "final_price": float(deal.final_price) if deal.final_price else None,
            "projected_irr": float(deal.projected_irr) if deal.projected_irr else None,
            "priority": deal.priority,
            "property_id": deal.property_id,
            "notes": deal.notes,
            "investment_thesis": deal.investment_thesis,
        }

        # Get associated property if requested
        property_data = None
        if include_property and deal.property_id:
            prop = await property_crud.get(db, deal.property_id)
            if prop:
                property_data = {
                    "id": prop.id,
                    "name": prop.name,
                    "property_type": prop.property_type,
                    "address": prop.address,
                    "city": prop.city,
                    "state": prop.state,
                    "market": prop.market,
                }

        # Generate PDF
        pdf_service = get_pdf_service()
        buffer = pdf_service.generate_deal_report(deal_data, property_data)

        # Return as downloadable file
        filename = f"deal_report_{deal_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"PDF generation not available: {str(e)}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deal PDF generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report",
        ) from e


@router.get("/portfolio/pdf")
async def export_portfolio_pdf(
    time_period: str = Query("ytd", pattern="^(mtd|qtd|ytd|1y|all)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a comprehensive portfolio PDF report.

    - **time_period**: Analysis period (mtd, qtd, ytd, 1y, all)

    Returns a downloadable PDF file with multiple sections.
    """
    try:
        # Get deals from database
        deals = await deal_crud.get_multi_filtered(db, limit=1000)
        deals_count = await deal_crud.count_filtered(db)

        # Convert deals to dicts for PDF service
        deals_data = []
        for deal in deals:
            deals_data.append(
                {
                    "id": deal.id,
                    "name": deal.name,
                    "deal_type": deal.deal_type,
                    "stage": (
                        deal.stage.value
                        if hasattr(deal.stage, "value")
                        else str(deal.stage)
                    ),
                    "asking_price": (
                        float(deal.asking_price) if deal.asking_price else None
                    ),
                    "priority": deal.priority,
                }
            )

        # Get analytics from database
        analytics_summary = await property_crud.get_analytics_summary(db)

        dashboard_metrics = {
            "portfolio_summary": {
                "total_properties": analytics_summary["total_properties"],
                "total_units": analytics_summary["total_units"] or 0,
                "total_sf": analytics_summary["total_sf"] or 0,
                "total_value": 425000000,
                "avg_occupancy": analytics_summary["avg_occupancy"] or 94.5,
                "avg_cap_rate": analytics_summary["avg_cap_rate"] or 5.8,
            },
            "kpis": {
                "ytd_noi_growth": 4.2,
                "ytd_rent_growth": 3.8,
                "deals_in_pipeline": deals_count,
                "deals_closed_ytd": 5,
                "capital_deployed_ytd": 85000000,
            },
        }

        portfolio_analytics = {
            "time_period": time_period,
            "performance": {
                "total_return": 12.5,
                "income_return": 6.2,
                "appreciation_return": 6.3,
                "benchmark_return": 10.8,
                "alpha": 1.7,
            },
        }

        # Get properties from database for report
        all_properties = await property_crud.get_multi_filtered(db, limit=1000)
        properties_data = []
        for prop in all_properties:
            properties_data.append(
                {
                    "id": prop.id,
                    "name": prop.name,
                    "property_type": prop.property_type,
                    "city": prop.city,
                    "state": prop.state,
                    "total_units": prop.total_units,
                    "total_sf": prop.total_sf,
                }
            )

        # Generate PDF
        pdf_service = get_pdf_service()
        buffer = pdf_service.generate_portfolio_report(
            dashboard_metrics,
            portfolio_analytics,
            properties_data,
            deals_data,
        )

        # Return as downloadable file
        filename = f"portfolio_report_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"PDF generation not available: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Portfolio PDF generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report",
        )
