# backend/stock_app/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

from .models import (
    Stock, StockPrice, UserPortfolio, PortfolioStock, 
    WatchList, StockAnalysis, Alert
)
from .serializers import (
    StockSerializer, StockDetailSerializer, StockPriceSerializer,
    UserPortfolioSerializer, PortfolioStockSerializer, WatchListSerializer,
    StockAnalysisSerializer, AlertSerializer
)

class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sector', 'industry']
    search_fields = ['symbol', 'company_name']
    ordering_fields = ['symbol', 'company_name', 'market_cap', 'current_price']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return StockDetailSerializer
        return StockSerializer
    
    @action(detail=True, methods=['get'])
    def historical_data(self, request, pk=None):
        stock = self.get_object()
        period = request.query_params.get('period', '1mo')  # Default to 1 month
        interval = request.query_params.get('interval', '1d')  # Default to daily
        
        # Validate period and interval
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        valid_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']
        
        if period not in valid_periods:
            return Response({"error": f"Invalid period. Must be one of {valid_periods}"}, 
                            status=status.HTTP_400_BAD_REQUEST)
            
        if interval not in valid_intervals:
            return Response({"error": f"Invalid interval. Must be one of {valid_intervals}"}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch data from Yahoo Finance
        try:
            ticker = yf.Ticker(stock.symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return Response({"error": "No data available for this stock and period"}, 
                                status=status.HTTP_404_NOT_FOUND)
                
            # Process and format the data
            hist.reset_index(inplace=True)
            data = []
            
            for _, row in hist.iterrows():
                date_str = row['Date'].strftime('%Y-%m-%d')
                data.append({
                    'date': date_str,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
                
            return Response(data)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def fetch_data(self, request):
        # This endpoint allows adding new stocks and updating prices
        symbol = request.data.get('symbol')
        
        if not symbol:
            return Response({"error": "Symbol is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Get stock info from Yahoo Finance
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'symbol' not in info:
                return Response({"error": f"Stock with symbol {symbol} not found"}, 
                                status=status.HTTP_404_NOT_FOUND)
            
            # Create or update the stock
            stock, created = Stock.objects.update_or_create(
                symbol=symbol,
                defaults={
                    'company_name': info.get('longName', info.get('shortName', symbol)),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'market_cap': info.get('marketCap', 0),
                    'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0))
                }
            )
            
            # Get historical data for the past 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            hist = ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                                  end=end_date.strftime('%Y-%m-%d'))
            
            # Save historical prices
            for date, row in hist.iterrows():
                StockPrice.objects.update_or_create(
                    stock=stock,
                    date=date.date(),
                    defaults={
                        'open_price': round(row['Open'], 2),
                        'high_price': round(row['High'], 2),
                        'low_price': round(row['Low'], 2),
                        'close_price': round(row['Close'], 2),
                        'adjusted_close': round(row['Close'], 2),
                        'volume': int(row['Volume'])
                    }
                )
            
            serializer = StockDetailSerializer(stock)
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockPriceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockPrice.objects.all()
    serializer_class = StockPriceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['stock', 'date']
    ordering_fields = ['date', 'close_price', 'volume']
    
    def get_queryset(self):
        queryset = StockPrice.objects.all()
        stock_symbol = self.request.query_params.get('symbol', None)
        days = self.request.query_params.get('days', None)
        
        if stock_symbol:
            queryset = queryset.filter(stock__symbol=stock_symbol)
            
        if days:
            try:
                days = int(days)
                start_date = datetime.now().date() - timedelta(days=days)
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass
                
        return queryset

class UserPortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = UserPortfolioSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return UserPortfolio.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        portfolio = self.get_object()
        
        # Validate required fields
        required_fields = ['stock', 'shares', 'purchase_price', 'purchase_date']
        for field in required_fields:
            if field not in request.data:
                return Response({"error": f"{field} is required"}, 
                                status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Extract data from request
            stock_id = request.data.get('stock')
            shares = float(request.data.get('shares'))
            purchase_price = float(request.data.get('purchase_price'))
            purchase_date = request.data.get('purchase_date')
            notes = request.data.get('notes', '')
            
            # Validate stock exists
            try:
                stock = Stock.objects.get(pk=stock_id)
            except Stock.DoesNotExist:
                return Response({"error": "Stock not found"}, 
                                status=status.HTTP_404_NOT_FOUND)
            
            # Create or update portfolio stock
            portfolio_stock, created = PortfolioStock.objects.update_or_create(
                portfolio=portfolio,
                stock=stock,
                defaults={
                    'shares': shares,
                    'purchase_price': purchase_price,
                    'purchase_date': purchase_date,
                    'notes': notes
                }
            )
            
            serializer = PortfolioStockSerializer(portfolio_stock)
            return Response(serializer.data, 
                            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
                            
        except Exception as e:
            return Response({"error": str(e)}, 
                            status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_stock(self, request, pk=None):
        portfolio = self.get_object()
        stock_id = request.query_params.get('stock_id')
        
        if not stock_id:
            return Response({"error": "stock_id query parameter is required"}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            portfolio_stock = PortfolioStock.objects.get(portfolio=portfolio, stock_id=stock_id)
            portfolio_stock.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PortfolioStock.DoesNotExist:
            return Response({"error": "Stock not found in this portfolio"}, 
                            status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        portfolio = self.get_object()
        
        # Calculate portfolio performance metrics
        portfolio_stocks = portfolio.stocks.all()
        if not portfolio_stocks:
            return Response({"error": "Portfolio is empty"}, status=status.HTTP_400_BAD_REQUEST)
        
        total_investment = 0
        current_value = 0
        stocks_data = []
        
        for ps in portfolio_stocks:
            investment = float(ps.shares) * float(ps.purchase_price)
            current_stock_value = float(ps.shares) * float(ps.stock.current_price or 0)
            gain_loss = current_stock_value - investment
            gain_loss_percent = (gain_loss / investment) * 100 if investment > 0 else 0
            
            total_investment += investment
            current_value += current_stock_value
            
            stocks_data.append({
                'symbol': ps.stock.symbol,
                'company_name': ps.stock.company_name,
                'shares': float(ps.shares),
                'purchase_price': float(ps.purchase_price),
                'current_price': float(ps.stock.current_price or 0),
                'investment': investment,
                'current_value': current_stock_value,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent
            })
        
        total_gain_loss = current_value - total_investment
        total_gain_loss_percent = (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
        
        return Response({
            'portfolio_name': portfolio.name,
            'total_investment': total_investment,
            'current_value': current_value,
            'total_gain_loss': total_gain_loss,
            'total_gain_loss_percent': total_gain_loss_percent,
            'stocks': stocks_data
        })

# backend/stock_app/views.py (continuation)
class WatchListViewSet(viewsets.ModelViewSet):
    serializer_class = WatchListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return WatchList.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        watchlist = self.get_object()
        stock_id = request.data.get('stock_id')
        
        if not stock_id:
            return Response({"error": "stock_id is required"}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            stock = Stock.objects.get(pk=stock_id)
            watchlist.stocks.add(stock)
            return Response({"message": f"Added {stock.symbol} to watchlist"}, 
                            status=status.HTTP_200_OK)
        except Stock.DoesNotExist:
            return Response({"error": "Stock not found"}, 
                            status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def remove_stock(self, request, pk=None):
        watchlist = self.get_object()
        stock_id = request.data.get('stock_id')
        
        if not stock_id:
            return Response({"error": "stock_id is required"}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            stock = Stock.objects.get(pk=stock_id)
            watchlist.stocks.remove(stock)
            return Response({"message": f"Removed {stock.symbol} from watchlist"}, 
                            status=status.HTTP_200_OK)
        except Stock.DoesNotExist:
            return Response({"error": "Stock not found"}, 
                            status=status.HTTP_404_NOT_FOUND)

class StockAnalysisViewSet(viewsets.ModelViewSet):
    serializer_class = StockAnalysisSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['stock', 'is_public']
    search_fields = ['title', 'content']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticatedOrReadOnly()]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Return public analyses and user's own analyses
            return StockAnalysis.objects.filter(
                (models.Q(is_public=True) | models.Q(user=user))
            )
        else:
            # Anonymous users can only see public analyses
            return StockAnalysis.objects.filter(is_public=True)

class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Alert.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        alert = self.get_object()
        alert.is_active = not alert.is_active
        alert.save()
        return Response({"is_active": alert.is_active}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def triggered(self, request):
        user = request.user
        queryset = Alert.objects.filter(user=user, triggered=True)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def check_alerts(self, request):
        # This would typically be called by a background task/scheduler
        # but we provide an endpoint for testing purposes
        if not request.user.is_staff:
            return Response({"error": "Only staff users can trigger alert checks manually"}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        active_alerts = Alert.objects.filter(is_active=True, triggered=False)
        triggered_count = 0
        
        for alert in active_alerts:
            stock = alert.stock
            current_price = stock.current_price
            
            if not current_price:
                continue
                
            current_price = float(current_price)
            alert_value = float(alert.value)
            
            triggered = False
            
            if alert.alert_type == 'price_above' and current_price > alert_value:
                triggered = True
            elif alert.alert_type == 'price_below' and current_price < alert_value:
                triggered = True
            elif alert.alert_type == 'percent_change':
                # We would need historical prices to check percent change properly
                # This is simplified for demonstration
                yesterday_price = StockPrice.objects.filter(
                    stock=stock, 
                    date__lt=timezone.now().date()
                ).order_by('-date').first()
                
                if yesterday_price:
                    percent_change = ((current_price - float(yesterday_price.close_price)) / 
                                    float(yesterday_price.close_price)) * 100
                                    
                    if abs(percent_change) > alert_value:
                        triggered = True
            elif alert.alert_type == 'volume_spike':
                # Similar to percent change, would need historical data to check properly
                pass
                
            if triggered:
                alert.triggered = True
                alert.triggered_at = timezone.now()
                alert.save()
                triggered_count += 1
                
        return Response({"message": f"Checked {active_alerts.count()} alerts. Triggered {triggered_count}."},
                        status=status.HTTP_200_OK)