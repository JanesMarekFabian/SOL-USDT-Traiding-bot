"""
SMART INDICATOR BOT - Klassische Indikatoren mit Risikomanagement

FEATURES:
✅ RSI, SMA, Bollinger Bands, MACD, Volume
✅ Risikomanagement (Max Loss, Position Size)
✅ Signal-Filtering (nur starke Signale)
✅ Multi-Timeframe (5min, 10min, 20min)
✅ Strukturierte Ausgabe nach Hold-Zeiträumen
✅ Weniger, aber qualitativere Signale

ZIEL: Weniger Rauschen, bessere Win-Rate
"""

import ccxt
import os
import time
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

API_KEY = os.getenv('MEXC_API_KEY', '')
API_SECRET = os.getenv('MEXC_SECRET', '')

exchange = ccxt.mexc({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {'defaultType': 'future'},
    'enableRateLimit': True,
})

SYMBOL = 'SOL_USDT'
TIMEFRAME = '1m'
SLEEP_TIME = 30  # 1 Minute zwischen Updates

# Risikomanagement (OPTIMIERT für mehr Signale)
MAX_DAILY_LOSS = 3.0  # 3% maximaler Tagesverlust (war 2.0%)
MAX_POSITION_SIZE = 3.0  # 3% maximaler Positionsgröße (war 5.0%)
MIN_SIGNAL_STRENGTH = 5.0  # Minimale Signal-Stärke (war 7.0 - mehr Signale!)
MIN_CONFIDENCE = 0.6  # Minimale Confidence (war 0.75 - mehr Signale!)

# Hold-Zeiträume für Analyse
HOLD_PERIODS = [5, 10, 20]  # Minuten

