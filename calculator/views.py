from decimal import ROUND_HALF_UP, Decimal

from django.shortcuts import render
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .forms import TaxForm
from .models import TaxRate
from .serializers import TaxRateSerializer

WEEKS_IN_YEAR = Decimal("52")
MONTHS_IN_YEAR = Decimal("12")
HUNDRED = Decimal("100")
PENNY = Decimal("0.01")
WEEKLY_NI_TABLE_STEP = Decimal("1")
MONTHLY_NI_TABLE_STEP = Decimal("4")


class TaxRateViewSet(viewsets.ModelViewSet):
    queryset = TaxRate.objects.all()
    serializer_class = TaxRateSerializer


class PublicTokenObtainPairView(TokenObtainPairView):
    authentication_classes = []
    permission_classes = [AllowAny]


class PublicTokenRefreshView(TokenRefreshView):
    authentication_classes = []
    permission_classes = [AllowAny]


def get_default_year():
    """
    Get current or last tax year available in DB
    """
    from datetime import datetime

    current_year = datetime.now().year
    current_month = datetime.now().month

    try:
        latest_year = TaxRate.objects.latest("year").year

        if current_month < 4:
            current_tax_year = current_year - 1
        else:
            current_tax_year = current_year

        if latest_year >= current_tax_year:
            return current_tax_year
        return latest_year
    except TaxRate.DoesNotExist:
        raise ValueError("No tax years available in the database.")


def get_tax_rates(year):
    return TaxRate.objects.filter(year=year).order_by("-id").first()


def _annual_income(income, income_type, workweek_hours):
    if income_type == "hourly":
        return Decimal(income) * Decimal(workweek_hours) * WEEKS_IN_YEAR
    return Decimal(income)


def _apply_mca_relief(tax_paid, tax_rates, mca_enabled):
    if not mca_enabled:
        return tax_paid, Decimal("0")
    mca_relief = min(Decimal(tax_rates.mca_relief_amount), max(Decimal("0"), tax_paid))
    return tax_paid - mca_relief, mca_relief


def _ni_paid(
    income,
    tax_rates,
    no_ni,
    period_factor=Decimal("1"),
    hmrc_stepwise=False,
    payroll_frequency="annual",
):
    if no_ni:
        return Decimal("0")

    ni_threshold = Decimal(tax_rates.ni_threshold) * period_factor
    ni_upper_limit = Decimal(tax_rates.ni_upper_limit) * period_factor

    main_rate = Decimal(tax_rates.ni_rate) / HUNDRED
    additional_rate = Decimal(tax_rates.ni_additional_rate) / HUNDRED

    income_for_ni = Decimal(income)
    if hmrc_stepwise:
        ni_table_step = (
            WEEKLY_NI_TABLE_STEP
            if payroll_frequency == "weekly"
            else MONTHLY_NI_TABLE_STEP if payroll_frequency == "monthly" else Decimal("0")
        )
        if ni_table_step > 0:
            income_for_ni = _floor_to_step(income_for_ni, ni_table_step)
            ni_threshold = _floor_to_step(ni_threshold, ni_table_step)
            ni_upper_limit = _floor_to_step(ni_upper_limit, ni_table_step)

    income_above_threshold = max(Decimal("0"), income_for_ni - ni_threshold)
    main_band = max(Decimal("0"), min(income_above_threshold, ni_upper_limit - ni_threshold))
    income_above_upper = max(Decimal("0"), income_above_threshold - (ni_upper_limit - ni_threshold))

    ni_main = _to_money(main_band * main_rate) if hmrc_stepwise else main_band * main_rate
    ni_additional = (
        _to_money(income_above_upper * additional_rate)
        if hmrc_stepwise
        else income_above_upper * additional_rate
    )

    total_ni = ni_main + ni_additional
    return _to_money(total_ni) if hmrc_stepwise else total_ni


def _to_money(value):
    return Decimal(value).quantize(PENNY, rounding=ROUND_HALF_UP)


