"""Gate de promoción de modelos con bootstrap de champion.

Reglas del contrato:
- Sin champion (bootstrap): el candidato se promueve si supera al baseline.
- Con champion: el candidato debe superar al baseline Y al champion actual,
  ambos evaluados sobre la misma ventana de test.

Uso:
    python -m ml.promotion_gate --candidate-run-id <run_id>

Siempre termina con exit 0 si el gate pudo decidir (promueva o no); la
decisión se imprime como JSON y se guarda en el run del candidato.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import logging
from pathlib import Path
import sys

from ml import model_store
from ml.config import (
    CHAMPION_ALIAS,
    MODEL_NAME,
    PRIMARY_METRIC,
    TARGET_COLUMN,
    get_mlflow_tracking_uri,
)
from ml.train import evaluate_on_test, temporal_split

logger = logging.getLogger(__name__)


def decide_promotion(
    candidate_metrics: dict[str, float],
    baseline_metrics: dict[str, float],
    champion_metrics: dict[str, float] | None,
    primary_metric: str = PRIMARY_METRIC,
) -> dict:
    """Decisión pura del gate; menor métrica es mejor."""
    candidate_value = candidate_metrics.get(primary_metric)
    baseline_value = baseline_metrics.get(primary_metric)

    if candidate_value is None or baseline_value is None:
        return {
            "promoted": False,
            "reason": f"candidato o baseline sin métrica '{primary_metric}': run inválido",
        }

    if not candidate_value < baseline_value:
        return {
            "promoted": False,
            "reason": (
                f"no supera al baseline ({primary_metric} candidato "
                f"{candidate_value:.4f} >= baseline {baseline_value:.4f})"
            ),
        }

    if champion_metrics is None:
        return {
            "promoted": True,
            "reason": (
                f"bootstrap: no hay champion y supera al baseline "
                f"({primary_metric} {candidate_value:.4f} < {baseline_value:.4f})"
            ),
        }

    champion_value = champion_metrics.get(primary_metric)
    if champion_value is None or candidate_value < champion_value:
        return {
            "promoted": True,
            "reason": (
                f"supera al baseline y al champion actual ({primary_metric} "
                f"{candidate_value:.4f} < champion {champion_value:.4f})"
                if champion_value is not None
                else "supera al baseline; champion sin métrica comparable"
            ),
        }

    return {
        "promoted": False,
        "reason": (
            f"supera al baseline pero no al champion ({primary_metric} "
            f"{candidate_value:.4f} >= champion {champion_value:.4f})"
        ),
    }


def _evaluate_champion_on_current_window(pointer: dict, as_of_date: date) -> dict | None:
    """Re-evalúa el champion sobre la misma ventana de test que el candidato."""
    from feature_store import repository

    try:
        champion_model = model_store.load_model(pointer["run_id"])
    except FileNotFoundError:
        logger.warning(
            "Champion %s sin artefactos locales: se aplica bootstrap", pointer["run_id"]
        )
        return None

    with repository.connect() as conn:
        features = repository.read_feature_frame(conn, as_of_date)
    trainable = features.dropna(subset=[TARGET_COLUMN])
    _, test_frame, _ = temporal_split(trainable)
    return evaluate_on_test(champion_model, test_frame)


def _set_mlflow_champion_alias(candidate_info: dict) -> None:
    tracking_uri = get_mlflow_tracking_uri()
    model_version = candidate_info.get("mlflow", {}).get("model_version")
    if not tracking_uri or not model_version:
        return
    try:
        import mlflow  # noqa: PLC0415

        client = mlflow.MlflowClient(tracking_uri=tracking_uri)
        client.set_registered_model_alias(MODEL_NAME, CHAMPION_ALIAS, model_version)
        logger.info(
            "Alias '%s' -> versión %s en MLflow (%s)",
            CHAMPION_ALIAS,
            model_version,
            MODEL_NAME,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo actualizar el alias en MLflow: %s", exc)


def run_gate(candidate_run_id: str) -> dict:
    candidate_info = model_store.load_run_info(candidate_run_id)
    as_of_date = date.fromisoformat(candidate_info["as_of_date"])

    pointer = model_store.read_champion_pointer()
    champion_metrics = None
    if pointer is not None:
        if pointer["run_id"] == candidate_run_id:
            return {
                "candidate_run_id": candidate_run_id,
                "promoted": False,
                "reason": "el candidato ya es el champion actual",
            }
        champion_metrics = _evaluate_champion_on_current_window(pointer, as_of_date)
        if champion_metrics is None:
            pointer = None

    decision = decide_promotion(
        candidate_info["metrics"]["model"],
        candidate_info["metrics"]["baseline"],
        champion_metrics,
    )

    result = {
        "candidate_run_id": candidate_run_id,
        "as_of_date": str(as_of_date),
        "primary_metric": PRIMARY_METRIC,
        "candidate": candidate_info["metrics"]["model"],
        "baseline": candidate_info["metrics"]["baseline"],
        "champion": champion_metrics,
        "previous_champion_run_id": pointer["run_id"] if pointer else None,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        **decision,
    }

    if decision["promoted"]:
        model_store.write_champion_pointer(
            candidate_run_id,
            decision["reason"],
            candidate_info["metrics"]["model"],
            pointer,
        )
        _set_mlflow_champion_alias(candidate_info)

    decision_path = Path(model_store.run_dir(candidate_run_id)) / "gate_decision.json"
    decision_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Gate de promoción de modelos")
    parser.add_argument("--candidate-run-id", required=True)
    args = parser.parse_args(argv)

    try:
        result = run_gate(args.candidate_run_id)
    except FileNotFoundError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
