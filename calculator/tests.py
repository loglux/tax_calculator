from decimal import Decimal

from django.test import TestCase

from .models import TaxRate
from .views import process_tax_calculation


class TaxCalculationModeTests(TestCase):
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

    def test_default_mode_is_hmrc(self):
        context, error = process_tax_calculation(
            {
                "income": Decimal("45000"),
                "income_type": "yearly",
                "workweek_hours": Decimal("40"),
                "is_blind": False,
                "no_ni": False,
                "is_scotland": False,
            },
            year=2025,
        )
        self.assertIsNone(error)
        self.assertEqual(context["calculation_mode"], "hmrc_paye")
        self.assertIn("hmrc_period_tax", context)

    def test_hmrc_mode_uses_tax_code(self):
        base_payload = {
            "income": Decimal("60000"),
            "income_type": "yearly",
            "workweek_hours": Decimal("40"),
            "is_blind": False,
            "no_ni": False,
            "is_scotland": False,
            "payroll_frequency": "monthly",
            "hmrc_basis": "cumulative",
            "period_number": 6,
            "ytd_tax_paid": Decimal("5000"),
            "ytd_gross": Decimal("25000"),
        }

        context_regular, error_regular = process_tax_calculation(
            {**base_payload, "tax_code": "1257L"},
            year=2025,
        )
        context_zero, error_zero = process_tax_calculation(
            {**base_payload, "tax_code": "0T"},
            year=2025,
        )

        self.assertIsNone(error_regular)
        self.assertIsNone(error_zero)
        self.assertEqual(context_regular["calculation_mode"], "hmrc_paye")
        self.assertIn("hmrc_period_tax", context_regular)
        self.assertGreater(Decimal(context_zero["tax_paid"]), Decimal(context_regular["tax_paid"]))

    def test_hmrc_mode_calculates_period_ni_above_threshold(self):
        context, error = process_tax_calculation(
            {
                "income": Decimal("60000"),
                "income_type": "yearly",
                "workweek_hours": Decimal("40"),
                "is_blind": False,
                "no_ni": False,
                "is_scotland": False,
                "tax_code": "1257L",
            },
            year=2025,
        )
        self.assertIsNone(error)
        self.assertEqual(context["calculation_mode"], "hmrc_paye")
        self.assertGreater(Decimal(context["hmrc_period_ni"]), Decimal("0"))

    def test_hmrc_mode_applies_personal_allowance_taper(self):
        context, error = process_tax_calculation(
            {
                "income": Decimal("120000"),
                "income_type": "yearly",
                "workweek_hours": Decimal("40"),
                "is_blind": False,
                "no_ni": False,
                "is_scotland": False,
                "tax_code": "1257L",
            },
            year=2025,
        )
        self.assertIsNone(error)
        self.assertEqual(context["calculation_mode"], "hmrc_paye")
        self.assertEqual(Decimal(context["personal_allowance_reduction"]), Decimal("10000.00"))

    def test_mca_reduces_tax_in_hmrc_mode(self):
        hmrc_without_mca, _ = process_tax_calculation(
            {
                "income": Decimal("60000"),
                "income_type": "yearly",
                "workweek_hours": Decimal("40"),
                "is_blind": False,
                "no_ni": False,
                "is_scotland": False,
                "tax_code": "1257L",
                "mca": False,
            },
            year=2025,
        )
        hmrc_with_mca, _ = process_tax_calculation(
            {
                "income": Decimal("60000"),
                "income_type": "yearly",
                "workweek_hours": Decimal("40"),
                "is_blind": False,
                "no_ni": False,
                "is_scotland": False,
                "tax_code": "1257L",
                "mca": True,
            },
            year=2025,
        )

        self.assertGreater(
            Decimal(hmrc_without_mca["tax_paid"]),
            Decimal(hmrc_with_mca["tax_paid"]),
        )
        self.assertEqual(Decimal(hmrc_with_mca["mca_relief_amount"]), Decimal("1137.00"))

    def test_ui_shows_result_table_when_tax_is_zero_for_nt_code(self):
        response = self.client.post(
            "/calculator/",
            {
                "tax_year": "2025",
                "income": "60000",
                "income_type": "yearly",
                "workweek_hours": "40",
                "tax_code": "NT",
            },
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("id=\"taxPaid\">£0.00</td>", html)
        self.assertIn("id=\"niPaid\">£3213.12</td>", html)

    def test_ui_hmrc_values_for_standard_and_br_codes(self):
        standard = self.client.post(
            "/calculator/",
            {
                "tax_year": "2025",
                "income": "60000",
                "income_type": "yearly",
                "workweek_hours": "40",
                "tax_code": "1257L",
            },
        )
        br = self.client.post(
            "/calculator/",
            {
                "tax_year": "2025",
                "income": "60000",
                "income_type": "yearly",
                "workweek_hours": "40",
                "tax_code": "BR",
            },
        )

        self.assertEqual(standard.status_code, 200)
        self.assertEqual(br.status_code, 200)

        html_standard = standard.content.decode("utf-8")
        self.assertIn("id=\"taxPaid\">£11431.92</td>", html_standard)
        self.assertIn("id=\"niPaid\">£3213.12</td>", html_standard)
        self.assertIn("id=\"takeHome\">£45354.96</td>", html_standard)
        self.assertNotIn("id=\"id_calculation_mode\"", html_standard)

        html_br = br.content.decode("utf-8")
        self.assertIn("id=\"taxPaid\">£12000.00</td>", html_br)
        self.assertIn("id=\"takeHome\">£44786.88</td>", html_br)

    def test_ui_checkboxes_persist_after_show(self):
        scotland_response = self.client.post(
            "/calculator/",
            {
                "tax_year": "2025",
                "income": "60000",
                "income_type": "yearly",
                "workweek_hours": "40",
                "tax_code": "1257L",
                "is_scotland": "on",
            },
        )
        no_ni_response = self.client.post(
            "/calculator/",
            {
                "tax_year": "2025",
                "income": "60000",
                "income_type": "yearly",
                "workweek_hours": "40",
                "tax_code": "1257L",
                "no_ni": "on",
            },
        )

        self.assertEqual(scotland_response.status_code, 200)
        self.assertEqual(no_ni_response.status_code, 200)

        scotland_html = scotland_response.content.decode("utf-8")
        self.assertIn(
            "name=\"is_scotland\" class=\"form-check-input\" id=\"id_is_scotland\" checked",
            scotland_html,
        )
        self.assertIn("id=\"taxPaid\">£13213.80</td>", scotland_html)

        no_ni_html = no_ni_response.content.decode("utf-8")
        self.assertIn(
            "name=\"no_ni\" class=\"form-check-input\" id=\"id_no_ni\" checked",
            no_ni_html,
        )
        self.assertIn("id=\"niPaid\">£0.00</td>", no_ni_html)