def _floor_to_step(value, step):
    value_dec = Decimal(value)
    step_dec = Decimal(step)
    if step_dec <= 0:
        return value_dec
    return (value_dec // step_dec) * step_dec


def _hmrc_tax_from_bands(taxable_income, bands):
    remaining = max(Decimal("0"), Decimal(taxable_income))
    total_tax = Decimal("0")

    for band_size, rate in bands:
        if remaining <= 0:
            break
        taxable_in_band = min(remaining, band_size) if band_size is not None else remaining
        total_tax += _to_money(taxable_in_band * rate)
        remaining -= taxable_in_band

    return _to_money(total_tax)


def _rate_fraction(raw_rate):
    rate = Decimal(raw_rate)
    return rate / HUNDRED if rate > Decimal("1") else rate


def _periods_in_year(payroll_frequency):
    if payroll_frequency == "weekly":
        return WEEKS_IN_YEAR
    if payroll_frequency == "monthly":
        return MONTHS_IN_YEAR
    return Decimal("1")


def _apply_allowance_taper(annual_allowance, annual_income, taper_threshold):
    if annual_allowance <= Decimal("0"):
        return annual_allowance, Decimal("0")

    if annual_income <= taper_threshold:
        return annual_allowance, Decimal("0")

    reduction = min(annual_allowance, (annual_income - taper_threshold) / Decimal("2"))
    return annual_allowance - reduction, reduction


def _parse_tax_code_metadata(tax_code):
    code = str(tax_code).strip().upper().replace(" ", "")
    if not code:
        raise ValueError("tax_code is required for hmrc_paye mode.")

    force_non_cumulative = False
    for marker in ("W1", "M1"):
        if code.endswith(marker):
            code = code[: -len(marker)]
            force_non_cumulative = True
            break
    if code.endswith("X"):
        code = code[:-1]
        force_non_cumulative = True

    region_hint = None
    if code and code[0] in ("S", "C"):
        region_hint = "scotland" if code[0] == "S" else "rUK"
        code = code[1:]

    if not code:
        raise ValueError(f"Invalid tax code: {tax_code}")

    return {
        "core_code": code,
        "force_non_cumulative": force_non_cumulative,
        "region_hint": region_hint,
    }


def _parse_tax_code_annual_allowance(tax_code):
    parsed = _parse_tax_code_metadata(tax_code)
    code = parsed["core_code"]

    if code in ("NT", "BR", "D0", "D1"):
        return Decimal("0")

    if code.endswith("M") or code.endswith("N"):
        suffix = code[-1]
        digits = "".join(ch for ch in code[:-1] if ch.isdigit())
        if not digits:
            raise ValueError(f"Invalid tax code: {tax_code}")
        allowance = Decimal(digits) * Decimal("10")
        marriage_transfer = Decimal("1260")
        return allowance + marriage_transfer if suffix == "M" else allowance - marriage_transfer

    if code.startswith("K"):
        digits = "".join(ch for ch in code[1:] if ch.isdigit())
        if not digits:
            raise ValueError(f"Invalid tax code: {tax_code}")
        return Decimal(digits) * Decimal("-10")

    digits = "".join(ch for ch in code if ch.isdigit())
    if not digits:
        raise ValueError(f"Invalid tax code: {tax_code}")
    return Decimal(digits) * Decimal("10")


def _parse_special_tax_code_rate(tax_code, tax_rates, is_scotland):
    parsed = _parse_tax_code_metadata(tax_code)
    code = parsed["core_code"]

    if code == "NT":
        return Decimal("0")
    if code == "BR":
        return _rate_fraction(
            tax_rates.basic_rate_scotland if is_scotland else tax_rates.basic_rate
        )
    if code == "D0":
        return _rate_fraction(
            tax_rates.higher_rate_scotland if is_scotland else tax_rates.higher_rate
        )
    if code == "D1":
        return _rate_fraction(
            tax_rates.top_rate_scotland if is_scotland else tax_rates.additional_rate
        )
    return None


def _rest_uk_tax_with_scaled_thresholds(taxable_income, tax_rates, period_factor):
    basic_threshold = Decimal(tax_rates.basic_threshold) * period_factor
    higher_threshold = Decimal(tax_rates.higher_threshold) * period_factor

    basic_rate = _rate_fraction(tax_rates.basic_rate)
    higher_rate = _rate_fraction(tax_rates.higher_rate)
    additional_rate = _rate_fraction(tax_rates.additional_rate)

    bands = (
        (basic_threshold, basic_rate),
        (max(Decimal("0"), higher_threshold - basic_threshold), higher_rate),
        (None, additional_rate),
    )
    return _hmrc_tax_from_bands(taxable_income, bands)


def _scotland_tax_with_scaled_thresholds(taxable_income, tax_rates, period_factor):
    starter_threshold = Decimal(tax_rates.starter_threshold_scotland) * period_factor
    basic_threshold = Decimal(tax_rates.basic_threshold_scotland) * period_factor
    intermediate_threshold = Decimal(tax_rates.intermediate_threshold_scotland) * period_factor
    higher_threshold = Decimal(tax_rates.higher_threshold_scotland) * period_factor
    advanced_threshold = Decimal(tax_rates.advanced_threshold_scotland) * period_factor

    starter_rate = _rate_fraction(tax_rates.starter_rate_scotland)
    basic_rate = _rate_fraction(tax_rates.basic_rate_scotland)
    intermediate_rate = _rate_fraction(tax_rates.intermediate_rate_scotland)
    higher_rate = _rate_fraction(tax_rates.higher_rate_scotland)
    advanced_rate = _rate_fraction(tax_rates.advanced_rate_scotland)
    top_rate = _rate_fraction(tax_rates.top_rate_scotland)

    bands = (
        (starter_threshold, starter_rate),
        (max(Decimal("0"), basic_threshold - starter_threshold), basic_rate),
        (
            max(Decimal("0"), intermediate_threshold - basic_threshold),
            intermediate_rate,
        ),
        (max(Decimal("0"), higher_threshold - intermediate_threshold), higher_rate),
        (max(Decimal("0"), advanced_threshold - higher_threshold), advanced_rate),
        (None, top_rate),
    )
    return _hmrc_tax_from_bands(taxable_income, bands)


def calculate_tax_details_hmrc_paye(
    income,
    income_type,
    is_blind,
    no_ni,
    tax_rates,
    is_scotland,
    workweek_hours,
    tax_code,
    payroll_frequency,
    hmrc_basis,
    period_number,
    ytd_tax_paid,
    ytd_gross,
    mca,
):
    salary = _annual_income(income, income_type, workweek_hours)
    periods = _periods_in_year(payroll_frequency)
    parsed_tax_code = _parse_tax_code_metadata(tax_code)
    effective_is_scotland = is_scotland
    if parsed_tax_code["region_hint"] == "scotland":
        effective_is_scotland = True
    elif parsed_tax_code["region_hint"] == "rUK":
        effective_is_scotland = False

    effective_hmrc_basis = (
        "non_cumulative" if parsed_tax_code["force_non_cumulative"] else hmrc_basis
    )
    period_number = max(1, min(int(period_number), int(periods)))
    period_gross = salary / periods
    period_factor = Decimal("1") / periods

    special_rate = _parse_special_tax_code_rate(tax_code, tax_rates, effective_is_scotland)
    annual_allowance = Decimal("0")
    personal_allowance_reduction = Decimal("0")

    if special_rate is not None:
        if effective_hmrc_basis == "cumulative":
            gross_to_date = Decimal(ytd_gross) + period_gross
            tax_to_date = _to_money(gross_to_date * special_rate)
            period_tax = _to_money(tax_to_date - Decimal(ytd_tax_paid))
        else:
            period_tax = _to_money(period_gross * special_rate)
    else:
        annual_allowance = _parse_tax_code_annual_allowance(tax_code)
        if is_blind:
            annual_allowance += Decimal(tax_rates.blind_allowance)
        annual_allowance, personal_allowance_reduction = _apply_allowance_taper(
            annual_allowance,
            salary,
            Decimal(tax_rates.personal_allowance_taper_threshold),
        )

        if effective_hmrc_basis == "cumulative":
            gross_to_date = Decimal(ytd_gross) + period_gross
            allowance_to_date = _to_money(annual_allowance * (Decimal(period_number) / periods))
            taxable_to_date = max(Decimal("0"), _to_money(gross_to_date - allowance_to_date))
            tax_fn = (
                _scotland_tax_with_scaled_thresholds
                if effective_is_scotland
                else _rest_uk_tax_with_scaled_thresholds
            )
            tax_to_date = _to_money(
                tax_fn(taxable_to_date, tax_rates, Decimal(period_number) / periods)
            )
            period_tax = _to_money(tax_to_date - Decimal(ytd_tax_paid))
        else:
            taxable_period = max(
                Decimal("0"), _to_money(period_gross - (annual_allowance / periods))
            )
            tax_fn = (
                _scotland_tax_with_scaled_thresholds
                if effective_is_scotland
                else _rest_uk_tax_with_scaled_thresholds
            )
            period_tax = _to_money(tax_fn(taxable_period, tax_rates, period_factor))

    period_ni = _ni_paid(
        period_gross,
        tax_rates,
        no_ni,
        period_factor=period_factor,
        hmrc_stepwise=True,
        payroll_frequency=payroll_frequency,
    )

    annual_tax_estimate = _to_money(period_tax * periods)
    annual_tax_estimate, mca_relief_amount = _apply_mca_relief(annual_tax_estimate, tax_rates, mca)
    annual_ni_estimate = _to_money(period_ni * periods)
    annual_take_home = _to_money(salary - annual_tax_estimate - annual_ni_estimate)

    return {
        "tax_paid": _to_money(annual_tax_estimate),
        "ni_paid": _to_money(annual_ni_estimate),
        "total_deduction": _to_money(annual_tax_estimate + annual_ni_estimate),
        "take_home": _to_money(annual_take_home),
        "personal_allowance_reduction": _to_money(personal_allowance_reduction),
        "starter_rate_scotland_amount": _to_money(Decimal("0")),
        "basic_rate_scotland_amount": _to_money(Decimal("0")),
        "intermediate_rate_scotland_amount": _to_money(Decimal("0")),
        "higher_rate_scotland_amount": _to_money(Decimal("0")),
        "top_rate_scotland_amount": _to_money(Decimal("0")),
        "advanced_rate_scotland_amount": _to_money(Decimal("0")),
        "mca_relief_amount": _to_money(mca_relief_amount),
        "monthly_salary": _to_money(salary / MONTHS_IN_YEAR),
        "weekly_salary": _to_money(salary / WEEKS_IN_YEAR),
        "hourly_salary": _to_money(salary / (WEEKS_IN_YEAR * workweek_hours)),
        "monthly_personal_allowance": _to_money(annual_allowance / MONTHS_IN_YEAR),
        "weekly_personal_allowance": _to_money(annual_allowance / WEEKS_IN_YEAR),
        "hourly_personal_allowance": _to_money(annual_allowance / (WEEKS_IN_YEAR * workweek_hours)),
        "monthly_tax_paid": _to_money(annual_tax_estimate / MONTHS_IN_YEAR),
        "weekly_tax_paid": _to_money(annual_tax_estimate / WEEKS_IN_YEAR),
        "hourly_tax_paid": _to_money(annual_tax_estimate / (WEEKS_IN_YEAR * workweek_hours)),
        "monthly_ni_paid": _to_money(annual_ni_estimate / MONTHS_IN_YEAR),
        "weekly_ni_paid": _to_money(annual_ni_estimate / WEEKS_IN_YEAR),
        "hourly_ni_paid": _to_money(annual_ni_estimate / (WEEKS_IN_YEAR * workweek_hours)),
        "monthly_total_deduction": _to_money(
            (annual_tax_estimate + annual_ni_estimate) / MONTHS_IN_YEAR
        ),
        "weekly_total_deduction": _to_money(
            (annual_tax_estimate + annual_ni_estimate) / WEEKS_IN_YEAR
        ),
        "hourly_total_deduction": _to_money(
            (annual_tax_estimate + annual_ni_estimate) / (WEEKS_IN_YEAR * workweek_hours)
        ),
        "monthly_take_home": _to_money(annual_take_home / MONTHS_IN_YEAR),
        "weekly_take_home": _to_money(annual_take_home / WEEKS_IN_YEAR),
        "hourly_take_home": _to_money(annual_take_home / (WEEKS_IN_YEAR * workweek_hours)),
        "salary": _to_money(salary),
        "hmrc_period_tax": _to_money(period_tax),
        "hmrc_period_ni": _to_money(period_ni),
        "hmrc_period_take_home": _to_money(period_gross - period_tax - period_ni),
        "hmrc_period_gross": _to_money(period_gross),
        "hmrc_tax_code": str(tax_code).upper(),
        "hmrc_basis": effective_hmrc_basis,
        "hmrc_region": "scotland" if effective_is_scotland else "rUK",
        "hmrc_payroll_frequency": payroll_frequency,
    }


def process_tax_calculation(data, year):
    income = data.get("income", 0)
    income_type = data.get("income_type", "yearly")
    is_blind = data.get("is_blind", False)
    no_ni = data.get("no_ni", False)
    mca = data.get("mca", False)
    is_scotland = data.get("is_scotland", False)
    workweek_hours = Decimal(data.get("workweek_hours", 40))
    tax_rate_obj = get_tax_rates(year)
    if not tax_rate_obj:
        return None, f"Tax rates not found for the year {year}."

    parsed_tax_code = _parse_tax_code_metadata(data.get("tax_code") or "1257L")
    hmrc_context_fields = (
        "payroll_frequency",
        "hmrc_basis",
        "period_number",
        "ytd_tax_paid",
        "ytd_gross",
    )
    uses_default_hmrc_profile = not any(
        data.get(field) not in (None, "", 0, "0") for field in hmrc_context_fields
    ) and not parsed_tax_code["force_non_cumulative"]
    hmrc_strict = str(data.get("hmrc_strict", "false")).lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if hmrc_strict and uses_default_hmrc_profile:
        return None, (
            "HMRC strict mode requires payroll context: "
            "period_number, ytd_gross, ytd_tax_paid, "
            "and optional payroll_frequency/hmrc_basis."
        )

    tax_details = calculate_tax_details_hmrc_paye(
        income=income,
        income_type=income_type,
        is_blind=is_blind,
        no_ni=no_ni,
        tax_rates=tax_rate_obj,
        is_scotland=is_scotland,
        workweek_hours=workweek_hours,
        tax_code=data.get("tax_code") or "1257L",
        payroll_frequency=data.get("payroll_frequency") or "monthly",
        hmrc_basis=data.get("hmrc_basis") or "cumulative",
        period_number=int(data.get("period_number") or 1),
        ytd_tax_paid=Decimal(data.get("ytd_tax_paid") or 0),
        ytd_gross=Decimal(data.get("ytd_gross") or 0),
        mca=mca,
    )
    tax_details["hmrc_precision_level"] = "approximate" if uses_default_hmrc_profile else "strict"
    if uses_default_hmrc_profile:
        tax_details["hmrc_precision_note"] = (
            "Default HMRC profile in use (monthly/cumulative, period 1, YTD 0)."
        )

    tax_details.update(
        {
            "personal_allowance": f"{tax_rate_obj.personal_allowance:,.2f}",
            "salary": f'{tax_details["salary"]:,.2f}',
            "is_scotland": is_scotland,
            "calculation_mode": "hmrc_paye",
            "has_result": True,
        }
    )

    return tax_details, None


def calculator_view(request):
    try:
        year = get_default_year()
    except ValueError as e:
        return render(request, "calculator/error.html", {"error_message": str(e)})

    if request.method == "POST":
        form = TaxForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            selected_year = int(data.get("tax_year", year))
            context, error = process_tax_calculation(data, selected_year)
            if error:
                return render(
                    request,
                    "calculator/index.html",
                    {"form": form, "error": error, "year": selected_year},
                )
            context["form"] = form
            context["year"] = selected_year
            return render(request, "calculator/index.html", context)
    else:
        form = TaxForm(initial={"tax_year": year})
    return render(request, "calculator/index.html", {"form": form, "year": year})


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def calculate_tax(request):
    year = int(request.data.get("tax_year", get_default_year()))
    context, error = process_tax_calculation(request.data, year)
    if error:
        return Response({"error": error}, status=404)
    return Response(context)
