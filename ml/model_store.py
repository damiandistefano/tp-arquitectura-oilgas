"""Artefactos locales de modelos y pointer de champion.

Es el fallback de sandbox visible del contrato: MLflow es la fuente
primaria cuando está disponible, pero training, gate y API siempre pueden
operar con `ml_artifacts/` (runs/<run_id>/ + champion.json).
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import joblib

from ml.config import get_champion_pointer_path, get_runs_dir


def run_dir(run_id: str) -> Path:
    return get_runs_dir() / run_id


def save_run_artifacts(run_id: str, model, run_info: dict) -> Path:
    directory = run_dir(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, directory / "model.pkl")
    (directory / "metrics.json").write_text(
        json.dumps(run_info, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (get_runs_dir().parent / "last_run_id.txt").write_text(run_id, encoding="utf-8")
    return directory


def load_run_info(run_id: str) -> dict:
    path = run_dir(run_id) / "metrics.json"
    if not path.exists():
        raise FileNotFoundError(f"No existe el run {run_id} en {path.parent}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_model(run_id: str):
    path = run_dir(run_id) / "model.pkl"
    if not path.exists():
        raise FileNotFoundError(f"No existe el modelo del run {run_id} en {path}")
    return joblib.load(path)


def read_champion_pointer() -> dict | None:
    path = get_champion_pointer_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_champion_pointer(
    run_id: str, reason: str, metrics: dict, previous: dict | None
) -> dict:
    pointer = {
        "run_id": run_id,
        "model_version": run_id,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "metrics": metrics,
        "previous_champion": previous["run_id"] if previous else None,
    }
    path = get_champion_pointer_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pointer, indent=2, ensure_ascii=False), encoding="utf-8")
    return pointer
