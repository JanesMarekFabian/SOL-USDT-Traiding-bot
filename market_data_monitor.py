"""
MARKET DATA MONITOR BOT - Live Marktdaten Überwachung

FEATURES:
✅ Live Kurs-Updates alle 10 Sekunden
✅ 10-Minuten Durchschnittspreis Vergleich
✅ Support/Resistance Level Erkennung
✅ RSI & SMA Indikatoren (mehrere Versionen)
✅ Markt-Tendenz Analyse (Bullish/Bearish)
✅ 24h & Wochen-Trend Analyse (OPTIMIERT)
✅ Unabhängiger Bot (keine Trading Signale)

STRATEGIE:
- Kontinuierliche Marktüberwachung
- Technische Analyse ohne Trading
- Übersichtliche Daten-Darstellung
"""

import ccxt
import os
import time
import numpy as np
from datetime import datetime, timedelta
from collections import deque

API_KEY = os.getenv('MEXC_API_KEY', '')
API_SECRET = os.getenv('MEXC_SECRET', '')

exchange = ccxt.mexc({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {'defaultType': 'future'},
    'enableRateLimit': True,
})

SYMBOL = 'SOL/USDT'
TIMEFRAME = '1m'
SLEEP_TIME = 3 # 10 Sekunden zwischen Updates

# Parameter
LOOKBACK_PERIOD = 50  # Für S/R Erkennung
AVERAGE_PERIOD = 10  # 10 Minuten für Durchschnitt
RSI_PERIODS = [14, 21, 50]  # Verschiedene RSI Perioden
SMA_PERIODS = [20, 50, 200]  # Verschiedene SMA Perioden

