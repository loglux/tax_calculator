from decimal import Decimal

from django.test import TestCase

from .models import TaxRate
from .views import process_tax_calculation


class HMRCPipelineParityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        TaxRate.objects.update_or_create(
            year=2025,
            defaults={
                "personal_allowance": Decimal("12570"),
                "blind_allowance": Decimal("3130"),
                "mca_relief_amount": Decimal("1137"),
                "personal_allowance_taper_threshold": Decimal("100000"),
                "basic_rate": Decimal("20"),
                "higher_rate": Decimal("40"),
                "additional_rate": Decimal("45"),
                "basic_threshold": Decimal("37700"),
                "higher_threshold": Decimal("125140"),
                "ni_threshold": Decimal("12570"),
                "ni_rate": Decimal("8"),
                "ni_additional_rate": Decimal("2"),
                "ni_upper_limit": Decimal("50270"),
                "starter_rate_scotland": Decimal("0.19"),
                "basic_rate_scotland": Decimal("0.20"),
                "intermediate_rate_scotland": Decimal("0.21"),
                "higher_rate_scotland": Decimal("0.42"),
                "advanced_rate_scotland": Decimal("0.45"),
                "top_rate_scotland": Decimal("0.48"),
                "starter_threshold_scotland": Decimal("2827"),
                "basic_threshold_scotland": Decimal("14921"),
                "intermediate_threshold_scotland": Decimal("31092"),
                "higher_threshold_scotland": Decimal("62430"),
                "advanced_threshold_scotland": Decimal("112570"),
            },
        )

    def _hmrc_payload(self, income, **extra):
        payload = {
            "income": Decimal(income),
            "income_type": "yearly",
            "workweek_hours": Decimal("40"),
            "is_blind": False,
            "no_ni": False,
            "is_scotland": False,
            "tax_code": "1257L",
        }
        payload.update(extra)
        return payload

    def test_hmrc_defaults_produce_expected_precision_marker(self):
        incomes = ("20000", "45000", "60000", "85000", "100000")
        for income in incomes:
            hmrc, error_hmrc = process_tax_calculation(self._hmrc_payload(income), year=2025)
            self.assertIsNone(error_hmrc)
            self.assertEqual(hmrc["calculation_mode"], "hmrc_paye")
            self.assertEqual(hmrc["hmrc_precision_level"], "approximate")

    def test_hmrc_cumulative_with_ytd_changes_default_result(self):
        default_hmrc, _ = process_tax_calculation(self._hmrc_payload("60000"), year=2025)
        hmrc, _ = process_tax_calculation(
            self._hmrc_payload(
                "60000",
                period_number=6,
                ytd_gross=Decimal("25000"),
                ytd_tax_paid=Decimal("5000"),
            ),
            year=2025,
        )
        self.assertNotEqual(Decimal(default_hmrc["tax_paid"]), Decimal(hmrc["tax_paid"]))
        self.assertIn("hmrc_period_tax", hmrc)

    def test_hmrc_zero_t_tax_code_pays_more_tax_than_1257l(self):
        hmrc_regular, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="1257L"), year=2025
        )
        hmrc_zero_t, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="0T"), year=2025
        )
        self.assertGreater(Decimal(hmrc_zero_t["tax_paid"]), Decimal(hmrc_regular["tax_paid"]))

    def test_hmrc_k_code_pays_more_tax_than_1257l(self):
        hmrc_regular, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="1257L"), year=2025
        )
        hmrc_k, _ = process_tax_calculation(self._hmrc_payload("60000", tax_code="K500"), year=2025)
        self.assertGreater(Decimal(hmrc_k["tax_paid"]), Decimal(hmrc_regular["tax_paid"]))

    def test_hmrc_marriage_allowance_suffixes_are_applied(self):
        hmrc_regular, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="1257L"), year=2025
        )
        hmrc_m, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="1257M"), year=2025
        )
        hmrc_n, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="1257N"), year=2025
        )
        self.assertLess(Decimal(hmrc_m["tax_paid"]), Decimal(hmrc_regular["tax_paid"]))
        self.assertGreater(Decimal(hmrc_n["tax_paid"]), Decimal(hmrc_regular["tax_paid"]))

    def test_hmrc_special_rate_codes_are_supported(self):
        hmrc_regular, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="1257L"), year=2025
        )
        hmrc_br, _ = process_tax_calculation(self._hmrc_payload("60000", tax_code="BR"), year=2025)
        hmrc_d0, _ = process_tax_calculation(self._hmrc_payload("60000", tax_code="D0"), year=2025)
        hmrc_d1, _ = process_tax_calculation(self._hmrc_payload("60000", tax_code="D1"), year=2025)
        hmrc_nt, _ = process_tax_calculation(self._hmrc_payload("60000", tax_code="NT"), year=2025)

        self.assertGreater(Decimal(hmrc_br["tax_paid"]), Decimal(hmrc_regular["tax_paid"]))
        self.assertGreater(Decimal(hmrc_d0["tax_paid"]), Decimal(hmrc_br["tax_paid"]))
        self.assertGreater(Decimal(hmrc_d1["tax_paid"]), Decimal(hmrc_d0["tax_paid"]))
        self.assertEqual(Decimal(hmrc_nt["tax_paid"]), Decimal("0.00"))

    def test_hmrc_s_prefix_forces_scotland_bands(self):
        hmrc_s_prefix, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="S1257L", is_scotland=False),
            year=2025,
        )
        hmrc_scotland_flag, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="1257L", is_scotland=True),
            year=2025,
        )
        self.assertEqual(hmrc_s_prefix["hmrc_region"], "scotland")
        self.assertEqual(
            Decimal(hmrc_s_prefix["tax_paid"]), Decimal(hmrc_scotland_flag["tax_paid"])
        )

    def test_hmrc_c_prefix_forces_ruk_bands(self):
        hmrc_c_prefix, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="C1257L", is_scotland=True),
            year=2025,
        )
        hmrc_ruk_flag, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="1257L", is_scotland=False),
            year=2025,
        )
        self.assertEqual(hmrc_c_prefix["hmrc_region"], "rUK")
        self.assertEqual(Decimal(hmrc_c_prefix["tax_paid"]), Decimal(hmrc_ruk_flag["tax_paid"]))

    def test_hmrc_w1_marker_forces_non_cumulative_basis(self):
        hmrc_w1, _ = process_tax_calculation(
            self._hmrc_payload(
                "60000",
                tax_code="1257LW1",
                hmrc_basis="cumulative",
                period_number=6,
                ytd_gross=Decimal("25000"),
                ytd_tax_paid=Decimal("5000"),
            ),
            year=2025,
        )
        hmrc_explicit_non_cum, _ = process_tax_calculation(
            self._hmrc_payload(
                "60000",
                tax_code="1257L",
                hmrc_basis="non_cumulative",
                period_number=6,
                ytd_gross=Decimal("25000"),
                ytd_tax_paid=Decimal("5000"),
            ),
            year=2025,
        )
        self.assertEqual(hmrc_w1["hmrc_basis"], "non_cumulative")
        self.assertEqual(Decimal(hmrc_w1["tax_paid"]), Decimal(hmrc_explicit_non_cum["tax_paid"]))

    def test_hmrc_scottish_special_rate_codes_are_supported(self):
        hmrc_sd0, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="SD0", is_scotland=False),
            year=2025,
        )
        hmrc_sd1, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="SD1", is_scotland=False),
            year=2025,
        )
        hmrc_d0, _ = process_tax_calculation(
            self._hmrc_payload("60000", tax_code="D0", is_scotland=False),
            year=2025,
        )

        self.assertEqual(hmrc_sd0["hmrc_region"], "scotland")
        self.assertEqual(hmrc_sd1["hmrc_region"], "scotland")
        self.assertGreater(Decimal(hmrc_sd0["tax_paid"]), Decimal(hmrc_d0["tax_paid"]))
        self.assertGreater(Decimal(hmrc_sd1["tax_paid"]), Decimal(hmrc_sd0["tax_paid"]))

    def test_hmrc_taper_reduction_is_applied_after_threshold(self):
        hmrc_below, _ = process_tax_calculation(self._hmrc_payload("100000"), year=2025)
        hmrc_above, _ = process_tax_calculation(self._hmrc_payload("120000"), year=2025)

        self.assertEqual(Decimal(hmrc_below["personal_allowance_reduction"]), Decimal("0.00"))
        self.assertEqual(Decimal(hmrc_above["personal_allowance_reduction"]), Decimal("10000.00"))

    def test_hmrc_period_outputs_are_consistent_with_annual_totals(self):
        hmrc, _ = process_tax_calculation(self._hmrc_payload("60000"), year=2025)
        yearly_tax = Decimal(hmrc["tax_paid"])
        monthly_tax = Decimal(hmrc["monthly_tax_paid"])
        # Rounded display values can differ by up to 0.02 when reconstructed from months.
        self.assertLessEqual(abs(yearly_tax - (monthly_tax * Decimal("12"))), Decimal("0.02"))

    def test_hmrc_default_profile_is_marked_as_approximate(self):
        hmrc, error = process_tax_calculation(self._hmrc_payload("60000"), year=2025)
        self.assertIsNone(error)
        self.assertEqual(hmrc["hmrc_precision_level"], "approximate")
        self.assertIn("hmrc_precision_note", hmrc)

    def test_hmrc_strict_mode_requires_period_context(self):
        _, error = process_tax_calculation(
            self._hmrc_payload("60000", hmrc_strict=True),
            year=2025,
        )
        self.assertIsNotNone(error)
        self.assertIn("HMRC strict mode requires payroll context", error)
