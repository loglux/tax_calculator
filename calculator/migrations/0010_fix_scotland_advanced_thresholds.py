from django.db import migrations


def fix_scotland_advanced_thresholds(apps, schema_editor):
    TaxRate = apps.get_model("calculator", "TaxRate")
    TaxRate.objects.filter(year__in=[2024, 2025]).update(
        advanced_threshold_scotland="125140.00"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("calculator", "0009_seed_tax_rates_2026_2027"),
    ]

    operations = [
        migrations.RunPython(fix_scotland_advanced_thresholds, migrations.RunPython.noop),
    ]
