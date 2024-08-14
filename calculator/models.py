from django.db import models

class TaxRate(models.Model):
    year = models.IntegerField()
    personal_allowance = models.DecimalField(max_digits=10, decimal_places=2)
    basic_rate = models.DecimalField(max_digits=5, decimal_places=2)
    higher_rate = models.DecimalField(max_digits=5, decimal_places=2)
    additional_rate = models.DecimalField(max_digits=5, decimal_places=2)
    ni_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    ni_rate = models.DecimalField(max_digits=5, decimal_places=2)
    ni_additional_rate = models.DecimalField(max_digits=5, decimal_places=2)
    starter_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    basic_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    intermediate_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    higher_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    top_rate_scotland = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.year} Tax Rates"
