from tools.recon_whatif import evaluate_tolerances


def test_missing_or_zero_control_totals_have_null_verdicts():
    # Corrected what-if controls handle missing and zero denominators without aborting.
    for drawn, ead in ((None, 10.0), (10.0, None), (0.0, 0.0)):
        result = evaluate_tolerances(drawn, ead, {"candidate": 0.0001})
        assert result == {
            "candidate": {
                "tolerance": 0.0001,
                "pass": None,
                "currency_excess": None,
                "currency_headroom": None,
            }
        }
