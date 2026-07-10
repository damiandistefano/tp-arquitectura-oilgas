"""Estadísticas de referencia de features del set de entrenamiento.

Se calculan dentro del mismo run de training (mitiga el riesgo de "drift
script muerto"): siempre que hay un modelo candidato, hay referencia para
el drift check del Integrante 3.
"""

from __future__ import annotations

import math

import pandas as pd

from ml.config import NUMERIC_FEATURES


def _clean(value: float) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def compute_reference_stats(
    train_frame: pd.DataFrame, training_run_id: str
) -> list[dict]:
    """Una fila de stats por feature numérica del set de entrenamiento."""
    rows = []
    total = len(train_frame)
    for feature_name in NUMERIC_FEATURES:
        series = pd.to_numeric(train_frame[feature_name], errors="coerce")
        non_null = series.dropna()
        rows.append(
            {
                "training_run_id": training_run_id,
                "feature_name": feature_name,
                "stat_count": int(non_null.count()),
                "mean": _clean(non_null.mean()),
                "std": _clean(non_null.std()),
                "min": _clean(non_null.min()),
                "p25": _clean(non_null.quantile(0.25)),
                "p50": _clean(non_null.quantile(0.50)),
                "p75": _clean(non_null.quantile(0.75)),
                "max": _clean(non_null.max()),
                "null_ratio": _clean(
                    (total - non_null.count()) / total if total else None
                ),
            }
        )
    return rows
