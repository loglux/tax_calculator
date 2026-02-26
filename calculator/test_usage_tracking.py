from decimal import Decimal

from django.test import TestCase

from .models import TaxRate, UsageEvent


class UsageTrackingTests(TestCase):
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
                "advanced_threshold_scotland": Decimal("125140"),
            },
        )

    def test_tracks_page_view(self):
        self.client.get("/calculator/")
        event = UsageEvent.objects.latest("id")
        self.assertEqual(event.event_type, UsageEvent.EVENT_PAGE_VIEW)
        self.assertEqual(event.path, "/calculator/")
        self.assertTrue(event.client_ip)

    def test_tracks_calculate_submit_with_payload_fields(self):
        self.client.post(
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
        event = UsageEvent.objects.latest("id")
        self.assertEqual(event.event_type, UsageEvent.EVENT_CALCULATE_SUBMIT)
        self.assertEqual(event.tax_year, 2025)
        self.assertEqual(event.income, Decimal("60000"))
        self.assertEqual(event.income_type, "yearly")
        self.assertEqual(event.workweek_hours, Decimal("40"))
        self.assertEqual(event.is_scotland, True)

    def test_tracks_api_call(self):
        self.client.post(
            "/calculator/api/calculate/",
            data='{"tax_year": 2025, "income_type": "yearly", "workweek_hours": 40}',
            content_type="application/json",
        )
        event = UsageEvent.objects.latest("id")
        self.assertEqual(event.event_type, UsageEvent.EVENT_API_CALL)
        self.assertEqual(event.path, "/calculator/api/calculate/")
        self.assertEqual(event.method, "POST")
