"""Generación de features mensuales por pozo, sin leakage temporal.

Regla del contrato: para el mes M, toda feature usa solo datos hasta M-1.
Los lags y rolling stats se calculan sobre un calendario mensual continuo
por pozo, así "lag 1" siempre significa "mes calendario anterior" aunque
falten meses en la fuente.

Uso:
    python -m ml.build_features --as-of-date 2026-06-01
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import sys
import uuid

import pandas as pd

from ml.config import SOURCE_FACT_TABLE

ROLLING_WINDOW = 3


def _month_start(value) -> pd.Timestamp:
    return pd.Timestamp(value).to_period("M").to_timestamp()


def build_feature_frame(
    produccion: pd.DataFrame,
    pozos: pd.DataFrame,
    as_of_date: date,
    run_id: str,
) -> pd.DataFrame:
    """Construye el frame de features a partir de producción mensual y dim_pozo.

    produccion: columnas id_pozo, periodo_mes, prod_pet (una fila por pozo y mes).
    pozos: columnas id_pozo + categóricas (cuenca, provincia, clasificacion,
    tipo_reservorio).
    """
    frame = produccion.copy()
    frame["periodo_mes"] = frame["periodo_mes"].map(_month_start)
    frame["prod_pet"] = pd.to_numeric(frame["prod_pet"], errors="coerce")

    cutoff = _month_start(as_of_date)
    frame = frame[frame["periodo_mes"] <= cutoff]
    frame = (
        frame.groupby(["id_pozo", "periodo_mes"], as_index=False)["prod_pet"].sum()
    )

    pieces = []
    for id_pozo, group in frame.groupby("id_pozo"):
        series = (
            group.set_index("periodo_mes")["prod_pet"]
            .sort_index()
        )
        observed_months = series.index
        # Calendario continuo para que los lags sean meses calendario reales
        full_index = pd.date_range(
            observed_months.min(), observed_months.max(), freq="MS"
        )
        series = series.reindex(full_index)

        shifted = series.shift(1)
        features = pd.DataFrame(
            {
                "prod_pet": series,
                "prod_pet_lag_1": series.shift(1),
                "prod_pet_lag_2": series.shift(2),
                "prod_pet_lag_3": series.shift(3),
                # Ventana M-3..M-1: nunca incluye el mes M
                "prod_pet_roll_mean_3": shifted.rolling(
                    ROLLING_WINDOW, min_periods=1
                ).mean(),
                "prod_pet_roll_std_3": shifted.rolling(
                    ROLLING_WINDOW, min_periods=2
                ).std(),
            }
        )
        features.index.name = "periodo_mes"
        features = features.reset_index()
        features["id_pozo"] = id_pozo

        first_month = observed_months.min()
        features["antiguedad_meses"] = (
            (features["periodo_mes"].dt.year - first_month.year) * 12
            + (features["periodo_mes"].dt.month - first_month.month)
        )

        # Solo meses observados en la fuente: no inventamos filas de target
        features = features[features["periodo_mes"].isin(observed_months)]
        pieces.append(features)

    if not pieces:
        return pd.DataFrame()

    result = pd.concat(pieces, ignore_index=True)
    result["mes"] = result["periodo_mes"].dt.month.astype("int16")
    result["anio"] = result["periodo_mes"].dt.year.astype("int16")

    categoricas = pozos.drop_duplicates(subset=["id_pozo"])[
        ["id_pozo", "cuenca", "provincia", "clasificacion", "tipo_reservorio"]
    ]
    result = result.merge(categoricas, on="id_pozo", how="left")

    result["feature_run_id"] = run_id
    result["as_of_date"] = cutoff.date()
    result["periodo_mes"] = result["periodo_mes"].dt.date

    return result.sort_values(["id_pozo", "periodo_mes"]).reset_index(drop=True)


def run_build_features(as_of_date: date) -> dict:
    """Lee Gold, construye las features y reemplaza el feature store."""
    from feature_store import repository

    run_id = f"features_{as_of_date:%Y%m%d}_{uuid.uuid4().hex[:8]}"

    with repository.connect() as conn:
        repository.record_feature_run_start(conn, run_id, as_of_date, SOURCE_FACT_TABLE)
        try:
            produccion, pozos = repository.read_source_frames(conn, as_of_date)
            if produccion.empty:
                raise RuntimeError(
                    f"{SOURCE_FACT_TABLE} no tiene datos hasta {as_of_date}: "
                    "correr primero el pipeline de datos (bronze/silver/gold)"
                )
            frame = build_feature_frame(produccion, pozos, as_of_date, run_id)
            rows_written = repository.replace_features(conn, frame)
            summary = {
                "run_id": run_id,
                "as_of_date": str(as_of_date),
                "rows_written": rows_written,
                "pozos": int(frame["id_pozo"].nunique()),
                "periodo_min": str(frame["periodo_mes"].min()),
                "periodo_max": str(frame["periodo_mes"].max()),
                "status": "success",
            }
            repository.record_feature_run_end(
                conn,
                run_id,
                status="success",
                rows_written=rows_written,
                pozos=summary["pozos"],
                periodo_min=frame["periodo_mes"].min(),
                periodo_max=frame["periodo_mes"].max(),
            )
        except Exception as exc:
            repository.record_feature_run_end(
                conn, run_id, status="failed", error_message=str(exc)
            )
            raise

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera features mensuales por pozo")
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Corte temporal (YYYY-MM-DD); solo se usan datos hasta ese mes",
    )
    args = parser.parse_args(argv)

    summary = run_build_features(args.as_of_date)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
