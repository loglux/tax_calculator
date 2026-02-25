from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from .models import TaxRate


class CalculatorAPITokenAuthTests(APITestCase):
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

    def _payload(self):
        return {
            "tax_year": 2025,
            "income": "60000",
            "income_type": "yearly",
            "workweek_hours": "40",
            "tax_code": "1257L",
            "is_blind": False,
            "no_ni": False,
            "is_scotland": False,
        }

    def test_calculate_api_requires_bearer_token(self):
        response = self.client.post(reverse("calculate_tax"), self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_calculate_api_works_with_valid_jwt(self):
        User = get_user_model()
        user = User.objects.create_user(username="api_test_user", password="test-pass-123")
        token = str(AccessToken.for_user(user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post(reverse("calculate_tax"), self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["calculation_mode"], "hmrc_paye")
        self.assertIn("tax_paid", response.data)
        self.assertIn("ni_paid", response.data)

    def test_token_endpoint_is_public(self):
        User = get_user_model()
        User.objects.create_user(username="token_user", password="token-pass-123")
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "token_user", "password": "token-pass-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
