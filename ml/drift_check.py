"""Drift check minimo, desacoplado del serving.

Compara la distribucion reciente de `features.pozo_monthly_features`
contra las `feature_reference_stats` del champion actual (generadas por
Integrante 1 en el mismo run de training). No bloquea la API ni el
retraining: es un chequeo de observabilidad que se corre aparte
(scripts/run-drift-check.sh) y reporta, por feature numerica, si la
media reciente se aleja de la referencia mas de --z-threshold desvios.

Si no hay champion o el champion no tiene reference stats, termina con
un mensaje claro en vez de fallar de forma silenciosa (evita el riesgo
de "drift script muerto" documentado en el contrato).

Uso:
    python -m ml.drift_check [--as-of-date 2026-06-01] [--z-threshold 3.0]
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import logging
import sys

import pandas as pd

from ml import model_store
from ml.config import DRIFT_WINDOW_MONTHS, DRIFT_Z_THRESHOLD, NUMERIC_FEATURES

logger = logging.getLogger(__name__)

STATUS_NO_CHAMPION = "no_champion"
STATUS_NO_REFERENCE_STATS = "no_reference_stats"
STATUS_NO_RECENT_DATA = "no_recent_data"
STATUS_OK = "ok"
STATUS_DRIFT = "drift_detected"


def _recent_window(frame: pd.DataFrame, window_months: int) -> pd.DataFrame:
    periodo = pd.to_datetime(frame["periodo_mes"])
    months = periodo.dt.to_period("M").drop_duplicates().sort_values()
    if months.empty:
        return frame.iloc[0:0]
    cutoff_period = months.iloc[-window_months] if len(months) >= window_months else months.iloc[0]
    cutoff = cutoff_period.to_timestamp()
    return frame[periodo >= cutoff]


def compare_feature(
    feature_name: str, current_values: pd.Series, reference_row: pd.Series
) -> dict:
    current = pd.to_numeric(current_values, errors="coerce").dropna()
    ref_mean = reference_row.get("mean")
    ref_std = reference_row.get("std")

    result = {
        "feature": feature_name,
        "current_count": int(current.count()),
        "current_mean": float(current.mean()) if not current.empty else None,
        "reference_mean": float(ref_mean) if ref_mean is not None else None,
        "reference_std": float(ref_std) if ref_std is not None else None,
        "z_score": None,
        "drifted": False,
    }

    if current.empty or ref_mean is None or ref_std is None or ref_std == 0:
        return result

    z_score = (result["current_mean"] - float(ref_mean)) / float(ref_std)
    result["z_score"] = z_score
    return result


def run_drift_check(
    as_of_date: date,
    window_months: int = DRIFT_WINDOW_MONTHS,
    z_threshold: float = DRIFT_Z_THRESHOLD,
) -> dict:
    from feature_store import repository

    pointer = model_store.read_champion_pointer()
    if pointer is None:
        return {
            "status": STATUS_NO_CHAMPION,
            "message": "No hay champion promovido todavia: corre ml.promotion_gate primero.",
        }

    champion_run_id = pointer["run_id"]

    with repository.connect() as conn:
        reference = repository.read_reference_stats(conn, champion_run_id)
        if reference.empty:
            return {
                "status": STATUS_NO_REFERENCE_STATS,
                "champion_run_id": champion_run_id,
                "message": (
                    f"El champion {champion_run_id} no tiene feature_reference_stats: "
                    "no se puede evaluar drift."
                ),
            }

        features = repository.read_feature_frame(conn, as_of_date)

    recent = _recent_window(features, window_months)
    if recent.empty:
        return {
            "status": STATUS_NO_RECENT_DATA,
            "champion_run_id": champion_run_id,
            "message": f"No hay features hasta {as_of_date} para evaluar drift.",
        }

    reference_by_feature = reference.set_index("feature_name")

    checks = []
    for feature_name in NUMERIC_FEATURES:
        if feature_name not in reference_by_feature.index:
            continue
        checks.append(
            compare_feature(
                feature_name,
                recent[feature_name],
                reference_by_feature.loc[feature_name],
            )
        )

    drifted = [
        check
        for check in checks
        if check["z_score"] is not None and abs(check["z_score"]) > z_threshold
    ]

    return {
        "status": STATUS_DRIFT if drifted else STATUS_OK,
        "champion_run_id": champion_run_id,
        "as_of_date": str(as_of_date),
        "window_months": window_months,
        "z_threshold": z_threshold,
        "checks": checks,
        "drifted_features": [check["feature"] for check in drifted],
    }


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Drift check minimo de features")
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Corte temporal (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--window-months",
        type=int,
        default=DRIFT_WINDOW_MONTHS,
        help="Meses recientes a comparar contra la referencia",
    )
    parser.add_argument(
        "--z-threshold",
        type=float,
        default=DRIFT_Z_THRESHOLD,
        help="Umbral de z-score para marcar drift",
    )
    args = parser.parse_args(argv)

    result = run_drift_check(args.as_of_date, args.window_months, args.z_threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] in (STATUS_NO_CHAMPION, STATUS_NO_REFERENCE_STATS, STATUS_NO_RECENT_DATA):
        return 2
    if result["status"] == STATUS_DRIFT:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
