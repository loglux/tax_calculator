from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .forms import TaxForm
from .models import TaxRate
from rest_framework import viewsets
from .serializers import TaxRateSerializer
from decimal import Decimal


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
        # Get the last available year from DB
        latest_year = TaxRate.objects.latest('year').year

        # Get the current taxable year
        if current_month < 4:  # Если до апреля, используем предыдущий календарный год
            current_tax_year = current_year - 1
        else:
            current_tax_year = current_year

        # if the last year in DB >= current taxable year, return the current year.
        if latest_year >= current_tax_year:
            return current_tax_year
        return latest_year  # If current year is missing, return last available year
    except TaxRate.DoesNotExist:
        # If no data in DB, raise the Error
        raise ValueError("No tax years available in the database.")


def get_tax_rates(year):
    try:
        return TaxRate.objects.get(year=year)
    except TaxRate.DoesNotExist:
        return None


def calculate_tax_details(
    income,
    income_type,
    is_blind,
    no_ni,
    tax_rates,
    is_scotland,
    workweek_hours
):
    """
    Полностью убираем хардкод: все пороги и ставки подтягиваем из tax_rates.
    """
    # 1. Годовой доход (преобразуем, если почасовая ставка)
    if income_type == 'hourly':
        salary = Decimal(income) * Decimal(workweek_hours) * Decimal(52)
    else:
        salary = Decimal(income)

    # Чтобы код дальше был единообразным:
    income = salary

    # 2. Personal allowance из БД
    personal_allowance = Decimal(tax_rates.personal_allowance)
    personal_allowance_reduction = Decimal('0')

    # Порог, начиная с которого уменьшается personal allowance
    taper_threshold = Decimal(tax_rates.personal_allowance_taper_threshold)

    if income > taper_threshold:
        # По британским правилам: за каждые 2 фунта сверх порога уменьшается на 1 фунт
        personal_allowance_reduction = min(
            personal_allowance,
            (income - taper_threshold) / Decimal('2')
        )
        personal_allowance -= personal_allowance_reduction

    # 3. Blind allowance (всё ещё хардкод 2500,
    # но при желании можно хранить и это в базе)
    if is_blind:
        personal_allowance += Decimal('2500')

    # 4. Налогооблагаемый доход
    taxable_income = max(Decimal('0'), income - personal_allowance)

    # 5. Подготовка переменных для Шотландии
    starter_rate_scotland_amount = Decimal('0')
    basic_rate_scotland_amount = Decimal('0')
    intermediate_rate_scotland_amount = Decimal('0')
    higher_rate_scotland_amount = Decimal('0')
    top_rate_scotland_amount = Decimal('0')

    # Прочитаем шотландские пороги
    starter_threshold_sco = Decimal(tax_rates.starter_threshold_scotland)
    basic_threshold_sco = Decimal(tax_rates.basic_threshold_scotland)
    intermediate_threshold_sco = Decimal(tax_rates.intermediate_threshold_scotland)
    higher_threshold_sco = Decimal(tax_rates.higher_threshold_scotland)

    # Прочитаем шотландские ставки
    starter_rate_sco = Decimal(tax_rates.starter_rate_scotland)
    basic_rate_sco = Decimal(tax_rates.basic_rate_scotland)
    intermediate_rate_sco = Decimal(tax_rates.intermediate_rate_scotland)
    higher_rate_sco = Decimal(tax_rates.higher_rate_scotland)
    top_rate_sco = Decimal(tax_rates.top_rate_scotland)

    # Прочитаем "обычные" (не-Шотландия) пороги
    basic_threshold = Decimal(tax_rates.basic_threshold)   # 37700
    higher_threshold = Decimal(tax_rates.higher_threshold) # 125140

    # Прочитаем ставки (делим на 100, т.к. храним 20.00 = 20%)
    basic_rate = Decimal(tax_rates.basic_rate) / Decimal('100')
    higher_rate = Decimal(tax_rates.higher_rate) / Decimal('100')
    additional_rate = Decimal(tax_rates.additional_rate) / Decimal('100')

    # 6. Расчёт налога (Шотландия vs остальная Британия)
    if is_scotland:
        if taxable_income <= starter_threshold_sco:
            starter_rate_scotland_amount = taxable_income * starter_rate_sco
        elif taxable_income <= basic_threshold_sco:
            starter_rate_scotland_amount = starter_threshold_sco * starter_rate_sco
            basic_rate_scotland_amount = (taxable_income - starter_threshold_sco) * basic_rate_sco
        elif taxable_income <= intermediate_threshold_sco:
            starter_rate_scotland_amount = starter_threshold_sco * starter_rate_sco
            basic_rate_scotland_amount = (basic_threshold_sco - starter_threshold_sco) * basic_rate_sco
            intermediate_rate_scotland_amount = (taxable_income - basic_threshold_sco) * intermediate_rate_sco
        elif taxable_income <= higher_threshold_sco:
            starter_rate_scotland_amount = starter_threshold_sco * starter_rate_sco
            basic_rate_scotland_amount = (basic_threshold_sco - starter_threshold_sco) * basic_rate_sco
            intermediate_rate_scotland_amount = (intermediate_threshold_sco - basic_threshold_sco) * intermediate_rate_sco
            higher_rate_scotland_amount = (taxable_income - intermediate_threshold_sco) * higher_rate_sco
        else:
            # всё, что выше higher_threshold_sco, попадает под top_rate_sco
            starter_rate_scotland_amount = starter_threshold_sco * starter_rate_sco
            basic_rate_scotland_amount = (basic_threshold_sco - starter_threshold_sco) * basic_rate_sco
            intermediate_rate_scotland_amount = (intermediate_threshold_sco - basic_threshold_sco) * intermediate_rate_sco
            higher_rate_scotland_amount = (higher_threshold_sco - intermediate_threshold_sco) * higher_rate_sco
            top_rate_scotland_amount = (taxable_income - higher_threshold_sco) * top_rate_sco

        tax_paid = (
            starter_rate_scotland_amount +
            basic_rate_scotland_amount +
            intermediate_rate_scotland_amount +
            higher_rate_scotland_amount +
            top_rate_scotland_amount
        )
    else:
        if taxable_income <= basic_threshold:
            tax_paid = taxable_income * basic_rate
        elif taxable_income <= higher_threshold:
            tax_paid = (
                basic_threshold * basic_rate +
                (taxable_income - basic_threshold) * higher_rate
            )
        else:
            tax_paid = (
                basic_threshold * basic_rate +
                (higher_threshold - basic_threshold) * higher_rate +
                (taxable_income - higher_threshold) * additional_rate
            )

    # 7. Расчёт National Insurance
    if no_ni:
        ni_paid = Decimal('0')
    else:
        # Порог (threshold) и верхний лимит (upper_limit) из БД
        ni_threshold_val = Decimal(tax_rates.ni_threshold)
        ni_upper_limit = Decimal(tax_rates.ni_upper_limit)

        main_rate = Decimal(tax_rates.ni_rate) / Decimal('100')
        additional_ni_rate = Decimal(tax_rates.ni_additional_rate) / Decimal('100')

        # Считаем доход, превышающий ni_threshold
        income_above_threshold = income - ni_threshold_val
        if income_above_threshold < 0:
            income_above_threshold = Decimal('0')

        # Всё, что выше ni_upper_limit, идёт по дополнительной ставке
        income_in_main_band = min(income_above_threshold, ni_upper_limit - ni_threshold_val)
        if income_in_main_band < 0:
            income_in_main_band = Decimal('0')

        ni_paid_main = income_in_main_band * main_rate

        # Проверяем, осталось ли что-то выше ni_upper_limit:
        income_above_upper = income_above_threshold - (ni_upper_limit - ni_threshold_val)
        if income_above_upper < 0:
            income_above_upper = Decimal('0')

        ni_paid_additional = income_above_upper * additional_ni_rate

        ni_paid = ni_paid_main + ni_paid_additional

    # 8. Суммарные удержания и чистый доход
    total_deduction = tax_paid + ni_paid
    take_home = income - total_deduction

    # 9. Эквиваленты по месяцам, неделям, часам
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
        'salary': round(salary, 2),
    }


def process_tax_calculation(data, year):
    income = data.get('income', 0)
    income_type = data.get('income_type', 'yearly')
    is_blind = data.get('is_blind', False)
    no_ni = data.get('no_ni', False)
    is_scotland = data.get('is_scotland', False)
    workweek_hours = Decimal(data.get('workweek_hours', 40))

    # now get_tax_rates return OBJECT TaxRate (or None)
    tax_rate_obj = get_tax_rates(year)
    if not tax_rate_obj:
        return None, f'Tax rates not found for the year {year}.'

    # Transfer object tax_rate_obj to calculate_tax_details
    tax_details = calculate_tax_details(
        income,
        income_type,
        is_blind,
        no_ni,
        tax_rate_obj,
        is_scotland,
        workweek_hours
    )

    """
    If we need to show some fields on the screen,
    we should add them into dictionary (UI context).
    But bear in mind, we get personal_allowance through attribute:
    """
    tax_details.update({
        'personal_allowance': f'{tax_rate_obj.personal_allowance:,.2f}',
        'salary': f'{tax_details["salary"]:,.2f}',
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


