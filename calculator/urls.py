from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaxRateViewSet, calculate_tax, calculator_view

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'tax-rates', TaxRateViewSet)

urlpatterns = [
    path('', calculator_view, name='calculator'),
    path('api/', include(router.urls)),
    path('api/calculate/', calculate_tax, name='calculate_tax'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

