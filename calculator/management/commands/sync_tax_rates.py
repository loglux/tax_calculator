from django.core.management.base import BaseCommand

from calculator.models import TaxRate
from calculator.tax_rate_seed_data import TAX_RATE_SEED_DATA, TAX_RATE_SOURCES


class Command(BaseCommand):
    help = "Sync TaxRate table from centralized seed data (upsert by year)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show planned changes without writing to DB.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write("Tax rate sources:")
        for key, url in TAX_RATE_SOURCES.items():
            self.stdout.write(f"- {key}: {url}")

        for year in sorted(TAX_RATE_SEED_DATA):
            defaults = TAX_RATE_SEED_DATA[year]
            if dry_run:
                exists = TaxRate.objects.filter(year=year).exists()
                action = "would update" if exists else "would create"
                self.stdout.write(f"{year}: {action}")
                continue

            obj, created = TaxRate.objects.update_or_create(year=year, defaults=defaults)
            action = "created" if created else "updated"
            self.stdout.write(f"{obj.year}: {action}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run completed. No DB changes were made."))
        else:
            self.stdout.write(self.style.SUCCESS("Tax rates sync completed."))
