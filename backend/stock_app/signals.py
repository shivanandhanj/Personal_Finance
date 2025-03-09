# backend/stock_app/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockPrice, Stock, Alert
from django.utils import timezone

@receiver(post_save, sender=StockPrice)
def update_stock_current_price(sender, instance, created, **kwargs):
    """
    When a new stock price is saved, update the stock's current_price
    if it's the most recent price.
    """
    # Get the most recent price for this stock
    latest_price = StockPrice.objects.filter(stock=instance.stock).order_by('-date').first()
    
    # If this is the most recent price, update the stock's current_price
    if latest_price and latest_price.id == instance.id:
        instance.stock.current_price = latest_price.close_price
        instance.stock.date_updated = timezone.now()
        instance.stock.save(update_fields=['current_price', 'date_updated'])

@receiver(post_save, sender=StockPrice)
def check_alerts(sender, instance, created, **kwargs):
    """
    When a new stock price is saved, check if any alerts should be triggered.
    """
    # Find active alerts for this stock
    alerts = Alert.objects.filter(
        stock=instance.stock,
        is_active=True,
        triggered=False
    )
    
    # Skip if no alerts
    if not alerts.exists():
        return
    
    current_price = float(instance.close_price)
    
    for alert in alerts:
        alert_value = float(alert.value)
        triggered = False
        
        if alert.alert_type == 'price_above' and current_price > alert_value:
            triggered = True
        elif alert.alert_type == 'price_below' and current_price < alert_value:
            triggered = True
        elif alert.alert_type == 'percent_change':
            # Get previous day's closing price
            previous_day = StockPrice.objects.filter(
                stock=instance.stock,
                date__lt=instance.date
            ).order_by('-date').first()
            
            if previous_day:
                previous_price = float(previous_day.close_price)
                percent_change = ((current_price - previous_price) / previous_price) * 100
                
                if abs(percent_change) > alert_value:
                    triggered = True
        elif alert.alert_type == 'volume_spike':
            # Get average volume for the past 10 days
            past_prices = StockPrice.objects.filter(
                stock=instance.stock,
                date__lt=instance.date
            ).order_by('-date')[:10]
            
            if past_prices.exists():
                avg_volume = sum(float(p.volume) for p in past_prices) / past_prices.count()
                volume_increase = (float(instance.volume) / avg_volume) * 100
                
                if volume_increase > alert_value:
                    triggered = True
        
        if triggered:
            alert.triggered = True
            alert.triggered_at = timezone.now()
            alert.save()