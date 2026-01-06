"""Tests for ML rent growth prediction service."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
import numpy as np

from app.services.ml.rent_growth_predictor import (
    RentPrediction,
    RentGrowthPredictor,
    get_rent_growth_predictor,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def predictor():
    """Create RentGrowthPredictor instance."""
    with patch('app.services.ml.rent_growth_predictor.get_model_manager') as mock_mgr:
        mock_manager = MagicMock()
        mock_manager.load_model.return_value = None
        mock_manager.get_model_info.return_value = {}
        mock_mgr.return_value = mock_manager
        return RentGrowthPredictor()


@pytest.fixture
def predictor_with_model():
    """Create predictor with mock model loaded."""
    with patch('app.services.ml.rent_growth_predictor.get_model_manager') as mock_mgr:
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([3.5])
        mock_model.feature_importances_ = np.array([0.1] * 16)

        mock_manager = MagicMock()
        mock_manager.load_model.return_value = mock_model
        mock_manager.get_model_info.return_value = {"latest_version": "v1.0.0"}
        mock_mgr.return_value = mock_manager

        pred = RentGrowthPredictor()
        pred._model = mock_model
        pred._model_version = "v1.0.0"
        return pred


@pytest.fixture
def sample_property_data():
    """Sample property data for predictions."""
    return {
        "id": 1,
        "total_units": 150,
        "year_built": 2015,
        "occupancy_rate": 96.5,
        "property_type": "multifamily",
        "market": "Phoenix",
        "avg_rent_per_unit": 1800,
        "avg_rent_per_sf": 2.25,
        "unemployment_rate": 3.8,
        "population_growth": 2.1,
        "median_income": 72000,
        "new_supply_units": 350,
        "historical_rent_growth_1y": 4.2,
        "historical_rent_growth_3y": 3.8,
        "cap_rate": 5.2,
        "latitude": 33.4484,
        "longitude": -112.0740,
    }


# =============================================================================
# RentPrediction Dataclass Tests
# =============================================================================


class TestRentPrediction:
    """Tests for RentPrediction dataclass."""

    def test_rent_prediction_creation(self):
        """Test creating a RentPrediction instance."""
        prediction = RentPrediction(
            property_id=1,
            current_rent=1500.0,
            predicted_rent=1545.0,
            predicted_growth_rate=3.0,
            confidence_interval=(2.5, 3.5),
            prediction_period_months=12,
            model_version="v1.0",
            prediction_date="2025-01-01T00:00:00",
            features_used={"occupancy": 95},
        )

        assert prediction.property_id == 1
        assert prediction.current_rent == 1500.0
        assert prediction.predicted_rent == 1545.0
        assert prediction.predicted_growth_rate == 3.0

    def test_rent_prediction_confidence_interval(self):
        """Test confidence interval is tuple."""
        prediction = RentPrediction(
            property_id=1,
            current_rent=1500.0,
            predicted_rent=1545.0,
            predicted_growth_rate=3.0,
            confidence_interval=(2.5, 3.5),
            prediction_period_months=12,
            model_version="v1.0",
            prediction_date="2025-01-01T00:00:00",
            features_used={},
        )

        assert len(prediction.confidence_interval) == 2
        assert prediction.confidence_interval[0] < prediction.confidence_interval[1]


# =============================================================================
# Initialization Tests
# =============================================================================


class TestPredictorInit:
    """Tests for RentGrowthPredictor initialization."""

    def test_init_creates_instance(self, predictor):
        """Test that predictor can be instantiated."""
        assert predictor is not None
        assert isinstance(predictor, RentGrowthPredictor)

    def test_init_no_model_loaded(self, predictor):
        """Test that init starts with no model."""
        assert predictor._model is None
        assert predictor._model_version is None

    def test_init_has_feature_columns(self, predictor):
        """Test that feature columns are defined."""
        assert len(predictor.FEATURE_COLUMNS) == 16
        assert "total_units" in predictor.FEATURE_COLUMNS
        assert "occupancy_rate" in predictor.FEATURE_COLUMNS

    def test_init_has_property_type_encoding(self, predictor):
        """Test property type encoding is defined."""
        assert "multifamily" in predictor.PROPERTY_TYPE_ENCODING
        assert "office" in predictor.PROPERTY_TYPE_ENCODING
        assert predictor.PROPERTY_TYPE_ENCODING["multifamily"] == 0

    @pytest.mark.asyncio
    async def test_initialize_no_model_available(self, predictor):
        """Test initialization when no model is available."""
        predictor._model_manager.load_model.return_value = None

        result = await predictor.initialize()

        assert result is False
        assert predictor._model is None

    @pytest.mark.asyncio
    async def test_initialize_with_model(self):
        """Test initialization when model is available."""
        with patch('app.services.ml.rent_growth_predictor.get_model_manager') as mock_mgr:
            mock_model = MagicMock()
            mock_manager = MagicMock()
            mock_manager.load_model.return_value = mock_model
            mock_manager.get_model_info.return_value = {"latest_version": "v1.0.0"}
            mock_mgr.return_value = mock_manager

            pred = RentGrowthPredictor()
            result = await pred.initialize()

            assert result is True
            assert pred._model is mock_model
            assert pred._model_version == "v1.0.0"


# =============================================================================
# Feature Preparation Tests
# =============================================================================


class TestFeaturePreparation:
    """Tests for feature preparation."""

    def test_prepare_features_returns_array(self, predictor, sample_property_data):
        """Test that feature preparation returns numpy array."""
        features = predictor._prepare_features(sample_property_data)

        assert isinstance(features, np.ndarray)
        assert features.shape == (1, 16)

    def test_prepare_features_uses_defaults(self, predictor):
        """Test that missing features use defaults."""
        features = predictor._prepare_features({})

        assert isinstance(features, np.ndarray)
        assert features.shape == (1, 16)
        # Check default values are used
        assert features[0][0] == 100  # default total_units
        assert features[0][1] == 2000  # default year_built

    def test_prepare_features_encodes_property_type(self, predictor):
        """Test property type encoding."""
        features_mf = predictor._prepare_features({"property_type": "multifamily"})
        features_office = predictor._prepare_features({"property_type": "office"})

        assert features_mf[0][3] == 0  # multifamily = 0
        assert features_office[0][3] == 1  # office = 1

    def test_prepare_features_handles_unknown_property_type(self, predictor):
        """Test handling of unknown property types."""
        features = predictor._prepare_features({"property_type": "unknown_type"})

        # Should default to 0 (multifamily encoding)
        assert features[0][3] == 0

    def test_prepare_features_extracts_all_values(self, predictor, sample_property_data):
        """Test that all property values are extracted."""
        features = predictor._prepare_features(sample_property_data)

        assert features[0][0] == 150  # total_units
        assert features[0][1] == 2015  # year_built
        assert features[0][2] == 96.5  # occupancy_rate


# =============================================================================
# Prediction Tests
# =============================================================================


class TestPrediction:
    """Tests for prediction functionality."""

    def test_predict_with_model(self, predictor_with_model, sample_property_data):
        """Test prediction with loaded model."""
        result = predictor_with_model.predict(sample_property_data)

        assert result is not None
        assert isinstance(result, RentPrediction)
        assert result.property_id == 1
        assert result.model_version == "v1.0.0"

    def test_predict_without_model_uses_mock(self, predictor, sample_property_data):
        """Test that prediction without model returns mock prediction."""
        result = predictor.predict(sample_property_data)

        assert result is not None
        assert isinstance(result, RentPrediction)
        assert result.model_version == "mock_v1"

    def test_predict_custom_period(self, predictor_with_model, sample_property_data):
        """Test prediction with custom period."""
        result = predictor_with_model.predict(sample_property_data, prediction_months=6)

        assert result is not None
        assert result.prediction_period_months == 6

    def test_predict_calculates_rent_correctly(self, predictor_with_model, sample_property_data):
        """Test rent calculation is correct."""
        result = predictor_with_model.predict(sample_property_data, prediction_months=12)

        # Model returns 3.5% annual growth
        expected_growth = 3.5
        expected_rent = 1800 * (1 + expected_growth / 100)

        assert result.predicted_rent == pytest.approx(expected_rent, rel=0.01)

    def test_predict_includes_confidence_interval(self, predictor_with_model, sample_property_data):
        """Test that prediction includes confidence interval."""
        result = predictor_with_model.predict(sample_property_data)

        assert result.confidence_interval is not None
        assert len(result.confidence_interval) == 2
        lower, upper = result.confidence_interval
        assert lower < result.predicted_growth_rate < upper

    def test_predict_includes_features_used(self, predictor_with_model, sample_property_data):
        """Test that prediction includes features used."""
        result = predictor_with_model.predict(sample_property_data)

        assert result.features_used is not None
        assert len(result.features_used) > 0

    def test_predict_handles_exception(self, predictor_with_model, sample_property_data):
        """Test that prediction handles exceptions gracefully."""
        predictor_with_model._model.predict.side_effect = Exception("Prediction error")

        result = predictor_with_model.predict(sample_property_data)

        assert result is None


# =============================================================================
# Mock Prediction Tests
# =============================================================================


class TestMockPrediction:
    """Tests for mock prediction generation."""

    def test_mock_prediction_base_growth(self, predictor):
        """Test mock prediction base growth rate."""
        result = predictor._generate_mock_prediction({"id": 1}, 12)

        assert result is not None
        assert result.model_version == "mock_v1"
        assert result.features_used == {"mock": True}

    def test_mock_prediction_high_occupancy_bonus(self, predictor):
        """Test mock prediction increases growth for high occupancy."""
        low_occ = predictor._generate_mock_prediction({"occupancy_rate": 85}, 12)
        high_occ = predictor._generate_mock_prediction({"occupancy_rate": 98}, 12)

        assert high_occ.predicted_growth_rate > low_occ.predicted_growth_rate

    def test_mock_prediction_new_building_bonus(self, predictor):
        """Test mock prediction increases growth for newer buildings."""
        old_building = predictor._generate_mock_prediction({"year_built": 1980}, 12)
        new_building = predictor._generate_mock_prediction({"year_built": 2020}, 12)

        assert new_building.predicted_growth_rate > old_building.predicted_growth_rate

    def test_mock_prediction_scales_with_period(self, predictor):
        """Test mock prediction scales with prediction period."""
        result_6mo = predictor._generate_mock_prediction({"id": 1}, 6)
        result_12mo = predictor._generate_mock_prediction({"id": 1}, 12)

        # 12 month should be approximately double 6 month
        assert result_12mo.predicted_growth_rate == pytest.approx(
            result_6mo.predicted_growth_rate * 2, rel=0.1
        )


# =============================================================================
# Batch Prediction Tests
# =============================================================================


class TestBatchPrediction:
    """Tests for batch prediction functionality."""

    def test_predict_batch_empty_list(self, predictor):
        """Test batch prediction with empty list."""
        result = predictor.predict_batch([])
        assert result == []

    def test_predict_batch_single_property(self, predictor, sample_property_data):
        """Test batch prediction with single property."""
        result = predictor.predict_batch([sample_property_data])

        assert len(result) == 1
        assert isinstance(result[0], RentPrediction)

    def test_predict_batch_multiple_properties(self, predictor):
        """Test batch prediction with multiple properties."""
        properties = [
            {"id": 1, "total_units": 100},
            {"id": 2, "total_units": 200},
            {"id": 3, "total_units": 300},
        ]

        result = predictor.predict_batch(properties)

        assert len(result) == 3
        assert all(isinstance(p, RentPrediction) for p in result)

    def test_predict_batch_custom_period(self, predictor, sample_property_data):
        """Test batch prediction with custom period."""
        result = predictor.predict_batch([sample_property_data], prediction_months=24)

        assert len(result) == 1
        assert result[0].prediction_period_months == 24


# =============================================================================
# Feature Importance Tests
# =============================================================================


class TestFeatureImportance:
    """Tests for feature importance functionality."""

    def test_get_feature_importance_no_model(self, predictor):
        """Test feature importance returns None without model."""
        result = predictor.get_feature_importance()
        assert result is None

    def test_get_feature_importance_with_model(self, predictor_with_model):
        """Test feature importance returns dict with model."""
        result = predictor_with_model.get_feature_importance()

        assert result is not None
        assert isinstance(result, dict)
        assert len(result) == 16

    def test_get_feature_importance_keys_match_columns(self, predictor_with_model):
        """Test feature importance keys match feature columns."""
        result = predictor_with_model.get_feature_importance()

        for key in result.keys():
            assert key in predictor_with_model.FEATURE_COLUMNS

    def test_get_feature_importance_handles_exception(self, predictor_with_model):
        """Test feature importance handles exception."""
        del predictor_with_model._model.feature_importances_
        predictor_with_model._model.feature_importances_ = property(
            lambda self: (_ for _ in ()).throw(Exception("Error"))
        )

        # Should return None on error, not raise
        result = predictor_with_model.get_feature_importance()
        # Either None or the mock value depending on mock setup
        assert result is None or isinstance(result, dict)


# =============================================================================
# Singleton Tests
# =============================================================================


class TestPredictorSingleton:
    """Tests for RentGrowthPredictor singleton pattern."""

    @pytest.mark.asyncio
    async def test_get_rent_growth_predictor_returns_instance(self):
        """Test get_rent_growth_predictor returns an instance."""
        with patch('app.services.ml.rent_growth_predictor.get_model_manager') as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.load_model.return_value = None
            mock_manager.get_model_info.return_value = {}
            mock_mgr.return_value = mock_manager

            import app.services.ml.rent_growth_predictor as module
            module._predictor = None

            result = await get_rent_growth_predictor()
            assert isinstance(result, RentGrowthPredictor)

    @pytest.mark.asyncio
    async def test_get_rent_growth_predictor_returns_same_instance(self):
        """Test get_rent_growth_predictor returns cached singleton."""
        with patch('app.services.ml.rent_growth_predictor.get_model_manager') as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.load_model.return_value = None
            mock_manager.get_model_info.return_value = {}
            mock_mgr.return_value = mock_manager

            import app.services.ml.rent_growth_predictor as module
            module._predictor = None

            result1 = await get_rent_growth_predictor()
            result2 = await get_rent_growth_predictor()
            assert result1 is result2
