# backend/stock_app/models.py
from django.db import models
from django.contrib.auth.models import User

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    company_name = models.CharField(max_length=255)
    sector = models.CharField(max_length=100, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    market_cap = models.BigIntegerField(blank=True, null=True)
    current_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    date_updated = models.DateTimeField(auto_now=True)
    date_added = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.symbol} - {self.company_name}"
    
    class Meta:
        ordering = ['symbol']

class StockPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='prices')
    date = models.DateField()
    open_price = models.DecimalField(max_digits=12, decimal_places=2)
    high_price = models.DecimalField(max_digits=12, decimal_places=2)
    low_price = models.DecimalField(max_digits=12, decimal_places=2)
    close_price = models.DecimalField(max_digits=12, decimal_places=2)
    adjusted_close = models.DecimalField(max_digits=12, decimal_places=2)
    volume = models.BigIntegerField()
    
    def __str__(self):
        return f"{self.stock.symbol} - {self.date}"
    
    class Meta:
        ordering = ['-date']
        unique_together = ['stock', 'date']

class UserPortfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolios')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'name']

class PortfolioStock(models.Model):
    portfolio = models.ForeignKey(UserPortfolio, on_delete=models.CASCADE, related_name='stocks')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    shares = models.DecimalField(max_digits=12, decimal_places=4)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.portfolio.name} - {self.stock.symbol} ({self.shares} shares)"
    
    class Meta:
        ordering = ['portfolio', 'stock__symbol']

class WatchList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists')
    name = models.CharField(max_length=100)
    stocks = models.ManyToManyField(Stock, related_name='watchlists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    class Meta:
        ordering = ['user', 'name']
        unique_together = ['user', 'name']

class StockAnalysis(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='analyses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analyses', null=True, blank=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.stock.symbol} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Stock Analyses"

class Alert(models.Model):
    ALERT_TYPES = (
        ('price_above', 'Price Above'),
        ('price_below', 'Price Below'),
        ('percent_change', 'Percent Change'),
        ('volume_spike', 'Volume Spike'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.stock.symbol} - {self.get_alert_type_display()} - {self.value}"
    
    class Meta:
        ordering = ['-created_at']