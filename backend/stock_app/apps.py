# backend/stock_app/apps.py
from django.apps import AppConfig

class StockAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stock_app'
    verbose_name = 'Stock Market Analysis'
    
    def ready(self):
        # Import signal handlers
        import stock_app.signals