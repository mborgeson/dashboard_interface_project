"""
Export endpoints for Excel and PDF generation.
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.services.export_service import get_excel_service
from app.services.pdf_service import get_pdf_service

router = APIRouter()

# Demo data imports (same as other endpoints for consistency)
from app.api.v1.endpoints.properties import DEMO_PROPERTIES
from app.api.v1.endpoints.deals import DEMO_DEALS


@router.get("/properties/excel")
async def export_properties_excel(
    property_type: Optional[str] = None,
    market: Optional[str] = None,
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
        # Filter properties
        filtered = DEMO_PROPERTIES.copy()

        if property_type:
            filtered = [p for p in filtered if p["property_type"] == property_type]
        if market:
            filtered = [p for p in filtered if p.get("market", "").lower() == market.lower()]

        if not filtered:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No properties match the specified criteria",
            )

        # Generate Excel file
        excel_service = get_excel_service()
        buffer = excel_service.export_properties(filtered, include_analytics=include_analytics)

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
        )
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Excel export",
        )


@router.get("/deals/excel")
async def export_deals_excel(
    stage: Optional[str] = None,
    deal_type: Optional[str] = None,
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
        # Filter deals
        filtered = DEMO_DEALS.copy()

        if stage:
            filtered = [d for d in filtered if d["stage"] == stage]
        if deal_type:
            filtered = [d for d in filtered if d["deal_type"] == deal_type]

        if not filtered:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No deals match the specified criteria",
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
        )
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Excel export",
        )


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
        )
    except Exception as e:
        logger.error(f"Analytics Excel export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Excel export",
        )


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
        # Find property
        property_data = next(
            (p for p in DEMO_PROPERTIES if p["id"] == property_id),
            None,
        )

        if not property_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {property_id} not found",
            )

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
        filename = f"property_report_{property_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Property PDF generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report",
        )


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
        # Find deal
        deal_data = next(
            (d for d in DEMO_DEALS if d["id"] == deal_id),
            None,
        )

        if not deal_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deal {deal_id} not found",
            )

        # Get associated property if requested
        property_data = None
        if include_property and deal_data.get("property_id"):
            property_data = next(
                (p for p in DEMO_PROPERTIES if p["id"] == deal_data.get("property_id")),
                None,
            )

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
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deal PDF generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report",
        )


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
        # Generate mock analytics data
        dashboard_metrics = {
            "portfolio_summary": {
                "total_properties": len(DEMO_PROPERTIES),
                "total_units": sum(p.get("total_units", 0) or 0 for p in DEMO_PROPERTIES),
                "total_sf": sum(p.get("total_sf", 0) or 0 for p in DEMO_PROPERTIES),
                "total_value": 425000000,
                "avg_occupancy": 94.5,
                "avg_cap_rate": 5.8,
            },
            "kpis": {
                "ytd_noi_growth": 4.2,
                "ytd_rent_growth": 3.8,
                "deals_in_pipeline": len(DEMO_DEALS),
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

        # Generate PDF
        pdf_service = get_pdf_service()
        buffer = pdf_service.generate_portfolio_report(
            dashboard_metrics,
            portfolio_analytics,
            DEMO_PROPERTIES,
            DEMO_DEALS,
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
