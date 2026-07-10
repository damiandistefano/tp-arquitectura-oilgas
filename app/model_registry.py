"""Adapter entre la API y el registry/artifacts de modelos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_MODEL_NAME = "oilgas_forecaster"
DEFAULT_MODEL_ALIAS = "champion"
SOURCE_MLFLOW = "mlflow"
SOURCE_LOCAL_FALLBACK = "local_fallback"


class ModelRegistryError(Exception):
    """Error base del adapter de modelos."""


class ModelUnavailableError(ModelRegistryError):
    """No hay modelo activo disponible para servir predicciones."""


@dataclass(frozen=True)
class ModelMetadata:
    name: str
    version: str
    alias: str
    run_id: str
    source: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "alias": self.alias,
            "run_id": self.run_id,
            "source": self.source,
        }


@dataclass(frozen=True)
class ActiveModel:
    model: Any
    metadata: ModelMetadata


class LocalFallbackForecaster:
    """Fallback local simple y explícito para sandbox/demo."""

    def predict(self, rows: list[dict[str, Any]]) -> list[float]:
        predictions = []
        for row in rows:
            prediction = _first_number(
                row.get("prod_pet_lag_1"),
                row.get("prod_pet_roll_mean_3"),
                row.get("prod_pet_lag_2"),
                row.get("prod_pet_lag_3"),
            )
            predictions.append(round(prediction, 2))
        return predictions


def _first_number(*values: Any) -> float:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _model_name() -> str:
    return os.getenv("MLFLOW_MODEL_NAME", DEFAULT_MODEL_NAME)


def _model_alias() -> str:
    return os.getenv("MLFLOW_MODEL_ALIAS", DEFAULT_MODEL_ALIAS)


def _tracking_uri() -> str | None:
    return os.getenv("MLFLOW_TRACKING_URI") or None


def _fallback_enabled() -> bool:
    return os.getenv("LOCAL_MODEL_FALLBACK_ENABLED", "true").lower() not in {
        "0",
        "false",
        "no",
    }


def _artifacts_dir() -> Path:
    return Path(os.getenv("ML_ARTIFACTS_DIR", "ml_artifacts"))


def _champion_pointer_path() -> Path:
    return _artifacts_dir() / "champion.json"


def _configured_fallback_path() -> Path | None:
    value = os.getenv("LOCAL_MODEL_FALLBACK_PATH")
    return Path(value) if value else None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _runtime_digest(path: Path | None = None) -> tuple[str, str]:
    hasher = hashlib.sha256()
    source = path or Path(__file__)
    if source.exists() and source.is_file():
        hasher.update(source.read_bytes())
        stat = source.stat()
        version_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    else:
        hasher.update(str(source).encode("utf-8"))
        version_time = datetime.now(timezone.utc)
    digest = hasher.hexdigest()[:12]
    version = f"local-{version_time:%Y%m%d%H%M%S}-{digest[:8]}"
    run_id = f"local_fallback_{digest}"
    return version, run_id


def _metadata(
    *,
    version: str,
    run_id: str,
    source: str,
    name: str | None = None,
    alias: str | None = None,
) -> ModelMetadata:
    return ModelMetadata(
        name=name or _model_name(),
        version="" if version is None else str(version),
        alias=alias or _model_alias(),
        run_id="" if run_id is None else str(run_id),
        source=source,
    )


def _load_from_mlflow() -> ActiveModel | None:
    tracking_uri = _tracking_uri()
    if not tracking_uri:
        return None

    try:
        import mlflow  # noqa: PLC0415
    except ImportError:
        return None

    model_name = _model_name()
    alias = _model_alias()
    try:
        client = mlflow.MlflowClient(tracking_uri=tracking_uri)
        model_version = client.get_model_version_by_alias(model_name, alias)
        model = mlflow.pyfunc.load_model(f"models:/{model_name}@{alias}")
    except Exception:
        return None

    return ActiveModel(
        model=model,
        metadata=_metadata(
            name=model_name,
            alias=alias,
            version=getattr(model_version, "version", None),
            run_id=getattr(model_version, "run_id", None),
            source=SOURCE_MLFLOW,
        ),
    )


def _load_joblib_model(path: Path):
    try:
        import joblib  # noqa: PLC0415
    except ImportError as exc:
        raise ModelUnavailableError(
            "El fallback local requiere joblib para cargar artifacts pickle"
        ) from exc
    return joblib.load(path)


def _metadata_from_artifact(path: Path, model_info: dict[str, Any] | None = None) -> ModelMetadata:
    model_info = model_info or {}
    version, run_id = _runtime_digest(path)
    return _metadata(
        version=(
            model_info.get("model_version")
            or model_info.get("version")
            or model_info.get("run_id")
            or version
        ),
        run_id=model_info.get("run_id") or run_id,
        source=SOURCE_LOCAL_FALLBACK,
    )


def _load_from_configured_fallback(path: Path) -> ActiveModel | None:
    if not path.exists():
        return None

    if path.suffix.lower() == ".json":
        info = _read_json(path)
        return ActiveModel(
            model=LocalFallbackForecaster(),
            metadata=_metadata_from_artifact(path, info),
        )

    model = _load_joblib_model(path)
    info_path = path.with_name("metrics.json")
    info = _read_json(info_path) if info_path.exists() else {}
    return ActiveModel(model=model, metadata=_metadata_from_artifact(path, info))


def _load_from_champion_pointer() -> ActiveModel | None:
    pointer_path = _champion_pointer_path()
    if not pointer_path.exists():
        return None

    pointer = _read_json(pointer_path)
    run_id = pointer.get("run_id")
    if not run_id:
        return None

    run_dir = _artifacts_dir() / "runs" / str(run_id)
    model_path = run_dir / "model.pkl"
    if not model_path.exists():
        return None

    info_path = run_dir / "metrics.json"
    info = _read_json(info_path) if info_path.exists() else {}
    model_info = {**info, **pointer, "run_id": run_id}
    return ActiveModel(
        model=_load_joblib_model(model_path),
        metadata=_metadata_from_artifact(model_path, model_info),
    )


def _load_builtin_fallback() -> ActiveModel:
    version, run_id = _runtime_digest()
    return ActiveModel(
        model=LocalFallbackForecaster(),
        metadata=_metadata(
            version=version,
            run_id=run_id,
            source=SOURCE_LOCAL_FALLBACK,
        ),
    )


def _load_from_local_fallback() -> ActiveModel | None:
    if not _fallback_enabled():
        return None

    configured_path = _configured_fallback_path()
    if configured_path:
        configured = _load_from_configured_fallback(configured_path)
        if configured:
            return configured

    champion = _load_from_champion_pointer()
    if champion:
        return champion

    return _load_builtin_fallback()


def get_active_model() -> ActiveModel:
    active = _load_from_mlflow() or _load_from_local_fallback()
    if active is None:
        raise ModelUnavailableError(
            "No hay modelo activo disponible: MLflow no respondió y no hay fallback local"
        )

    if not active.metadata.version or not active.metadata.run_id:
        raise ModelUnavailableError(
            "El modelo activo no expone version/run_id de runtime"
        )
    return active


def get_active_model_metadata() -> ModelMetadata:
    return get_active_model().metadata


def load_model():
    return get_active_model().model
