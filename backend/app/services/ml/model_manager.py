"""
Model Manager for loading, saving, and managing ML models.
"""
import os
import json
import pickle
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, Dict

from loguru import logger

from app.core.config import settings


class ModelManager:
    """
    Manages ML model lifecycle including loading, saving, and versioning.

    Features:
    - Model persistence with versioning
    - Metadata tracking (training date, metrics, parameters)
    - Model registry for quick access
    - Automatic model selection based on performance
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path or settings.ML_MODEL_PATH)
        self._models: Dict[str, Any] = {}
        self._metadata: Dict[str, dict] = {}
        self._ensure_model_directory()

    def _ensure_model_directory(self) -> None:
        """Create model directory if it doesn't exist."""
        self.model_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Model directory: {self.model_path}")

    def _get_model_file_path(self, model_name: str, version: Optional[str] = None) -> Path:
        """Get path to model file."""
        if version:
            return self.model_path / f"{model_name}_v{version}.pkl"
        return self.model_path / f"{model_name}.pkl"

    def _get_metadata_path(self, model_name: str) -> Path:
        """Get path to model metadata file."""
        return self.model_path / f"{model_name}_metadata.json"

    def save_model(
        self,
        model: Any,
        model_name: str,
        metrics: Optional[dict] = None,
        parameters: Optional[dict] = None,
        version: Optional[str] = None,
    ) -> str:
        """
        Save a trained model with metadata.

        Args:
            model: The trained model object
            model_name: Name identifier for the model
            metrics: Performance metrics (e.g., MAE, RMSE, R2)
            parameters: Training parameters and hyperparameters
            version: Optional version string

        Returns:
            Path to saved model
        """
        version = version or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        model_path = self._get_model_file_path(model_name, version)

        try:
            # Save model
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            # Save/update metadata
            metadata = {
                "model_name": model_name,
                "version": version,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics or {},
                "parameters": parameters or {},
                "file_path": str(model_path),
            }

            # Update model registry
            metadata_path = self._get_metadata_path(model_name)
            existing_metadata = self._load_metadata(model_name)

            if "versions" not in existing_metadata:
                existing_metadata["versions"] = []

            existing_metadata["versions"].append(metadata)
            existing_metadata["latest_version"] = version
            existing_metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

            with open(metadata_path, "w") as f:
                json.dump(existing_metadata, f, indent=2)

            logger.info(f"Saved model {model_name} version {version}")
            return str(model_path)

        except Exception as e:
            logger.error(f"Failed to save model {model_name}: {e}")
            raise

    def load_model(
        self,
        model_name: str,
        version: Optional[str] = None
    ) -> Optional[Any]:
        """
        Load a model from disk.

        Args:
            model_name: Name identifier for the model
            version: Specific version to load (default: latest)

        Returns:
            Loaded model object or None if not found
        """
        # Check in-memory cache first
        cache_key = f"{model_name}_{version}" if version else model_name
        if cache_key in self._models:
            return self._models[cache_key]

        try:
            # Get version from metadata if not specified
            if not version:
                metadata = self._load_metadata(model_name)
                version = metadata.get("latest_version")

            if not version:
                logger.warning(f"No version found for model {model_name}")
                return None

            model_path = self._get_model_file_path(model_name, version)

            if not model_path.exists():
                logger.warning(f"Model file not found: {model_path}")
                return None

            with open(model_path, "rb") as f:
                model = pickle.load(f)

            # Cache the model
            self._models[cache_key] = model
            logger.info(f"Loaded model {model_name} version {version}")

            return model

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return None

    def _load_metadata(self, model_name: str) -> dict:
        """Load model metadata from disk."""
        metadata_path = self._get_metadata_path(model_name)

        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata for {model_name}: {e}")

        return {}

    def get_model_info(self, model_name: str) -> Optional[dict]:
        """Get information about a model including all versions."""
        return self._load_metadata(model_name) or None

    def list_models(self) -> list[dict]:
        """List all available models with their metadata."""
        models = []
        for metadata_file in self.model_path.glob("*_metadata.json"):
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    models.append({
                        "name": metadata_file.stem.replace("_metadata", ""),
                        "latest_version": metadata.get("latest_version"),
                        "version_count": len(metadata.get("versions", [])),
                        "updated_at": metadata.get("updated_at"),
                    })
            except Exception as e:
                logger.error(f"Failed to read metadata {metadata_file}: {e}")

        return models

    def delete_model(
        self,
        model_name: str,
        version: Optional[str] = None
    ) -> bool:
        """
        Delete a model or specific version.

        Args:
            model_name: Name of the model
            version: Specific version to delete (None = delete all versions)
        """
        try:
            if version:
                # Delete specific version
                model_path = self._get_model_file_path(model_name, version)
                if model_path.exists():
                    os.remove(model_path)

                # Update metadata
                metadata = self._load_metadata(model_name)
                if "versions" in metadata:
                    metadata["versions"] = [
                        v for v in metadata["versions"]
                        if v.get("version") != version
                    ]
                    if metadata["versions"]:
                        metadata["latest_version"] = metadata["versions"][-1]["version"]
                    else:
                        metadata["latest_version"] = None

                    with open(self._get_metadata_path(model_name), "w") as f:
                        json.dump(metadata, f, indent=2)

            else:
                # Delete all versions
                for model_file in self.model_path.glob(f"{model_name}*.pkl"):
                    os.remove(model_file)

                metadata_path = self._get_metadata_path(model_name)
                if metadata_path.exists():
                    os.remove(metadata_path)

            # Clear from cache
            keys_to_remove = [k for k in self._models if k.startswith(model_name)]
            for key in keys_to_remove:
                del self._models[key]

            logger.info(f"Deleted model {model_name} version {version or 'all'}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear in-memory model cache."""
        self._models.clear()
        self._metadata.clear()
        logger.info("Model cache cleared")


# Singleton instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get or create ModelManager singleton."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
