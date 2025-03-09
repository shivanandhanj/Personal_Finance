# backend/stock_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'stocks', views.StockViewSet)
router.register(r'stock-prices', views.StockPriceViewSet)
router.register(r'portfolios', views.UserPortfolioViewSet, basename='portfolio')
router.register(r'watchlists', views.WatchListViewSet, basename='watchlist')
router.register(r'analyses', views.StockAnalysisViewSet, basename='analysis')
router.register(r'alerts', views.AlertViewSet, basename='alert')

urlpatterns = [
    path('', include(router.urls)),
]