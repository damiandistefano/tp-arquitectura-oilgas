"""Valida un modelo (por alias o run) sobre el split temporal actual.

Uso:
    python -m ml.validate --model-alias champion
    python -m ml.validate --run-id model_20260601_ab12cd34
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import sys

from ml import model_store
from ml.baseline import evaluate_baseline
from ml.config import CHAMPION_ALIAS, TARGET_COLUMN
from ml.train import evaluate_on_test, temporal_split


def resolve_run_id(model_alias: str | None, run_id: str | None) -> str:
    if run_id:
        return run_id
    if model_alias != CHAMPION_ALIAS:
        raise ValueError(f"Alias no soportado: {model_alias} (solo '{CHAMPION_ALIAS}')")
    pointer = model_store.read_champion_pointer()
    if pointer is None:
        raise FileNotFoundError(
            "No hay champion promovido todavía: correr training y "
            "`python -m ml.promotion_gate --candidate-run-id <run_id>`"
        )
    return pointer["run_id"]


def run_validation(model_alias: str | None, run_id: str | None, as_of_date: date) -> dict:
    from feature_store import repository

    resolved_run_id = resolve_run_id(model_alias, run_id)
    model = model_store.load_model(resolved_run_id)

    with repository.connect() as conn:
        features = repository.read_feature_frame(conn, as_of_date)
    if features.empty:
        raise RuntimeError("El feature store está vacío: correr ml.build_features primero")

    trainable = features.dropna(subset=[TARGET_COLUMN])
    _, test_frame, split_info = temporal_split(trainable)

    return {
        "run_id": resolved_run_id,
        "alias": model_alias if not run_id else None,
        "as_of_date": str(as_of_date),
        "split": split_info,
        "n_test": int(len(test_frame)),
        "metrics": {
            "model": evaluate_on_test(model, test_frame),
            "baseline": evaluate_baseline(test_frame),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida un modelo sobre el test temporal")
    parser.add_argument("--model-alias", default=None, help="Alias, ej: champion")
    parser.add_argument("--run-id", default=None, help="Run puntual a validar")
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Corte temporal (YYYY-MM-DD)",
    )
    args = parser.parse_args(argv)

    if not args.model_alias and not args.run_id:
        args.model_alias = CHAMPION_ALIAS

    try:
        result = run_validation(args.model_alias, args.run_id, args.as_of_date)
    except FileNotFoundError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
