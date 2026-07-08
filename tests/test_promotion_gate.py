"""Tests de las reglas del gate de promoción (decisión pura, sin DB)."""

from ml.promotion_gate import decide_promotion


def test_bootstrap_promueve_si_supera_baseline():
    decision = decide_promotion(
        candidate_metrics={"mae": 8.0},
        baseline_metrics={"mae": 10.0},
        champion_metrics=None,
    )
    assert decision["promoted"] is True
    assert "bootstrap" in decision["reason"]


def test_bootstrap_no_promueve_si_no_supera_baseline():
    decision = decide_promotion(
        candidate_metrics={"mae": 12.0},
        baseline_metrics={"mae": 10.0},
        champion_metrics=None,
    )
    assert decision["promoted"] is False
    assert "baseline" in decision["reason"]


def test_empatar_al_baseline_no_alcanza():
    decision = decide_promotion(
        candidate_metrics={"mae": 10.0},
        baseline_metrics={"mae": 10.0},
        champion_metrics=None,
    )
    assert decision["promoted"] is False


def test_con_champion_debe_superar_a_ambos():
    decision = decide_promotion(
        candidate_metrics={"mae": 7.0},
        baseline_metrics={"mae": 10.0},
        champion_metrics={"mae": 8.0},
    )
    assert decision["promoted"] is True


def test_superar_baseline_pero_no_al_champion_no_promueve():
    decision = decide_promotion(
        candidate_metrics={"mae": 9.0},
        baseline_metrics={"mae": 10.0},
        champion_metrics={"mae": 8.0},
    )
    assert decision["promoted"] is False
    assert "champion" in decision["reason"]


def test_run_sin_metrica_primaria_es_invalido():
    decision = decide_promotion(
        candidate_metrics={},
        baseline_metrics={"mae": 10.0},
        champion_metrics=None,
    )
    assert decision["promoted"] is False
    assert "inválido" in decision["reason"]
