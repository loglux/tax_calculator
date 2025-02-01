from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .forms import TaxForm
from .models import TaxRate
from rest_framework import viewsets
from .serializers import TaxRateSerializer
from decimal import Decimal

# for get_default_year
from datetime import datetime

class TaxRateViewSet(viewsets.ModelViewSet):
    queryset = TaxRate.objects.all()
    serializer_class = TaxRateSerializer


def get_default_year():
    """
    Get current or last tax year available in DB
    """
    from datetime import datetime

    current_year = datetime.now().year
    current_month = datetime.now().month

    try:
        # Получаем последний доступный год из базы
        latest_year = TaxRate.objects.latest('year').year

        # Определяем текущий налоговый год
        if current_month < 4:  # Если до апреля, используем предыдущий календарный год
            current_tax_year = current_year - 1
        else:
            current_tax_year = current_year

        # Если последний год в базе >= текущего налогового года, возвращаем текущий год
        if latest_year >= current_tax_year:
            return current_tax_year
        return latest_year  # Если текущий год отсутствует, возвращаем последний доступный
    except TaxRate.DoesNotExist:
        # Если в базе нет данных, явно сигнализируем об этом
        raise ValueError("No tax years available in the database.")


def get_tax_rates(year):
    try:
        tax_rate = TaxRate.objects.get(year=year)
        return {
            'personal_allowance': tax_rate.personal_allowance,
            'basic_rate': tax_rate.basic_rate,
            'higher_rate': tax_rate.higher_rate,
            'additional_rate': tax_rate.additional_rate,
            'ni_threshold': tax_rate.ni_threshold,
            'ni_rate': tax_rate.ni_rate,
            'ni_additional_rate': tax_rate.ni_additional_rate,
            'starter_rate_scotland': tax_rate.starter_rate_scotland,
            'basic_rate_scotland': tax_rate.basic_rate_scotland,
            'intermediate_rate_scotland': tax_rate.intermediate_rate_scotland,
            'higher_rate_scotland': tax_rate.higher_rate_scotland,
            'top_rate_scotland': tax_rate.top_rate_scotland,
        }
    except TaxRate.DoesNotExist:
        return None

