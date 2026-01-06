"""Tests for ML model manager service."""
import json
import pickle
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import shutil

from app.services.ml.model_manager import ModelManager, get_model_manager


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_model_dir():
    """Create a temporary directory for model tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def model_manager(temp_model_dir):
    """Create ModelManager with temporary directory."""
    return ModelManager(model_path=temp_model_dir)


class SimpleModel:
    """Simple picklable model class for testing."""
    def __init__(self, value=3.5):
        self.value = value

    def predict(self, X):
        return [self.value]


@pytest.fixture
def mock_model():
    """Create a simple model object that can be pickled."""
    return SimpleModel(value=3.5)


# =============================================================================
# Initialization Tests
# =============================================================================


class TestModelManagerInit:
    """Tests for ModelManager initialization."""

    def test_init_creates_instance(self, model_manager):
        """Test that ModelManager can be instantiated."""
        assert model_manager is not None
        assert isinstance(model_manager, ModelManager)

    def test_init_creates_model_directory(self, temp_model_dir):
        """Test that init creates the model directory."""
        # Create manager with non-existent subdir
        model_path = Path(temp_model_dir) / "models"
        manager = ModelManager(model_path=str(model_path))
        assert model_path.exists()

    def test_init_with_default_path(self):
        """Test initialization with default path from settings."""
        with patch('app.services.ml.model_manager.settings') as mock_settings:
            mock_settings.ML_MODEL_PATH = "/tmp/test_models"
            with patch.object(Path, 'mkdir'):
                manager = ModelManager()
                assert str(manager.model_path) == "/tmp/test_models"

    def test_init_empty_cache(self, model_manager):
        """Test that init starts with empty caches."""
        assert model_manager._models == {}
        assert model_manager._metadata == {}


# =============================================================================
# Path Generation Tests
# =============================================================================


class TestPathGeneration:
    """Tests for model file path generation."""

    def test_get_model_file_path_no_version(self, model_manager):
        """Test model file path without version."""
        path = model_manager._get_model_file_path("test_model")
        assert path.name == "test_model.pkl"

    def test_get_model_file_path_with_version(self, model_manager):
        """Test model file path with version."""
        path = model_manager._get_model_file_path("test_model", "20250101_120000")
        assert path.name == "test_model_v20250101_120000.pkl"

    def test_get_metadata_path(self, model_manager):
        """Test metadata file path generation."""
        path = model_manager._get_metadata_path("test_model")
        assert path.name == "test_model_metadata.json"


# =============================================================================
# Save Model Tests
# =============================================================================


class TestSaveModel:
    """Tests for model saving functionality."""

    def test_save_model_success(self, model_manager, mock_model):
        """Test successful model saving."""
        result = model_manager.save_model(
            model=mock_model,
            model_name="test_model",
            metrics={"mae": 0.1, "rmse": 0.15},
            parameters={"learning_rate": 0.01}
        )

        assert result is not None
        assert "test_model" in result
        assert Path(result).exists()

    def test_save_model_creates_metadata(self, model_manager, mock_model):
        """Test that saving model creates metadata file."""
        model_manager.save_model(
            model=mock_model,
            model_name="test_model"
        )

        metadata_path = model_manager._get_metadata_path("test_model")
        assert metadata_path.exists()

        with open(metadata_path) as f:
            metadata = json.load(f)

        assert "latest_version" in metadata
        assert "versions" in metadata
        assert len(metadata["versions"]) == 1

    def test_save_model_with_custom_version(self, model_manager, mock_model):
        """Test saving model with custom version string."""
        result = model_manager.save_model(
            model=mock_model,
            model_name="test_model",
            version="v1.0.0"
        )

        assert "v1.0.0" in result

    def test_save_model_multiple_versions(self, model_manager, mock_model):
        """Test saving multiple versions of same model."""
        model_manager.save_model(mock_model, "test_model", version="v1")
        model_manager.save_model(mock_model, "test_model", version="v2")
        model_manager.save_model(mock_model, "test_model", version="v3")

        metadata_path = model_manager._get_metadata_path("test_model")
        with open(metadata_path) as f:
            metadata = json.load(f)

        assert len(metadata["versions"]) == 3
        assert metadata["latest_version"] == "v3"

    def test_save_model_with_metrics(self, model_manager, mock_model):
        """Test that metrics are saved in metadata."""
        metrics = {"accuracy": 0.95, "f1_score": 0.92}
        model_manager.save_model(
            mock_model,
            "test_model",
            metrics=metrics,
            version="v1"
        )

        metadata = model_manager._load_metadata("test_model")
        assert metadata["versions"][0]["metrics"] == metrics

    def test_save_model_with_parameters(self, model_manager, mock_model):
        """Test that parameters are saved in metadata."""
        parameters = {"epochs": 100, "batch_size": 32}
        model_manager.save_model(
            mock_model,
            "test_model",
            parameters=parameters,
            version="v1"
        )

        metadata = model_manager._load_metadata("test_model")
        assert metadata["versions"][0]["parameters"] == parameters

    def test_save_model_pickles_correctly(self, model_manager, mock_model):
        """Test that model is properly pickled."""
        model_manager.save_model(mock_model, "test_model", version="v1")

        model_path = model_manager._get_model_file_path("test_model", "v1")
        with open(model_path, "rb") as f:
            loaded = pickle.load(f)

        # Verify it's the same type of object
        assert hasattr(loaded, "predict")


# =============================================================================
# Load Model Tests
# =============================================================================


class TestLoadModel:
    """Tests for model loading functionality."""

    def test_load_model_success(self, model_manager, mock_model):
        """Test successful model loading."""
        model_manager.save_model(mock_model, "test_model", version="v1")

        loaded = model_manager.load_model("test_model", "v1")
        assert loaded is not None
        assert hasattr(loaded, "predict")

    def test_load_model_latest_version(self, model_manager, mock_model):
        """Test loading latest version when no version specified."""
        model_manager.save_model(mock_model, "test_model", version="v1")
        model_manager.save_model(mock_model, "test_model", version="v2")

        # Clear cache to force reload
        model_manager.clear_cache()

        loaded = model_manager.load_model("test_model")
        assert loaded is not None

    def test_load_model_uses_cache(self, model_manager, mock_model):
        """Test that subsequent loads use cache."""
        model_manager.save_model(mock_model, "test_model", version="v1")

        # First load
        loaded1 = model_manager.load_model("test_model", "v1")
        # Second load (should use cache)
        loaded2 = model_manager.load_model("test_model", "v1")

        assert loaded1 is loaded2

    def test_load_model_not_found(self, model_manager):
        """Test loading non-existent model returns None."""
        result = model_manager.load_model("nonexistent_model")
        assert result is None

    def test_load_model_no_version_found(self, model_manager):
        """Test loading model with no versions returns None."""
        # Create empty metadata file
        metadata_path = model_manager._get_metadata_path("empty_model")
        with open(metadata_path, "w") as f:
            json.dump({}, f)

        result = model_manager.load_model("empty_model")
        assert result is None

    def test_load_model_file_missing(self, model_manager, mock_model):
        """Test loading when model file is missing returns None."""
        # Save model and then delete the file
        model_manager.save_model(mock_model, "test_model", version="v1")
        model_path = model_manager._get_model_file_path("test_model", "v1")
        model_path.unlink()
        model_manager.clear_cache()

        result = model_manager.load_model("test_model", "v1")
        assert result is None


# =============================================================================
# Metadata Tests
# =============================================================================


class TestMetadata:
    """Tests for metadata loading and model info."""

    def test_load_metadata_existing(self, model_manager, mock_model):
        """Test loading existing metadata."""
        model_manager.save_model(mock_model, "test_model", version="v1")

        metadata = model_manager._load_metadata("test_model")
        assert metadata is not None
        assert "versions" in metadata

    def test_load_metadata_nonexistent(self, model_manager):
        """Test loading metadata for non-existent model."""
        metadata = model_manager._load_metadata("nonexistent")
        assert metadata == {}

    def test_get_model_info(self, model_manager, mock_model):
        """Test getting model info."""
        model_manager.save_model(
            mock_model,
            "test_model",
            metrics={"accuracy": 0.95},
            version="v1"
        )

        info = model_manager.get_model_info("test_model")
        assert info is not None
        assert "versions" in info
        assert "latest_version" in info

    def test_get_model_info_nonexistent(self, model_manager):
        """Test getting info for non-existent model returns None."""
        info = model_manager.get_model_info("nonexistent")
        assert info is None


# =============================================================================
# List Models Tests
# =============================================================================


class TestListModels:
    """Tests for listing available models."""

    def test_list_models_empty(self, model_manager):
        """Test listing models when none exist."""
        models = model_manager.list_models()
        assert models == []

    def test_list_models_single(self, model_manager, mock_model):
        """Test listing single model."""
        model_manager.save_model(mock_model, "model_a", version="v1")

        models = model_manager.list_models()
        assert len(models) == 1
        assert models[0]["name"] == "model_a"

    def test_list_models_multiple(self, model_manager, mock_model):
        """Test listing multiple models."""
        model_manager.save_model(mock_model, "model_a", version="v1")
        model_manager.save_model(mock_model, "model_b", version="v1")
        model_manager.save_model(mock_model, "model_c", version="v1")

        models = model_manager.list_models()
        assert len(models) == 3
        names = [m["name"] for m in models]
        assert "model_a" in names
        assert "model_b" in names
        assert "model_c" in names

    def test_list_models_shows_version_count(self, model_manager, mock_model):
        """Test that list shows correct version count."""
        model_manager.save_model(mock_model, "model_a", version="v1")
        model_manager.save_model(mock_model, "model_a", version="v2")
        model_manager.save_model(mock_model, "model_a", version="v3")

        models = model_manager.list_models()
        assert models[0]["version_count"] == 3


# =============================================================================
# Delete Model Tests
# =============================================================================


class TestDeleteModel:
    """Tests for model deletion."""

    def test_delete_model_specific_version(self, model_manager, mock_model):
        """Test deleting specific model version."""
        model_manager.save_model(mock_model, "test_model", version="v1")
        model_manager.save_model(mock_model, "test_model", version="v2")

        result = model_manager.delete_model("test_model", "v1")
        assert result is True

        # Check v1 file is deleted
        v1_path = model_manager._get_model_file_path("test_model", "v1")
        assert not v1_path.exists()

        # Check v2 still exists
        v2_path = model_manager._get_model_file_path("test_model", "v2")
        assert v2_path.exists()

    def test_delete_model_all_versions(self, model_manager, mock_model):
        """Test deleting all versions of a model."""
        model_manager.save_model(mock_model, "test_model", version="v1")
        model_manager.save_model(mock_model, "test_model", version="v2")

        result = model_manager.delete_model("test_model")
        assert result is True

        # Check all files are deleted
        v1_path = model_manager._get_model_file_path("test_model", "v1")
        v2_path = model_manager._get_model_file_path("test_model", "v2")
        metadata_path = model_manager._get_metadata_path("test_model")

        assert not v1_path.exists()
        assert not v2_path.exists()
        assert not metadata_path.exists()

    def test_delete_model_clears_cache(self, model_manager, mock_model):
        """Test that delete clears model from cache."""
        model_manager.save_model(mock_model, "test_model", version="v1")
        model_manager.load_model("test_model", "v1")  # Load to cache

        assert len(model_manager._models) > 0

        model_manager.delete_model("test_model")

        # Cache should be cleared for this model
        assert not any(k.startswith("test_model") for k in model_manager._models)

    def test_delete_model_updates_latest_version(self, model_manager, mock_model):
        """Test that deleting version updates latest version."""
        model_manager.save_model(mock_model, "test_model", version="v1")
        model_manager.save_model(mock_model, "test_model", version="v2")

        model_manager.delete_model("test_model", "v2")

        metadata = model_manager._load_metadata("test_model")
        assert metadata["latest_version"] == "v1"


# =============================================================================
# Cache Tests
# =============================================================================


class TestCache:
    """Tests for cache functionality."""

    def test_clear_cache(self, model_manager, mock_model):
        """Test clearing the model cache."""
        model_manager.save_model(mock_model, "test_model", version="v1")
        model_manager.load_model("test_model", "v1")

        assert len(model_manager._models) > 0

        model_manager.clear_cache()

        assert model_manager._models == {}
        assert model_manager._metadata == {}


# =============================================================================
# Singleton Tests
# =============================================================================


class TestModelManagerSingleton:
    """Tests for ModelManager singleton pattern."""

    def test_get_model_manager_returns_instance(self):
        """Test get_model_manager returns an instance."""
        with patch('app.services.ml.model_manager.settings') as mock_settings:
            mock_settings.ML_MODEL_PATH = "/tmp/test_models"
            with patch.object(Path, 'mkdir'):
                import app.services.ml.model_manager as module
                module._model_manager = None

                manager = get_model_manager()
                assert isinstance(manager, ModelManager)

    def test_get_model_manager_returns_same_instance(self):
        """Test get_model_manager returns cached singleton."""
        with patch('app.services.ml.model_manager.settings') as mock_settings:
            mock_settings.ML_MODEL_PATH = "/tmp/test_models"
            with patch.object(Path, 'mkdir'):
                import app.services.ml.model_manager as module
                module._model_manager = None

                manager1 = get_model_manager()
                manager2 = get_model_manager()
                assert manager1 is manager2
