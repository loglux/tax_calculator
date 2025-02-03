from django.db import models

class TaxRate(models.Model):
    year = models.IntegerField()

    # Личный необлагаемый минимум
    personal_allowance = models.DecimalField(max_digits=10, decimal_places=2)
    # Сумма, выше которой сокращается personal_allowance
    personal_allowance_taper_threshold = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=100000
    )

    # Ставки и пороги для обычной части Великобритании
    basic_rate = models.DecimalField(max_digits=5, decimal_places=2)
    higher_rate = models.DecimalField(max_digits=5, decimal_places=2)
    additional_rate = models.DecimalField(max_digits=5, decimal_places=2)

    basic_threshold = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=37700
    )
    higher_threshold = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=125140
    )

    # National Insurance
    ni_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    ni_rate = models.DecimalField(max_digits=5, decimal_places=2)
    ni_additional_rate = models.DecimalField(max_digits=5, decimal_places=2)
    ni_upper_limit = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=50000
    )

    # Шотландские ставки
    starter_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    basic_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    intermediate_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    higher_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    top_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Шотландские пороги
    starter_threshold_scotland = models.DecimalField(max_digits=10, decimal_places=2, default=2306)
    basic_threshold_scotland = models.DecimalField(max_digits=10, decimal_places=2, default=13991)
    intermediate_threshold_scotland = models.DecimalField(max_digits=10, decimal_places=2, default=31092)
    higher_threshold_scotland = models.DecimalField(max_digits=10, decimal_places=2, default=125140)

    def __str__(self):
        return f"{self.year} Tax Rates"
