from django.contrib import admin
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import TaxRate, UsageEvent


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ("year", "personal_allowance", "basic_rate", "higher_rate", "additional_rate")
    ordering = ("-year",)


@admin.register(UsageEvent)
class UsageEventAdmin(admin.ModelAdmin):
    change_list_template = "admin/calculator/usageevent/change_list.html"
    list_display = (
        "created_at",
        "event_type",
        "path",
        "method",
        "status_code",
        "client_ip",
        "tax_year",
        "income",
        "income_type",
        "workweek_hours",
        "is_scotland",
        "no_ni",
        "mca",
    )
    list_filter = (
        "event_type",
        "method",
        "status_code",
        "tax_year",
        "income_type",
        "is_scotland",
        "is_blind",
        "no_ni",
        "mca",
    )
    search_fields = ("path", "client_ip", "client_hash", "user_agent")
    readonly_fields = (
        "created_at",
        "event_type",
        "path",
        "method",
        "status_code",
        "client_ip",
        "client_hash",
        "user_agent",
        "tax_year",
        "income",
        "income_type",
        "workweek_hours",
        "is_scotland",
        "is_blind",
        "no_ni",
        "mca",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        now = timezone.now()
        day_ago = now - timezone.timedelta(days=1)
        week_ago = now - timezone.timedelta(days=7)
        month_ago = now - timezone.timedelta(days=30)

        qs = UsageEvent.objects.all()
        calculate_qs = qs.filter(event_type=UsageEvent.EVENT_CALCULATE_SUBMIT)

        summary = {
            "events_today": qs.filter(created_at__gte=day_ago).count(),
            "events_7d": qs.filter(created_at__gte=week_ago).count(),
            "events_30d": qs.filter(created_at__gte=month_ago).count(),
            "unique_clients_30d": (
                qs.filter(created_at__gte=month_ago)
                .exclude(client_hash="")
                .values("client_hash")
                .distinct()
                .count()
            ),
            "calc_submits_30d": calculate_qs.filter(created_at__gte=month_ago).count(),
            "page_views_30d": qs.filter(
                created_at__gte=month_ago, event_type=UsageEvent.EVENT_PAGE_VIEW
            ).count(),
            "api_calls_30d": qs.filter(
                created_at__gte=month_ago, event_type=UsageEvent.EVENT_API_CALL
            ).count(),
            "errors_30d": qs.filter(created_at__gte=month_ago, status_code__gte=400).count(),
        }
        summary["conversion_30d"] = (
            round((summary["calc_submits_30d"] / summary["page_views_30d"]) * 100, 2)
            if summary["page_views_30d"]
            else 0
        )

        top_tax_years = (
            calculate_qs.exclude(tax_year__isnull=True)
            .exclude(tax_year=0)
            .values("tax_year")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        top_hours = (
            calculate_qs.exclude(workweek_hours__isnull=True)
            .values("workweek_hours")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        option_usage = calculate_qs.aggregate(
            scotland_on=Count("id", filter=Q(is_scotland=True)),
            blind_on=Count("id", filter=Q(is_blind=True)),
            no_ni_on=Count("id", filter=Q(no_ni=True)),
            mca_on=Count("id", filter=Q(mca=True)),
        )
        top_incomes = (
            calculate_qs.exclude(income__isnull=True)
            .values("income")
            .annotate(total=Count("id"))
            .order_by("-total", "-income")[:10]
        )
        income_buckets = calculate_qs.aggregate(
            lt_30k=Count("id", filter=Q(income__lt=30000)),
            bt_30_50=Count("id", filter=Q(income__gte=30000, income__lt=50000)),
            bt_50_100=Count("id", filter=Q(income__gte=50000, income__lt=100000)),
            ge_100=Count("id", filter=Q(income__gte=100000)),
        )
        daily_activity = (
            qs.filter(created_at__gte=month_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                events=Count("id"),
                page_views=Count("id", filter=Q(event_type=UsageEvent.EVENT_PAGE_VIEW)),
                calc_submits=Count(
                    "id", filter=Q(event_type=UsageEvent.EVENT_CALCULATE_SUBMIT)
                ),
                api_calls=Count("id", filter=Q(event_type=UsageEvent.EVENT_API_CALL)),
                errors=Count("id", filter=Q(status_code__gte=400)),
            )
            .order_by("day")
        )

        context = {
            "usage_summary": summary,
            "top_tax_years": list(top_tax_years),
            "top_hours": list(top_hours),
            "option_usage": option_usage,
            "top_incomes": list(top_incomes),
            "income_buckets": income_buckets,
            "daily_activity": list(daily_activity),
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)
