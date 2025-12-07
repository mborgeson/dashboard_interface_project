"""
Rent Growth Prediction Service using ML models.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass

from loguru import logger

from app.core.config import settings
from .model_manager import get_model_manager


@dataclass
class RentPrediction:
    """Container for rent growth predictions."""
    property_id: int
    current_rent: float
    predicted_rent: float
    predicted_growth_rate: float  # Percentage
    confidence_interval: Tuple[float, float]  # (lower, upper)
    prediction_period_months: int
    model_version: str
    prediction_date: str
    features_used: Dict[str, Any]


class RentGrowthPredictor:
    """
    ML-powered rent growth prediction service.

    Features:
    - Multiple model support (XGBoost, LightGBM, ensemble)
    - Feature engineering for real estate data
    - Confidence interval estimation
    - Batch prediction support
    - Caching of predictions
    """

    # Feature columns expected by the model
    FEATURE_COLUMNS = [
        "total_units",
        "year_built",
        "occupancy_rate",
        "property_type_encoded",
        "market_encoded",
        "avg_rent_current",
        "rent_per_sf",
        "unemployment_rate",
        "population_growth",
        "median_income",
        "new_supply_units",
        "historical_rent_growth_1y",
        "historical_rent_growth_3y",
        "cap_rate",
        "latitude",
        "longitude",
    ]

    # Property type encoding
    PROPERTY_TYPE_ENCODING = {
        "multifamily": 0,
        "office": 1,
        "retail": 2,
        "industrial": 3,
        "mixed_use": 4,
        "other": 5,
    }

    def __init__(self):
        self._model = None
        self._model_version = None
        self._model_manager = get_model_manager()
        self._feature_scaler = None

    async def initialize(self) -> bool:
        """Load model and prepare for predictions."""
        try:
            self._model = self._model_manager.load_model("rent_growth")
            if self._model:
                model_info = self._model_manager.get_model_info("rent_growth")
                self._model_version = model_info.get("latest_version", "unknown")
                logger.info(f"Rent growth model loaded: version {self._model_version}")
                return True
            else:
                logger.warning("No rent growth model found - predictions unavailable")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize rent growth predictor: {e}")
            return False

    def _prepare_features(self, property_data: dict) -> np.ndarray:
        """
        Prepare feature vector from property data.

        Args:
            property_data: Dictionary with property attributes

        Returns:
            Feature array for model input
        """
        features = []

        # Numeric features with defaults
        features.append(property_data.get("total_units", 100))
        features.append(property_data.get("year_built", 2000))
        features.append(property_data.get("occupancy_rate", 95.0))

        # Categorical encoding
        property_type = property_data.get("property_type", "multifamily").lower()
        features.append(self.PROPERTY_TYPE_ENCODING.get(property_type, 0))

        # Market encoding (simplified - in production would use proper encoding)
        market = property_data.get("market", "unknown")
        features.append(hash(market) % 100)  # Simple hash encoding

        # Financial features
        features.append(property_data.get("avg_rent_per_unit", 1500))
        features.append(property_data.get("avg_rent_per_sf", 2.0))

        # Economic indicators (would come from external data sources)
        features.append(property_data.get("unemployment_rate", 4.5))
        features.append(property_data.get("population_growth", 1.5))
        features.append(property_data.get("median_income", 65000))
        features.append(property_data.get("new_supply_units", 500))

        # Historical rent growth
        features.append(property_data.get("historical_rent_growth_1y", 3.0))
        features.append(property_data.get("historical_rent_growth_3y", 2.5))

        # Additional metrics
        features.append(property_data.get("cap_rate", 5.5))
        features.append(property_data.get("latitude", 33.4484))
        features.append(property_data.get("longitude", -112.0740))

        return np.array(features).reshape(1, -1)

    def predict(
        self,
        property_data: dict,
        prediction_months: int = 12
    ) -> Optional[RentPrediction]:
        """
        Predict rent growth for a single property.

        Args:
            property_data: Dictionary with property attributes
            prediction_months: Forecast horizon in months

        Returns:
            RentPrediction object or None if prediction fails
        """
        if self._model is None:
            # Return mock prediction if model not loaded
            return self._generate_mock_prediction(property_data, prediction_months)

        try:
            features = self._prepare_features(property_data)

            # Make prediction
            predicted_growth_rate = self._model.predict(features)[0]

            # Adjust for prediction period
            annual_growth = predicted_growth_rate
            period_growth = annual_growth * (prediction_months / 12)

            # Calculate confidence interval (simplified)
            confidence_margin = 0.02  # 2% margin
            lower_bound = period_growth - confidence_margin
            upper_bound = period_growth + confidence_margin

            current_rent = property_data.get("avg_rent_per_unit", 1500)
            predicted_rent = current_rent * (1 + period_growth / 100)

            return RentPrediction(
                property_id=property_data.get("id", 0),
                current_rent=current_rent,
                predicted_rent=round(predicted_rent, 2),
                predicted_growth_rate=round(period_growth, 2),
                confidence_interval=(round(lower_bound, 2), round(upper_bound, 2)),
                prediction_period_months=prediction_months,
                model_version=self._model_version or "unknown",
                prediction_date=datetime.now(timezone.utc).isoformat(),
                features_used={
                    col: features[0][i]
                    for i, col in enumerate(self.FEATURE_COLUMNS)
                },
            )

        except Exception as e:
            logger.error(f"Prediction failed for property {property_data.get('id')}: {e}")
            return None

    def _generate_mock_prediction(
        self,
        property_data: dict,
        prediction_months: int
    ) -> RentPrediction:
        """Generate a mock prediction when model is not available."""
        # Use simple heuristics for mock prediction
        base_growth = 3.0  # Base annual growth rate

        # Adjust based on occupancy
        occupancy = property_data.get("occupancy_rate", 95)
        if occupancy > 95:
            base_growth += 0.5
        elif occupancy < 90:
            base_growth -= 0.5

        # Adjust based on property age
        year_built = property_data.get("year_built", 2000)
        age = datetime.now().year - year_built
        if age < 10:
            base_growth += 0.3
        elif age > 30:
            base_growth -= 0.3

        # Scale to prediction period
        period_growth = base_growth * (prediction_months / 12)

        current_rent = property_data.get("avg_rent_per_unit", 1500)
        predicted_rent = current_rent * (1 + period_growth / 100)

        return RentPrediction(
            property_id=property_data.get("id", 0),
            current_rent=current_rent,
            predicted_rent=round(predicted_rent, 2),
            predicted_growth_rate=round(period_growth, 2),
            confidence_interval=(round(period_growth - 1.5, 2), round(period_growth + 1.5, 2)),
            prediction_period_months=prediction_months,
            model_version="mock_v1",
            prediction_date=datetime.now(timezone.utc).isoformat(),
            features_used={"mock": True},
        )

    def predict_batch(
        self,
        properties: List[dict],
        prediction_months: int = 12
    ) -> List[RentPrediction]:
        """
        Predict rent growth for multiple properties.

        Args:
            properties: List of property dictionaries
            prediction_months: Forecast horizon in months

        Returns:
            List of RentPrediction objects
        """
        predictions = []
        for prop in properties:
            prediction = self.predict(prop, prediction_months)
            if prediction:
                predictions.append(prediction)
        return predictions

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from the model."""
        if self._model is None:
            return None

        try:
            # Works for tree-based models (XGBoost, LightGBM)
            if hasattr(self._model, "feature_importances_"):
                importances = self._model.feature_importances_
                return dict(zip(self.FEATURE_COLUMNS, importances))
        except Exception as e:
            logger.error(f"Failed to get feature importance: {e}")

        return None


# Singleton instance
_predictor: Optional[RentGrowthPredictor] = None


async def get_rent_growth_predictor() -> RentGrowthPredictor:
    """Get or create RentGrowthPredictor singleton."""
    global _predictor
    if _predictor is None:
        _predictor = RentGrowthPredictor()
        await _predictor.initialize()
    return _predictor
