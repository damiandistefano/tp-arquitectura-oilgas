"""Baseline del contrato: baseline_pred = prod_pet_lag_1 (persistencia)."""

from __future__ import annotations

import pandas as pd

from ml.config import BASELINE_FEATURE, TARGET_COLUMN
from ml.metrics import regression_metrics


def baseline_predictions(frame: pd.DataFrame) -> pd.Series:
    """Predicción ingenua: la producción del mes anterior."""
    return frame[BASELINE_FEATURE]


def evaluate_baseline(frame: pd.DataFrame) -> dict[str, float]:
    """Métricas del baseline sobre filas con target y lag_1 disponibles."""
    evaluable = frame.dropna(subset=[TARGET_COLUMN, BASELINE_FEATURE])
    if evaluable.empty:
        raise ValueError(
            "No hay filas evaluables para el baseline "
            f"(se necesitan {TARGET_COLUMN} y {BASELINE_FEATURE} no nulos)"
        )
    return regression_metrics(
        evaluable[TARGET_COLUMN], baseline_predictions(evaluable)
    )
