# backend/stock_app/admin.py
from django.contrib import admin
from .models import Stock, StockPrice, UserPortfolio, PortfolioStock, WatchList, StockAnalysis, Alert

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'company_name', 'sector', 'current_price', 'date_updated')
    list_filter = ('sector', 'industry')
    search_fields = ('symbol', 'company_name')
    ordering = ('symbol',)

@admin.register(StockPrice)
class StockPriceAdmin(admin.ModelAdmin):
    list_display = ('stock', 'date', 'open_price', 'close_price', 'volume')
    list_filter = ('date', 'stock')
    date_hierarchy = 'date'
    ordering = ('-date',)

class PortfolioStockInline(admin.TabularInline):
    model = PortfolioStock
    extra = 1

@admin.register(UserPortfolio)
class UserPortfolioAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_public', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'user__username')
    inlines = [PortfolioStockInline]

@admin.register(PortfolioStock)
class PortfolioStockAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'stock', 'shares', 'purchase_price', 'purchase_date')
    list_filter = ('purchase_date', 'portfolio')
    search_fields = ('portfolio__name', 'stock__symbol')

@admin.register(WatchList)
class WatchListAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'user__username')
    filter_horizontal = ('stocks',)

@admin.register(StockAnalysis)
class StockAnalysisAdmin(admin.ModelAdmin):
    list_display = ('title', 'stock', 'user', 'is_public', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('title', 'content', 'stock__symbol', 'user__username')

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('stock', 'user', 'alert_type', 'value', 'is_active', 'triggered')
    list_filter = ('alert_type', 'is_active', 'triggered', 'created_at')
    search_fields = ('stock__symbol', 'user__username')
    readonly_fields = ('triggered_at',)