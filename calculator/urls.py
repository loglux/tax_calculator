from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PublicTokenObtainPairView,
    PublicTokenRefreshView,
    TaxRateViewSet,
    calculate_tax,
    calculator_view,
)

router = DefaultRouter()
router.register(r"tax-rates", TaxRateViewSet)

urlpatterns = [
    path("", calculator_view, name="calculator"),
    path("api/", include(router.urls)),
    path("api/calculate/", calculate_tax, name="calculate_tax"),
    path("api/token/", PublicTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", PublicTokenRefreshView.as_view(), name="token_refresh"),
]
