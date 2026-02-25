from django.db import migrations


def seed_tax_rates(apps, schema_editor):
    TaxRate = apps.get_model("calculator", "TaxRate")

    defaults_2025 = {
        "personal_allowance": "12570.00",
        "blind_allowance": "3130.00",
        "mca_relief_amount": "1137.00",
        "personal_allowance_taper_threshold": "100000.00",
        "basic_rate": "20.00",
        "higher_rate": "40.00",
        "additional_rate": "45.00",
        "basic_threshold": "37700.00",
        "higher_threshold": "125140.00",
        "ni_threshold": "12570.00",
        "ni_rate": "8.00",
        "ni_additional_rate": "2.00",
        "ni_upper_limit": "50270.00",
        "starter_rate_scotland": "0.19",
        "basic_rate_scotland": "0.20",
        "intermediate_rate_scotland": "0.21",
        "higher_rate_scotland": "0.42",
        "advanced_rate_scotland": "0.45",
        "top_rate_scotland": "0.48",
        "starter_threshold_scotland": "2827.00",
        "basic_threshold_scotland": "14921.00",
        "intermediate_threshold_scotland": "31092.00",
        "higher_threshold_scotland": "62430.00",
        "advanced_threshold_scotland": "112570.00",
    }

    defaults_2026 = {
        "personal_allowance": "12570.00",
        "blind_allowance": "3250.00",
        "mca_relief_amount": "1170.00",
        "personal_allowance_taper_threshold": "100000.00",
        "basic_rate": "20.00",
        "higher_rate": "40.00",
        "additional_rate": "45.00",
        "basic_threshold": "37700.00",
        "higher_threshold": "125140.00",
        "ni_threshold": "12570.00",
        "ni_rate": "8.00",
        "ni_additional_rate": "2.00",
        "ni_upper_limit": "50270.00",
        "starter_rate_scotland": "0.19",
        "basic_rate_scotland": "0.20",
        "intermediate_rate_scotland": "0.21",
        "higher_rate_scotland": "0.42",
        "advanced_rate_scotland": "0.45",
        "top_rate_scotland": "0.48",
        "starter_threshold_scotland": "3967.00",
        "basic_threshold_scotland": "16956.00",
        "intermediate_threshold_scotland": "31092.00",
        "higher_threshold_scotland": "62430.00",
        "advanced_threshold_scotland": "125140.00",
    }

    TaxRate.objects.update_or_create(year=2025, defaults=defaults_2025)
    TaxRate.objects.update_or_create(year=2026, defaults=defaults_2026)

    # Keep 2024/25 NI aligned with current employee Class 1 rates.
    TaxRate.objects.filter(year=2024).update(
        ni_threshold="12570.00",
        ni_rate="8.00",
        ni_additional_rate="2.00",
        ni_upper_limit="50270.00",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("calculator", "0008_taxrate_advanced_scotland_and_allowances"),
    ]

    operations = [
        migrations.RunPython(seed_tax_rates, migrations.RunPython.noop),
    ]