class MarketDataMonitor:
    
    def __init__(self):
        self.price_history = deque(maxlen=600)  # 10 Stunden History
        self.average_price_10min = None
        self.last_average_update = None
        self.support_levels = []
        self.resistance_levels = []
        
    def calculate_average_price_10min(self, ohlcv):
        """Berechnet 10-Minuten Durchschnittspreis"""
        if len(ohlcv) < AVERAGE_PERIOD:
            return None
            
        # Hole letzten 10 Minuten (10 Kerzen)
        recent_candles = ohlcv[-AVERAGE_PERIOD:]
        closes = [candle[4] for candle in recent_candles]
        
        return np.mean(closes)
    
    def calculate_rsi(self, prices, period=14):
        """Berechnet RSI"""
        if len(prices) < period + 1:
            return 50  # Neutral wenn nicht genug Daten
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.mean(gains[-period:])
        avg_losses = np.mean(losses[-period:])
        
        if avg_losses == 0:
            return 100
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_sma(self, prices, period):
        """Berechnet Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
            
        return np.mean(prices[-period:])
    
    def find_pivot_points(self, ohlcv, window=3):
        """Findet Pivot Highs und Lows für S/R"""
        if len(ohlcv) < window * 2 + 1:
            return [], []
            
        highs = [candle[2] for candle in ohlcv]
        lows = [candle[3] for candle in ohlcv]
        
        pivot_highs = []
        pivot_lows = []
        
        for i in range(window, len(highs) - window):
            # Pivot High
            is_pivot_high = True
            for j in range(i - window, i + window + 1):
                if j != i and highs[j] >= highs[i]:
                    is_pivot_high = False
                    break
            
            if is_pivot_high:
                pivot_highs.append({
                    'price': highs[i],
                    'index': i,
                    'timestamp': ohlcv[i][0]
                })
            
            # Pivot Low
            is_pivot_low = True
            for j in range(i - window, i + window + 1):
                if j != i and lows[j] <= lows[i]:
                    is_pivot_low = False
                    break
            
            if is_pivot_low:
                pivot_lows.append({
                    'price': lows[i],
                    'index': i,
                    'timestamp': ohlcv[i][0]
                })
        
        return pivot_highs, pivot_lows
    
    def cluster_levels(self, pivot_points, tolerance=0.5):
        """Clustert ähnliche Pivot Points zu S/R Levels"""
        if not pivot_points:
            return []
        
        clusters = []
        used_points = set()
        
        for i, point in enumerate(pivot_points):
            if i in used_points:
                continue
                
            cluster = [point]
            used_points.add(i)
            
            for j, other_point in enumerate(pivot_points):
                if j in used_points or j <= i:
                    continue
                
                price_diff = abs(point['price'] - other_point['price']) / point['price'] * 100
                
                if price_diff <= tolerance:
                    cluster.append(other_point)
                    used_points.add(j)
            
            if len(cluster) >= 1:
                avg_price = sum(p['price'] for p in cluster) / len(cluster)
                clusters.append({
                    'price': avg_price,
                    'touch_count': len(cluster),
                    'strength': len(cluster)
                })
        
        return clusters
    
    def calculate_support_resistance(self, ohlcv):
        """Berechnet aktuelle Support/Resistance Levels"""
        if len(ohlcv) < LOOKBACK_PERIOD:
            return [], []
        
        pivot_highs, pivot_lows = self.find_pivot_points(ohlcv)
        
        resistance_clusters = self.cluster_levels(pivot_highs, tolerance=0.5)
        support_clusters = self.cluster_levels(pivot_lows, tolerance=0.5)
        
        # Validiere S/R Levels (mindestens 2 Berührungen)
        valid_resistance = [
            level for level in resistance_clusters 
            if level['touch_count'] >= 2
        ]
        
        valid_support = [
            level for level in support_clusters 
            if level['touch_count'] >= 2
        ]
        
        valid_resistance.sort(key=lambda x: x['touch_count'], reverse=True)
        valid_support.sort(key=lambda x: x['touch_count'], reverse=True)
        
        return valid_resistance[:3], valid_support[:3]  # Top 3
    
    def analyze_market_tendency(self, current_price, rsi_values, sma_values):
        """Analysiert Markt-Tendenz (Bullish/Bearish)"""
        bullish_signals = 0
        bearish_signals = 0
        
        # RSI Analyse
        for rsi in rsi_values:
            if rsi > 70:
                bearish_signals += 1  # Overbought
            elif rsi < 30:
                bullish_signals += 1  # Oversold
            elif rsi > 50:
                bullish_signals += 0.5
            else:
                bearish_signals += 0.5
        
        # SMA Analyse
        if len(sma_values) >= 2:
            sma_short = sma_values[0]  # 20 SMA
            sma_long = sma_values[1]   # 50 SMA
            
            if current_price > sma_short > sma_long:
                bullish_signals += 2  # Starke Bullish
            elif current_price < sma_short < sma_long:
                bearish_signals += 2  # Starke Bearish
            elif current_price > sma_short:
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        # Tendenz bestimmen
        if bullish_signals > bearish_signals + 1:
            return 'BULLISH', bullish_signals - bearish_signals
        elif bearish_signals > bullish_signals + 1:
            return 'BEARISH', bearish_signals - bearish_signals
        else:
            return 'NEUTRAL', 0
    
    def analyze_24h_trend(self):
        """Analysiert 24h Trend mit 1h Daten"""
        try:
            ohlcv_1h = exchange.fetch_ohlcv(SYMBOL, '1h', limit=25)
            if len(ohlcv_1h) < 24:
                return 'UNKNOWN', 0
                
            # Hole 24h Daten
            day_ago = ohlcv_1h[-24]
            current = ohlcv_1h[-1]
            
            open_24h = day_ago[1]  # Open vor 24h
            close_current = current[4]  # Aktueller Close
            
            change_24h = ((close_current - open_24h) / open_24h) * 100
            
            if change_24h > 2:
                return 'STRONG_BULLISH', change_24h
            elif change_24h > 0.5:
                return 'BULLISH', change_24h
            elif change_24h < -2:
                return 'STRONG_BEARISH', change_24h
            elif change_24h < -0.5:
                return 'BEARISH', change_24h
            else:
                return 'SIDEWAYS', change_24h
                
        except Exception as e:
            return 'UNKNOWN', 0
    
    def analyze_weekly_trend(self):
        """Analysiert Wochen-Trend mit 1d Daten"""
        try:
            ohlcv_1d = exchange.fetch_ohlcv(SYMBOL, '1d', limit=10)
            if len(ohlcv_1d) < 7:
                return 'UNKNOWN', 0
                
            # Hole Wochen-Daten
            week_ago = ohlcv_1d[-7]
            current = ohlcv_1d[-1]
            
            open_week = week_ago[1]  # Open vor 1 Woche
            close_current = current[4]  # Aktueller Close
            
            change_week = ((close_current - open_week) / open_week) * 100
            
            if change_week > 5:
                return 'STRONG_BULLISH', change_week
            elif change_week > 1:
                return 'BULLISH', change_week
            elif change_week < -5:
                return 'STRONG_BEARISH', change_week
            elif change_week < -1:
                return 'BEARISH', change_week
            else:
                return 'SIDEWAYS', change_week
                
        except Exception as e:
            return 'UNKNOWN', 0
    
    def get_market_data(self):
        """Hauptfunktion für Marktdaten-Sammlung"""
        try:
            # Hole OHLCV Daten
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=200)
            if len(ohlcv) < 50:
                return None
            
            current_candle = ohlcv[-1]
            current_price = current_candle[4]  # Close
            
            # 10-Minuten Durchschnitt
            avg_price_10min = self.calculate_average_price_10min(ohlcv)
            
            # Update 10-Min Durchschnitt (alle 10 Minuten)
            current_time = datetime.now()
            if (self.last_average_update is None or 
                (current_time - self.last_average_update).total_seconds() > 600):
                self.average_price_10min = avg_price_10min
                self.last_average_update = current_time
            
            # Preis-Vergleich
            price_change_vs_avg = 0
            if self.average_price_10min:
                price_change_vs_avg = ((current_price - self.average_price_10min) / self.average_price_10min) * 100
            
            # RSI Berechnung
            closes = [candle[4] for candle in ohlcv]
            rsi_values = [self.calculate_rsi(closes, period) for period in RSI_PERIODS]
            
            # SMA Berechnung
            sma_values = [self.calculate_sma(closes, period) for period in SMA_PERIODS]
            
            # Support/Resistance
            resistance_levels, support_levels = self.calculate_support_resistance(ohlcv)
            
            # Markt-Tendenz
            market_tendency, tendency_strength = self.analyze_market_tendency(
                current_price, rsi_values, sma_values
            )
            
            # 24h & Wochen-Trend (OPTIMIERT)
            trend_24h, change_24h = self.analyze_24h_trend()
            trend_week, change_week = self.analyze_weekly_trend()
            
            return {
                'timestamp': current_time,
                'current_price': current_price,
                'avg_price_10min': self.average_price_10min,
                'price_change_vs_avg': price_change_vs_avg,
                'rsi_values': rsi_values,
                'sma_values': sma_values,
                'resistance_levels': resistance_levels,
                'support_levels': support_levels,
                'market_tendency': market_tendency,
                'tendency_strength': tendency_strength,
                'trend_24h': trend_24h,
                'change_24h': change_24h,
                'trend_week': trend_week,
                'change_week': change_week
            }
            
        except Exception as e:
            print(f'❌ Marktdaten Fehler: {e}')
            return None
    
    def print_market_data(self, data):
        """Druckt formatierte Marktdaten"""
        if not data:
            return
            
        print(f'\n{'='*80}')
        print(f'📊 MARKET DATA MONITOR - {data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'{'='*80}')
        
        # Preis-Informationen
        print(f'💰 AKTUELLER PREIS: {data["current_price"]:.4f} USDT')
        if data['avg_price_10min']:
            print(f'📊 10-MIN DURCHSCHNITT: {data["avg_price_10min"]:.4f} USDT')
            print(f'📈 VERÄNDERUNG: {data["price_change_vs_avg"]:+.2f}%')
        
        # RSI Indikatoren
        print(f'\n📊 RSI INDIKATOREN:')
        for i, (period, rsi) in enumerate(zip(RSI_PERIODS, data['rsi_values'])):
            status = '🔴 Overbought' if rsi > 70 else '🟢 Oversold' if rsi < 30 else '🟡 Neutral'
            print(f'  RSI({period}): {rsi:.1f} {status}')
        
        # SMA Indikatoren
        print(f'\n📈 SMA INDIKATOREN:')
        for i, (period, sma) in enumerate(zip(SMA_PERIODS, data['sma_values'])):
            diff = ((data['current_price'] - sma) / sma) * 100
            status = '🟢 Über SMA' if diff > 0 else '🔴 Unter SMA'
            print(f'  SMA({period}): {sma:.4f} USDT ({diff:+.2f}%) {status}')
        
        # Support/Resistance
        if data['resistance_levels']:
            print(f'\n🔴 RESISTANCE LEVELS:')
            for i, level in enumerate(data['resistance_levels'], 1):
                distance = (level['price'] - data['current_price']) / data['current_price'] * 100
                print(f'  {i}. {level["price"]:.4f} USDT (+{distance:.2f}%) | {level["touch_count"]} Berührungen')
        
        if data['support_levels']:
            print(f'\n🟢 SUPPORT LEVELS:')
            for i, level in enumerate(data['support_levels'], 1):
                distance = (data['current_price'] - level['price']) / data['current_price'] * 100
                print(f'  {i}. {level["price"]:.4f} USDT (-{distance:.2f}%) | {level["touch_count"]} Berührungen')
        
        # Markt-Tendenz
        tendency_emoji = '🟢' if data['market_tendency'] == 'BULLISH' else '🔴' if data['market_tendency'] == 'BEARISH' else '🟡'
        print(f'\n🎯 MARKT-TENDENZ: {tendency_emoji} {data["market_tendency"]} (Stärke: {data["tendency_strength"]:.1f})')
        
        # 24h & Wochen-Trend
        trend_24h_emoji = '🟢' if 'BULL' in data['trend_24h'] else '🔴' if 'BEAR' in data['trend_24h'] else '🟡'
        trend_week_emoji = '🟢' if 'BULL' in data['trend_week'] else '🔴' if 'BEAR' in data['trend_week'] else '🟡'
        
        print(f'\n⏰ 24H TREND: {trend_24h_emoji} {data["trend_24h"]} ({data["change_24h"]:+.2f}%)')
        print(f'📅 WOCHEN-TREND: {trend_week_emoji} {data["trend_week"]} ({data["change_week"]:+.2f}%)')
        
        print(f'\n{'='*80}')
    
    def run(self):
        """Haupt-Loop"""
        print('📊 MARKET DATA MONITOR gestartet!')
        print(f'🎯 Symbol: {SYMBOL}')
        print(f'⏰ Update: alle {SLEEP_TIME} Sekunden')
        print(f'📊 10-Min Durchschnitt wird alle 10 Minuten aktualisiert')
        print(f'📈 RSI Perioden: {RSI_PERIODS}')
        print(f'📊 SMA Perioden: {SMA_PERIODS}')
        print(f'🎯 Unabhängiger Monitor (keine Trading Signale)\n')
        
        while True:
            try:
                data = self.get_market_data()
                
                if data:
                    self.print_market_data(data)
                else:
                    print(f'⏰ {datetime.now().strftime("%H:%M:%S")} - Keine Marktdaten verfügbar')
                
                time.sleep(SLEEP_TIME)
                
            except KeyboardInterrupt:
                print('\n🛑 Market Data Monitor gestoppt')
                break
            except Exception as e:
                print(f'❌ Fehler: {e}')
                time.sleep(SLEEP_TIME)

if __name__ == '__main__':
    monitor = MarketDataMonitor()
    monitor.run()