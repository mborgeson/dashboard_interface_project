"""Machine Learning services for analytics and predictions."""

from .model_manager import ModelManager, get_model_manager
from .rent_growth_predictor import RentGrowthPredictor, get_rent_growth_predictor

__all__ = [
    "RentGrowthPredictor",
    "get_rent_growth_predictor",
    "ModelManager",
    "get_model_manager",
]
