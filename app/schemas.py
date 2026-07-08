"""Schemas públicos de la API predictiva."""

from __future__ import annotations

from pydantic import BaseModel


class ForecastPrediction(BaseModel):
    periodo_mes: str
    prediction: float


class ModelMetadata(BaseModel):
    name: str
    version: str
    alias: str
    run_id: str
    source: str


class ForecastResponse(BaseModel):
    id_pozo: str
    target: str
    horizon: list[str]
    predictions: list[ForecastPrediction]
    model: ModelMetadata