def calculate_tax_details(income, income_type, is_blind, no_ni, tax_rates, is_scotland, workweek_hours):
    if income_type == 'hourly':
        salary = Decimal(income) * Decimal(workweek_hours) * Decimal(52)
    else:
        salary = Decimal(income)
    income = salary

    personal_allowance = tax_rates['personal_allowance']
    personal_allowance_reduction = Decimal('0')

    if income > Decimal('100000'):
        personal_allowance_reduction = min(personal_allowance, (income - Decimal('100000')) / Decimal('2'))
        personal_allowance -= personal_allowance_reduction

    if is_blind:
        personal_allowance += Decimal('2500')

    taxable_income = max(Decimal('0'), income - personal_allowance)

    starter_rate_scotland_amount = Decimal('0')
    basic_rate_scotland_amount = Decimal('0')
    intermediate_rate_scotland_amount = Decimal('0')
    higher_rate_scotland_amount = Decimal('0')
    top_rate_scotland_amount = Decimal('0')

    if is_scotland:
        if taxable_income <= Decimal('2306'):
            starter_rate_scotland_amount = taxable_income * tax_rates['starter_rate_scotland']
        elif taxable_income <= Decimal('13991'):
            starter_rate_scotland_amount = Decimal('2306') * tax_rates['starter_rate_scotland']
            basic_rate_scotland_amount = (taxable_income - Decimal('2306')) * tax_rates['basic_rate_scotland']
        elif taxable_income <= Decimal('31092'):
            starter_rate_scotland_amount = Decimal('2306') * tax_rates['starter_rate_scotland']
            basic_rate_scotland_amount = (Decimal('13991') - Decimal('2306')) * tax_rates['basic_rate_scotland']
            intermediate_rate_scotland_amount = (taxable_income - Decimal('13991')) * tax_rates['intermediate_rate_scotland']
        elif taxable_income <= Decimal('125140'):
            starter_rate_scotland_amount = Decimal('2306') * tax_rates['starter_rate_scotland']
            basic_rate_scotland_amount = (Decimal('13991') - Decimal('2306')) * tax_rates['basic_rate_scotland']
            intermediate_rate_scotland_amount = (Decimal('31092') - Decimal('13991')) * tax_rates['intermediate_rate_scotland']
            higher_rate_scotland_amount = (taxable_income - Decimal('31092')) * tax_rates['higher_rate_scotland']
        else:
            starter_rate_scotland_amount = Decimal('2306') * tax_rates['starter_rate_scotland']
            basic_rate_scotland_amount = (Decimal('13991') - Decimal('2306')) * tax_rates['basic_rate_scotland']
            intermediate_rate_scotland_amount = (Decimal('31092') - Decimal('13991')) * tax_rates['intermediate_rate_scotland']
            higher_rate_scotland_amount = (Decimal('125140') - Decimal('31092')) * tax_rates['higher_rate_scotland']
            #higher_rate_scotland_amount = (taxable_income - Decimal('31092')) * tax_rates['higher_rate_scotland']
            top_rate_scotland_amount = (taxable_income - Decimal('125140')) * tax_rates['top_rate_scotland']

        tax_paid = starter_rate_scotland_amount + basic_rate_scotland_amount + intermediate_rate_scotland_amount + higher_rate_scotland_amount + top_rate_scotland_amount
    else:
        if taxable_income <= Decimal('37700'):
            tax_paid = taxable_income * (tax_rates['basic_rate'] / Decimal('100'))
        elif taxable_income <= Decimal('125140'):
            tax_paid = Decimal('37700') * (tax_rates['basic_rate'] / Decimal('100')) + (taxable_income - Decimal('37700')) * (tax_rates['higher_rate'] / Decimal('100'))
        else:
            tax_paid = Decimal('37700') * (tax_rates['basic_rate'] / Decimal('100')) + (Decimal('125140') - Decimal('37700')) * (tax_rates['higher_rate'] / Decimal('100')) + (taxable_income - Decimal('125140')) * (tax_rates['additional_rate'] / Decimal('100'))

    if no_ni:
        ni_paid = Decimal('0')
    else:
        ni_paid = max(Decimal('0'), min(income - tax_rates['ni_threshold'], Decimal('40500')) * (tax_rates['ni_rate'] / Decimal('100')) + max(Decimal('0'), income - Decimal('50000')) * (tax_rates['ni_additional_rate'] / Decimal('100')))

    total_deduction = tax_paid + ni_paid
    take_home = income - total_deduction

    monthly_salary = salary / 12
    weekly_salary = salary / 52
    hourly_salary = salary / (52 * workweek_hours)

    monthly_personal_allowance = personal_allowance / 12
    weekly_personal_allowance = personal_allowance / 52
    hourly_personal_allowance = personal_allowance / (52 * workweek_hours)

    monthly_tax_paid = tax_paid / 12
    weekly_tax_paid = tax_paid / 52
    hourly_tax_paid = tax_paid / (52 * workweek_hours)

    monthly_ni_paid = ni_paid / 12
    weekly_ni_paid = ni_paid / 52
    hourly_ni_paid = ni_paid / (52 * workweek_hours)

    monthly_total_deduction = total_deduction / 12
    weekly_total_deduction = total_deduction / 52
    hourly_total_deduction = total_deduction / (52 * workweek_hours)

    monthly_take_home = take_home / 12
    weekly_take_home = take_home / 52
    hourly_take_home = take_home / (52 * workweek_hours)

    return {
        'tax_paid': round(tax_paid, 2),
        'ni_paid': round(ni_paid, 2),
        'total_deduction': round(total_deduction, 2),
        'take_home': round(take_home, 2),
        'personal_allowance_reduction': round(personal_allowance_reduction, 2),
        'starter_rate_scotland_amount': round(starter_rate_scotland_amount, 2),
        'basic_rate_scotland_amount': round(basic_rate_scotland_amount, 2),
        'intermediate_rate_scotland_amount': round(intermediate_rate_scotland_amount, 2),
        'higher_rate_scotland_amount': round(higher_rate_scotland_amount, 2),
        'top_rate_scotland_amount': round(top_rate_scotland_amount, 2),
        'monthly_salary': round(monthly_salary, 2),
        'weekly_salary': round(weekly_salary, 2),
        'hourly_salary': round(hourly_salary, 2),
        'monthly_personal_allowance': round(monthly_personal_allowance, 2),
        'weekly_personal_allowance': round(weekly_personal_allowance, 2),
        'hourly_personal_allowance': round(hourly_personal_allowance, 2),
        'monthly_tax_paid': round(monthly_tax_paid, 2),
        'weekly_tax_paid': round(weekly_tax_paid, 2),
        'hourly_tax_paid': round(hourly_tax_paid, 2),
        'monthly_ni_paid': round(monthly_ni_paid, 2),
        'weekly_ni_paid': round(weekly_ni_paid, 2),
        'hourly_ni_paid': round(hourly_ni_paid, 2),
        'monthly_total_deduction': round(monthly_total_deduction, 2),
        'weekly_total_deduction': round(weekly_total_deduction, 2),
        'hourly_total_deduction': round(hourly_total_deduction, 2),
        'monthly_take_home': round(monthly_take_home, 2),
        'weekly_take_home': round(weekly_take_home, 2),
        'hourly_take_home': round(hourly_take_home, 2),
        'salary': round(salary, 2)  # Add this to return the correct salary
    }


def process_tax_calculation(data, year):
    income = data.get('income', 0)
    income_type = data.get('income_type', 'yearly')
    is_blind = data.get('is_blind', False)
    no_ni = data.get('no_ni', False)
    is_scotland = data.get('is_scotland', False)
    workweek_hours = Decimal(data.get('workweek_hours', 40))  # Default to 40 if not provided

    tax_rates = get_tax_rates(year)  # Используем переданный год
    if not tax_rates:
        return None, f'Tax rates not found for the year {year}.'

    tax_details = calculate_tax_details(income, income_type, is_blind, no_ni, tax_rates, is_scotland, workweek_hours)
    tax_details.update({
        'personal_allowance': f'{tax_rates["personal_allowance"]:,.2f}',
        'salary': f'{tax_details["salary"]:,.2f}',  # Ensure the correct salary is displayed
        'is_scotland': is_scotland,
    })

    return tax_details, None

def calculator_view(request):
    try:
        year = get_default_year()  # Получаем текущий или последний доступный год
    except ValueError as e:
        return render(request, 'calculator/error.html', {'error_message': str(e)})

    if request.method == 'POST':
        form = TaxForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            selected_year = int(data.get('tax_year', year))  # Используем выбранный год или дефолтный
            context, error = process_tax_calculation(data, selected_year)
            if error:
                return render(request, 'calculator/index.html', {'form': form, 'error': error, 'year': selected_year})
            context['form'] = form
            context['year'] = selected_year
            return render(request, 'calculator/index.html', context)
    else:
        form = TaxForm(initial={'tax_year': year})
    return render(request, 'calculator/index.html', {'form': form, 'year': year})


@csrf_exempt
@api_view(['POST'])
def calculate_tax(request):
    year = int(request.data.get('tax_year', get_default_year()))  # Используем переданный год или дефолтный
    context, error = process_tax_calculation(request.data, year)
    if error:
        return Response({'error': error}, status=404)
    return Response(context)


