import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings

from .models import UsageEvent


class UsageTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            self._track_event(request, response)
        except Exception:
            # Tracking failures must never affect user requests.
            pass

        return response

    def _track_event(self, request, response):
        path = request.path
        event_type = None

        if path == "/calculator/" and request.method == "GET":
            event_type = UsageEvent.EVENT_PAGE_VIEW
        elif path == "/calculator/" and request.method == "POST":
            event_type = UsageEvent.EVENT_CALCULATE_SUBMIT
        elif path.startswith("/calculator/api/"):
            event_type = UsageEvent.EVENT_API_CALL
        else:
            return

        payload = self._extract_payload(request, event_type)
        client_ip = self._client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
        client_kind, is_bot = self._classify_client(user_agent)
        UsageEvent.objects.create(
            event_type=event_type,
            path=path[:255],
            method=request.method[:8],
            status_code=response.status_code,
            client_ip=client_ip,
            client_hash=self._client_hash(client_ip),
            client_kind=client_kind,
            is_bot=is_bot,
            user_agent=user_agent,
            tax_year=self._to_int(payload.get("tax_year")),
            income=self._to_decimal(payload.get("income")),
            income_type=str(payload.get("income_type", ""))[:16],
            workweek_hours=self._to_decimal(payload.get("workweek_hours")),
            is_scotland=self._to_bool(payload.get("is_scotland")),
            is_blind=self._to_bool(payload.get("is_blind")),
            no_ni=self._to_bool(payload.get("no_ni")),
            mca=self._to_bool(payload.get("mca")),
        )

    def _extract_payload(self, request, event_type):
        if event_type == UsageEvent.EVENT_CALCULATE_SUBMIT:
            return request.POST
        if event_type == UsageEvent.EVENT_API_CALL:
            content_type = request.META.get("CONTENT_TYPE", "")
            if "application/json" in content_type:
                try:
                    return json.loads(request.body.decode("utf-8") or "{}")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return {}
        return {}

    def _client_ip(self, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
        if not ip:
            ip = request.META.get("REMOTE_ADDR", "")
        return ip[:45] if ip else ""

    def _client_hash(self, ip):
        if not ip:
            return ""
        return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode("utf-8")).hexdigest()

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_decimal(value):
        try:
            return Decimal(str(value))
        except (TypeError, ValueError, InvalidOperation):
            return None

    @staticmethod
    def _to_bool(value):
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return None

    @staticmethod
    def _classify_client(user_agent):
        ua = (user_agent or "").lower()
        if not ua:
            return "unknown", False

        bot_markers = ("bot", "crawl", "spider", "slurp", "headless", "python-requests")
        if any(marker in ua for marker in bot_markers):
            return "bot", True

        if "mobile" in ua or "iphone" in ua or "android" in ua:
            if "ipad" in ua or "tablet" in ua:
                return "tablet", False
            return "mobile", False

        if "ipad" in ua or "tablet" in ua:
            return "tablet", False

        desktop_markers = ("windows", "macintosh", "x11", "linux")
        if any(marker in ua for marker in desktop_markers):
            return "desktop", False

        return "unknown", False
