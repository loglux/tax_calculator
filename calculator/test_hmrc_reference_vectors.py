import json
from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from .tax_rate_seed_data import TAX_RATE_SEED_DATA
from .views import process_tax_calculation
from .models import TaxRate


class HMRCReferenceVectorsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        TaxRate.objects.update_or_create(year=2025, defaults=TAX_RATE_SEED_DATA[2025])

    def test_hmrc_reference_vectors_2025(self):
        vectors_path = Path(__file__).resolve().parent / "reference_vectors" / "hmrc_paye_2025.json"
        vectors = json.loads(vectors_path.read_text())

        for vector in vectors:
            payload = vector["payload"].copy()
            for field in ("income", "workweek_hours", "ytd_gross", "ytd_tax_paid"):
                if field in payload:
                    payload[field] = Decimal(payload[field])

            context, error = process_tax_calculation(payload, year=vector["year"])
            self.assertIsNone(error, msg=f"{vector['name']}: unexpected error {error}")
            for key, expected_value in vector["expected"].items():
                actual = Decimal(context[key])
                self.assertEqual(
                    actual,
                    Decimal(expected_value),
                    msg=f"{vector['name']} field={key}: expected {expected_value}, got {actual}",
                )