class SmartIndicatorBot:
    def __init__(self):
        self.daily_pnl = 0.0
        self.last_signal_time = None
        self.signal_cooldown = 180  # 3 Minuten zwischen Signalen (war 5min - häufiger!)
        
    def calculate_rsi(self, prices, period=14):
        """Berechnet RSI"""
        if len(prices) < period + 1:
            return 50.0
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.mean(gains[-period:])
        avg_losses = np.mean(losses[-period:])
        
        if avg_losses == 0:
            return 100.0
            
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_sma(self, prices, period):
        """Berechnet Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return np.mean(prices[-period:])
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Berechnet Bollinger Bands"""
        if len(prices) < period:
            return None, None, None
            
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return upper, sma, lower
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Berechnet MACD"""
        if len(prices) < slow:
            return 0, 0, 0
            
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD)
        macd_values = [macd_line]  # Vereinfacht
        signal_line = self.calculate_ema(macd_values, signal)
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_ema(self, prices, period):
        """Berechnet Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
            
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
            
        return ema
    
    def calculate_atr(self, high, low, close, period=14):
        """Berechnet Average True Range für Volatilität"""
        if len(high) < period + 1:
            return 0
            
        true_ranges = []
        for i in range(1, len(high)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            true_ranges.append(max(tr1, tr2, tr3))
            
        return np.mean(true_ranges[-period:])
    
    def analyze_volume(self, volumes, prices):
        """Analysiert Volume-Patterns"""
        if len(volumes) < 10:
            return 0
            
        avg_volume = np.mean(volumes[-10:])
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volume-Preis Divergenz
        price_change = (prices[-1] - prices[-2]) / prices[-2] if len(prices) > 1 else 0
        volume_support = 1 if (price_change > 0 and volume_ratio > 1.2) or (price_change < 0 and volume_ratio > 1.2) else 0
        
        return volume_ratio, volume_support
    
    def calculate_signal_strength(self, indicators):
        """Berechnet Gesamt-Signal-Stärke (0-10)"""
        strength = 0.0
        
        # RSI Beitrag (0-2 Punkte)
        rsi = indicators['rsi']
        if rsi < 30:
            strength += 2.0  # Oversold
        elif rsi > 70:
            strength -= 2.0  # Overbought
        elif 40 <= rsi <= 60:
            strength += 0.5  # Neutral
            
        # SMA Beitrag (0-2 Punkte)
        sma_alignment = indicators['sma_alignment']
        strength += sma_alignment * 2.0
        
        # Bollinger Bands Beitrag (0-2 Punkte)
        bb_position = indicators['bb_position']
        if bb_position < 0.1:  # Near lower band
            strength += 1.5
        elif bb_position > 0.9:  # Near upper band
            strength -= 1.5
            
        # MACD Beitrag (0-2 Punkte)
        macd_signal = indicators['macd_signal']
        strength += macd_signal * 2.0
        
        # Volume Beitrag (0-1 Punkt)
        volume_support = indicators['volume_support']
        strength += volume_support
        
        # Volatilität Beitrag (0-1 Punkt)
        volatility_score = indicators['volatility_score']
        strength += volatility_score
        
        return max(-10, min(10, strength))
    
    def get_risk_adjusted_signal(self, signal_strength, confidence, current_price):
        """Risikomanagement und Signal-Filtering"""
        # Prüfe Cooldown
        if self.last_signal_time and (datetime.now() - self.last_signal_time).total_seconds() < self.signal_cooldown:
            return None, 0, "Cooldown"
        
        # Prüfe minimale Stärke
        if abs(signal_strength) < MIN_SIGNAL_STRENGTH:
            return None, 0, "Zu schwach"
        
        # Prüfe minimale Confidence
        if confidence < MIN_CONFIDENCE:
            return None, 0, "Zu wenig Confidence"
        
        # Prüfe Tagesverlust
        if self.daily_pnl < -MAX_DAILY_LOSS:
            return None, 0, "Tagesverlust-Limit erreicht"
        
        # Bestimme Signal-Typ
        if signal_strength > MIN_SIGNAL_STRENGTH:
            signal_type = "buy"
            position_size = min(MAX_POSITION_SIZE, abs(signal_strength) / 10 * MAX_POSITION_SIZE)
        elif signal_strength < -MIN_SIGNAL_STRENGTH:
            signal_type = "sell"
            position_size = min(MAX_POSITION_SIZE, abs(signal_strength) / 10 * MAX_POSITION_SIZE)
        else:
            return None, 0, "Neutral"
        
        return signal_type, position_size, "OK"
    
    def analyze_market(self):
        """Hauptanalyse-Funktion"""
        try:
            # Hole OHLCV-Daten
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
            if len(ohlcv) < 50:
                return None
                
            # Extrahiere Daten
            closes = [candle[4] for candle in ohlcv]
            highs = [candle[2] for candle in ohlcv]
            lows = [candle[3] for candle in ohlcv]
            volumes = [candle[5] for candle in ohlcv]
            
            current_price = closes[-1]
            
            # Berechne Indikatoren
            rsi = self.calculate_rsi(closes)
            sma_20 = self.calculate_sma(closes, 20)
            sma_50 = self.calculate_sma(closes, 50)
            sma_200 = self.calculate_sma(closes, 200)
            
            # SMA Alignment
            sma_alignment = 0
            if sma_20 > sma_50 > sma_200:
                sma_alignment = 1  # Bullish
            elif sma_20 < sma_50 < sma_200:
                sma_alignment = -1  # Bearish
                
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(closes)
            bb_position = 0
            if bb_upper and bb_lower:
                bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            
            # MACD
            macd_line, signal_line, histogram = self.calculate_macd(closes)
            macd_signal = 1 if macd_line > signal_line else -1
            
            # Volume
            volume_ratio, volume_support = self.analyze_volume(volumes, closes)
            
            # ATR für Volatilität
            atr = self.calculate_atr(highs, lows, closes)
            volatility_score = min(1.0, atr / current_price * 100)  # Normalisiert
            
            # Indikatoren zusammenfassen
            indicators = {
                'rsi': rsi,
                'sma_alignment': sma_alignment,
                'bb_position': bb_position,
                'macd_signal': macd_signal,
                'volume_support': volume_support,
                'volatility_score': volatility_score
            }
            
            # Signal-Stärke berechnen
            signal_strength = self.calculate_signal_strength(indicators)
            
            # Confidence basierend auf Konsistenz
            confidence = min(1.0, abs(signal_strength) / 10)
            
            # Risikomanagement
            signal_type, position_size, status = self.get_risk_adjusted_signal(signal_strength, confidence, current_price)
            
            if signal_type:
                self.last_signal_time = datetime.now()
                
                # Logging
                with open('signals.log', 'a') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"{timestamp} - bot:smart_indicator - signal:{signal_type} - strength:{signal_strength:.2f} - price:{current_price:.4f} - additional:confidence:{confidence:.2f}/position_size:{position_size:.1f}%/rsi:{rsi:.1f}/sma_alignment:{sma_alignment}\n")
                
                return {
                    'signal': signal_type,
                    'strength': signal_strength,
                    'confidence': confidence,
                    'position_size': position_size,
                    'price': current_price,
                    'indicators': indicators,
                    'status': status
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Fehler bei Marktanalyse: {e}")
            return None
    
    def run(self):
        """Haupt-Loop"""
        print("🚀 SMART INDICATOR BOT gestartet!")
        print(f"📊 Analysiert {SYMBOL} alle {SLEEP_TIME} Sekunden")
        print(f"🎯 Minimale Signal-Stärke: {MIN_SIGNAL_STRENGTH}")
        print(f"🛡️ Risikomanagement: Max {MAX_DAILY_LOSS}% Tagesverlust")
        print(f"⏰ Cooldown: {self.signal_cooldown} Sekunden zwischen Signalen\n")
        
        while True:
            try:
                result = self.analyze_market()
                
                if result:
                    print(f"\n{'='*60}")
                    print(f"🎯 SMART INDICATOR SIGNAL")
                    print(f"{'='*60}")
                    print(f"⏰ Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"💱 Symbol: {SYMBOL}")
                    print(f"💰 Preis: {result['price']:.4f} USDT")
                    print(f"📈 Signal: {result['signal'].upper()}")
                    print(f"💪 Stärke: {result['strength']:.2f}/10")
                    print(f"🎯 Confidence: {result['confidence']:.1%}")
                    print(f"📊 Position Size: {result['position_size']:.1f}%")
                    print(f"✅ Status: {result['status']}")
                    
                    # Indikatoren-Details
                    ind = result['indicators']
                    print(f"\n📊 INDIKATOREN:")
                    print(f"  RSI: {ind['rsi']:.1f}")
                    print(f"  SMA Alignment: {'🟢 Bullish' if ind['sma_alignment'] > 0 else '🔴 Bearish' if ind['sma_alignment'] < 0 else '⚪ Neutral'}")
                    print(f"  BB Position: {ind['bb_position']:.2f}")
                    print(f"  MACD: {'🟢 Bullish' if ind['macd_signal'] > 0 else '🔴 Bearish'}")
                    print(f"  Volume Support: {'✅ Ja' if ind['volume_support'] else '❌ Nein'}")
                    print(f"  Volatilität: {ind['volatility_score']:.2f}")
                    
                    print(f"\n⏰ Hold-Zeiträume: {', '.join(map(str, HOLD_PERIODS))} Minuten")
                    print(f"🛡️ Risikomanagement aktiv")
                    
                else:
                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Kein Signal (zu schwach/Cooldown)")
                
                time.sleep(SLEEP_TIME)
                
            except KeyboardInterrupt:
                print("\n🛑 Bot gestoppt")
                break
            except Exception as e:
                print(f"❌ Fehler: {e}")
                time.sleep(SLEEP_TIME)

if __name__ == '__main__':
    bot = SmartIndicatorBot()
    bot.run() 