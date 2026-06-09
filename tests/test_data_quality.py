from quality.checks import build_result, status_from_failed_rows


def test_status_pass_when_no_failed_rows():
    assert status_from_failed_rows(0, "CRITICAL") == "PASS"


def test_status_failed_when_critical_has_failed_rows():
    assert status_from_failed_rows(3, "CRITICAL") == "FAILED"


def test_status_warning_when_warning_has_failed_rows():
    assert status_from_failed_rows(3, "WARNING") == "WARNING"


def test_build_result_sets_status_from_failed_rows():
    result = build_result(
        run_id="test-run",
        layer="gold",
        table_name="gold.fact_produccion_pozo",
        check_name="test_check",
        dimension="completeness",
        severity="CRITICAL",
        rows_checked=10,
        rows_failed=2,
        details={"field": "idpozo"},
    )

    assert result.status == "FAILED"
    assert result.rows_checked == 10
    assert result.rows_failed == 2
