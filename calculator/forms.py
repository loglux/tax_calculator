from django import forms
from .models import TaxRate

class TaxForm(forms.Form):
    income = forms.DecimalField(
        label='Income £',
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    income_type = forms.ChoiceField(
        choices=[('yearly', 'Yearly'), ('hourly', 'Hourly')],
        label='Income Type',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_blind = forms.BooleanField(
        label='Blind',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    no_ni = forms.BooleanField(
        label='No NI',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    mca = forms.BooleanField(
        label='MCA',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_scotland = forms.BooleanField(
        label='Scotland',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    workweek_hours = forms.ChoiceField(
        choices=[(40, '40 hours'), (37.5, '37.5 hours')],
        label='Workweek Hours',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Правильная реализация
    @staticmethod
    def generate_tax_year_choices():
        years = TaxRate.objects.values_list('year', flat=True).order_by('year')
        return [(year, f"{year}/{year + 1 - 2000}") for year in years]

    tax_year = forms.ChoiceField(
        choices=[],  # по умолчанию пусто!
        label='Tax Year',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tax_year'].choices = TaxForm.generate_tax_year_choices()
