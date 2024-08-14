from django import forms

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
"""    tax_year = forms.ChoiceField(
        choices=[('2021/22', '2021/22'), ('2022/23', '2022/23')],
        label='Tax Year',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    """