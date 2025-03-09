# backend/stock_app/serializers.py
from rest_framework import serializers
from .models import Stock, StockPrice, UserPortfolio, PortfolioStock, WatchList, StockAnalysis, Alert
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['date_joined']

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = '__all__'
        read_only_fields = ['date_updated', 'date_added']

class StockPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPrice
        fields = '__all__'

class StockPriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPrice
        fields = ['date', 'open_price', 'high_price', 'low_price', 'close_price', 'adjusted_close', 'volume']

class StockDetailSerializer(serializers.ModelSerializer):
    historical_prices = serializers.SerializerMethodField()
    
    class Meta:
        model = Stock
        fields = '__all__'
        read_only_fields = ['date_updated', 'date_added']
    
    def get_historical_prices(self, obj):
        # Get the last 30 days of prices by default
        prices = obj.prices.all()[:30]
        return StockPriceListSerializer(prices, many=True).data

class PortfolioStockSerializer(serializers.ModelSerializer):
    stock_details = StockSerializer(source='stock', read_only=True)
    current_value = serializers.SerializerMethodField()
    
    class Meta:
        model = PortfolioStock
        fields = ['id', 'stock', 'stock_details', 'shares', 'purchase_price', 
                  'purchase_date', 'notes', 'current_value']
        read_only_fields = ['current_value']
    
    def get_current_value(self, obj):
        # Calculate current value based on latest price
        if obj.stock.current_price:
            return float(obj.stock.current_price) * float(obj.shares)
        return None

class UserPortfolioSerializer(serializers.ModelSerializer):
    stocks = PortfolioStockSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = UserPortfolio
        fields = ['id', 'user', 'name', 'description', 'is_public', 
                  'created_at', 'updated_at', 'stocks', 'total_value']
        read_only_fields = ['created_at', 'updated_at', 'user']
    
    def get_total_value(self, obj):
        # Calculate total portfolio value
        total = 0
        for portfolio_stock in obj.stocks.all():
            if portfolio_stock.stock.current_price:
                total += float(portfolio_stock.stock.current_price) * float(portfolio_stock.shares)
        return total
    
    def create(self, validated_data):
        # Assign the current user to the portfolio
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class WatchListSerializer(serializers.ModelSerializer):
    stocks = StockSerializer(many=True, read_only=True)
    stock_ids = serializers.PrimaryKeyRelatedField(
        source='stocks', 
        queryset=Stock.objects.all(),
        many=True, 
        write_only=True
    )
    
    class Meta:
        model = WatchList
        fields = ['id', 'name', 'stocks', 'stock_ids', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        # Get the stocks data and remove from validated data
        stocks = validated_data.pop('stocks', [])
        # Assign the current user to the watchlist
        validated_data['user'] = self.context['request'].user
        # Create the watchlist
        watchlist = WatchList.objects.create(**validated_data)
        # Add stocks to the watchlist
        watchlist.stocks.set(stocks)
        return watchlist
    
    def update(self, instance, validated_data):
        # Get the stocks data and remove from validated data
        stocks = validated_data.pop('stocks', None)
        # Update the watchlist
        instance = super().update(instance, validated_data)
        # Update stocks if provided
        if stocks is not None:
            instance.stocks.set(stocks)
        return instance

class StockAnalysisSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    stock_details = StockSerializer(source='stock', read_only=True)
    
    class Meta:
        model = StockAnalysis
        fields = ['id', 'stock', 'stock_details', 'user', 'title', 'content', 
                  'is_public', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'user']
    
    def create(self, validated_data):
        # Assign the current user to the analysis
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class AlertSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    stock_details = StockSerializer(source='stock', read_only=True)
    
    class Meta:
        model = Alert
        fields = ['id', 'user', 'stock', 'stock_details', 'alert_type', 'value', 
                  'is_active', 'triggered', 'triggered_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'user', 'triggered', 'triggered_at']
    
    def create(self, validated_data):
        # Assign the current user to the alert
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)