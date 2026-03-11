"""
Shared service reference for market data sub-modules.

This module provides a single import point for market_data_service,
enabling consistent mock targeting in tests. Tests patch
``app.api.v1.endpoints.market_data._service.market_data_service``
or the re-exported ``app.api.v1.endpoints.market_data.market_data_service``.
"""

from app.services.market_data import market_data_service

__all__ = ["market_data_service"]
