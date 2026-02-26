from django.db import models


class TaxRate(models.Model):
    year = models.IntegerField()

    # Personal tax-free allowance.
    personal_allowance = models.DecimalField(max_digits=10, decimal_places=2)
    blind_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=3130)
    mca_relief_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Income threshold above which personal allowance starts tapering.
    personal_allowance_taper_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=100000
    )

    # Rates and thresholds for rUK (non-Scotland).
    basic_rate = models.DecimalField(max_digits=5, decimal_places=2)
    higher_rate = models.DecimalField(max_digits=5, decimal_places=2)
    additional_rate = models.DecimalField(max_digits=5, decimal_places=2)

    basic_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=37700)
    higher_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=125140)

    # National Insurance
    ni_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    ni_rate = models.DecimalField(max_digits=5, decimal_places=2)
    ni_additional_rate = models.DecimalField(max_digits=5, decimal_places=2)
    ni_upper_limit = models.DecimalField(max_digits=10, decimal_places=2, default=50000)

    # Scotland tax rates.
    starter_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    basic_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    intermediate_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    higher_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    advanced_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    top_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Scotland thresholds.
    starter_threshold_scotland = models.DecimalField(max_digits=10, decimal_places=2, default=2306)
    basic_threshold_scotland = models.DecimalField(max_digits=10, decimal_places=2, default=13991)
    intermediate_threshold_scotland = models.DecimalField(
        max_digits=10, decimal_places=2, default=31092
    )
    higher_threshold_scotland = models.DecimalField(max_digits=10, decimal_places=2, default=62430)
    advanced_threshold_scotland = models.DecimalField(
        max_digits=10, decimal_places=2, default=125140
    )

    def __str__(self):
        return f"{self.year} Tax Rates"


class UsageEvent(models.Model):
    EVENT_PAGE_VIEW = "page_view"
    EVENT_CALCULATE_SUBMIT = "calculate_submit"
    EVENT_API_CALL = "api_call"

    EVENT_CHOICES = (
        (EVENT_PAGE_VIEW, "Page View"),
        (EVENT_CALCULATE_SUBMIT, "Calculator Submit"),
        (EVENT_API_CALL, "API Call"),
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES, db_index=True)
    path = models.CharField(max_length=255, db_index=True)
    method = models.CharField(max_length=8)
    status_code = models.PositiveSmallIntegerField()
    client_ip = models.CharField(max_length=45, blank=True, db_index=True)
    client_hash = models.CharField(max_length=64, blank=True, db_index=True)
    client_kind = models.CharField(max_length=16, blank=True, db_index=True)
    is_bot = models.BooleanField(default=False, db_index=True)
    user_agent = models.CharField(max_length=255, blank=True)

    tax_year = models.IntegerField(null=True, blank=True, db_index=True)
    income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    income_type = models.CharField(max_length=16, blank=True, db_index=True)
    workweek_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_scotland = models.BooleanField(null=True, blank=True)
    is_blind = models.BooleanField(null=True, blank=True)
    no_ni = models.BooleanField(null=True, blank=True)
    mca = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.event_type} {self.path} {self.status_code}"
