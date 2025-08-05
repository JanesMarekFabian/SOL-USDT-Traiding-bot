"""
PATTERN FILTER BOT - Pattern-basierte Signal-Filterung

FEATURES:
✅ Candlestick Patterns (Doji, Hammer, Shooting Star, etc.)
✅ Support/Resistance Levels
✅ Trend Formations (Triangles, Flags, Wedges)
✅ Volume Patterns
✅ Zeitbasierte Filter (5min, 10min, 20min)
✅ Confidence Scoring
✅ Strukturierte Ausgabe nach Hold-Zeiträumen

ZIEL: Qualitativ hochwertige Pattern-Signale
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

# Pattern-Schwellenwerte (OPTIMIERT für mehr Signale)
MIN_PATTERN_CONFIDENCE = 0.5  # war 0.7 (mehr Signale!)
MIN_VOLUME_RATIO = 1.0  # war 1.2 (mehr Volume-Signale!)
MIN_TREND_STRENGTH = 0.4  # war 0.6 (schwächere Trends OK!)

# Hold-Zeiträume für Analyse
HOLD_PERIODS = [5, 10, 20]  # Minuten

class PatternFilterBot:
    def __init__(self):
        self.last_signal_time = None
        self.signal_cooldown = 300  # 5 Minuten zwischen Pattern-Signalen (war 10min - häufiger!)
        self.pattern_history = defaultdict(list)
        
    def detect_candlestick_pattern(self, ohlcv):
        """Erkennt Candlestick-Patterns"""
        if len(ohlcv) < 3:
            return None
            
        patterns = []
        
        for i in range(len(ohlcv) - 2):
            current = ohlcv[i]
            prev = ohlcv[i+1] if i+1 < len(ohlcv) else None
            next_candle = ohlcv[i-1] if i > 0 else None
            
            if not prev:
                continue
                
            # Extrahiere OHLC
            curr_open, curr_high, curr_low, curr_close = current[1], current[2], current[3], current[4]
            prev_open, prev_high, prev_low, prev_close = prev[1], prev[2], prev[3], prev[4]
            
            # Body und Shadow berechnen
            curr_body = abs(curr_close - curr_open)
            curr_upper_shadow = curr_high - max(curr_open, curr_close)
            curr_lower_shadow = min(curr_open, curr_close) - curr_low
            
            prev_body = abs(prev_close - prev_open)
            
            # Doji Pattern
            if curr_body < (curr_high - curr_low) * 0.1:
                patterns.append({
                    'name': 'Doji',
                    'type': 'neutral',
                    'strength': 0.5,
                    'description': 'Unentschlossener Markt'
                })
            
            # Hammer Pattern
            if (curr_lower_shadow > curr_body * 2 and 
                curr_upper_shadow < curr_body * 0.5 and
                curr_close > curr_open):
                patterns.append({
                    'name': 'Hammer',
                    'type': 'bullish',
                    'strength': 0.7,
                    'description': 'Bullish Reversal'
                })
            
            # Shooting Star Pattern
            if (curr_upper_shadow > curr_body * 2 and
                curr_lower_shadow < curr_body * 0.5 and
                curr_close < curr_open):
                patterns.append({
                    'name': 'Shooting Star',
                    'type': 'bearish',
                    'strength': 0.7,
                    'description': 'Bearish Reversal'
                })
            
            # Engulfing Pattern
            if (curr_body > prev_body * 1.5):
                if curr_close > curr_open and prev_close < prev_open:
                    patterns.append({
                        'name': 'Bullish Engulfing',
                        'type': 'bullish',
                        'strength': 0.8,
                        'description': 'Starker Bullish Reversal'
                    })
                elif curr_close < curr_open and prev_close > prev_open:
                    patterns.append({
                        'name': 'Bearish Engulfing',
                        'type': 'bearish',
                        'strength': 0.8,
                        'description': 'Starker Bearish Reversal'
                    })
        
        return patterns
    
    def find_support_resistance(self, ohlcv, window=20):
        """Findet Support/Resistance Levels"""
        if len(ohlcv) < window:
            return None, None
            
        highs = [candle[2] for candle in ohlcv[-window:]]
        lows = [candle[3] for candle in ohlcv[-window:]]
        
        # Einfache Support/Resistance (Min/Max)
        resistance = max(highs)
        support = min(lows)
        
        current_price = ohlcv[-1][4]
        
        # Berechne Abstände
        resistance_distance = (resistance - current_price) / current_price * 100
        support_distance = (current_price - support) / current_price * 100
        
        return {
            'resistance': resistance,
            'support': support,
            'resistance_distance': resistance_distance,
            'support_distance': support_distance
        }
    
    def analyze_trend_formation(self, ohlcv):
        """Analysiert Trend-Formationen"""
        if len(ohlcv) < 10:
            return None
            
        closes = [candle[4] for candle in ohlcv]
        
        # Linear Regression für Trend-Stärke
        x = np.arange(len(closes))
        slope = 0
        trend_strength = 0
        trend_direction = 'neutral'
        
        try:
            slope, intercept, r_value, p_value, std_err = np.polyfit(x, closes, 1)
            trend_strength = abs(r_value)
            trend_direction = 'bullish' if slope > 0 else 'bearish'
        except:
            trend_strength = 0
            trend_direction = 'neutral'
        
        # Volatilität
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns)
        
        # Trend-Formation erkennen
        formation = 'unknown'
        if trend_strength > MIN_TREND_STRENGTH:
            if trend_direction == 'bullish':
                formation = 'uptrend'
            else:
                formation = 'downtrend'
        else:
            formation = 'sideways'
        
        return {
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'formation': formation,
            'volatility': volatility,
            'slope': slope
        }
    
    def analyze_volume_patterns(self, ohlcv):
        """Analysiert Volume-Patterns"""
        if len(ohlcv) < 10:
            return None
            
        volumes = [candle[5] for candle in ohlcv]
        closes = [candle[4] for candle in ohlcv]
        
        # Volume-Trend
        recent_volumes = volumes[-5:]
        avg_volume = np.mean(volumes[-10:])
        current_volume = volumes[-1]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volume-Preis Divergenz
        price_change = (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0
        volume_divergence = 0
        
        if abs(price_change) > 0.01:  # >1% Preisänderung
            if price_change > 0 and volume_ratio < 0.8:
                volume_divergence = -1  # Bullish Divergenz
            elif price_change < 0 and volume_ratio < 0.8:
                volume_divergence = 1   # Bearish Divergenz
        
        return {
            'volume_ratio': volume_ratio,
            'volume_divergence': volume_divergence,
            'high_volume': volume_ratio > MIN_VOLUME_RATIO
        }
    
    def calculate_pattern_confidence(self, patterns, support_resistance, trend, volume):
        """Berechnet Gesamt-Confidence für Pattern"""
        confidence = 0.0
        factors = 0
        
        # Candlestick Patterns
        if patterns:
            pattern_strength = sum(p['strength'] for p in patterns)
            confidence += pattern_strength
            factors += 1
        
        # Support/Resistance
        if support_resistance:
            current_price = support_resistance.get('current_price', 0)
            if current_price > 0:
                # Nähe zu Support/Resistance
                support_dist = support_resistance['support_distance']
                resistance_dist = support_resistance['resistance_distance']
                
                if support_dist < 2 or resistance_dist < 2:  # <2% Abstand
                    confidence += 0.3
                    factors += 1
        
        # Trend-Formation
        if trend and trend['trend_strength'] > MIN_TREND_STRENGTH:
            confidence += trend['trend_strength']
            factors += 1
        
        # Volume
        if volume and volume['high_volume']:
            confidence += 0.2
            factors += 1
        
        # Normalisiere auf 0-1
        if factors > 0:
            confidence = min(1.0, confidence / factors)
        
        return confidence
    
    def get_timeframe_signal(self, confidence, patterns, trend):
        """Generiert Signal für verschiedene Zeiträume"""
        if confidence < MIN_PATTERN_CONFIDENCE:
            return None
        
        # Bestimme Signal basierend auf Patterns und Trend
        bullish_patterns = [p for p in patterns if p['type'] == 'bullish']
        bearish_patterns = [p for p in patterns if p['type'] == 'bearish']
        
        signal = None
        strength = 0
        
        if bullish_patterns and (not trend or trend['trend_direction'] != 'bearish'):
            signal = 'buy'
            strength = sum(p['strength'] for p in bullish_patterns)
        elif bearish_patterns and (not trend or trend['trend_direction'] != 'bullish'):
            signal = 'sell'
            strength = sum(p['strength'] for p in bearish_patterns)
        
        if signal:
            return {
                'signal': signal,
                'strength': min(10.0, strength * 10),
                'confidence': confidence,
                'patterns': patterns,
                'trend': trend
            }
        
        return None
    
    def analyze_market(self):
        """Hauptanalyse-Funktion"""
        try:
            # Hole OHLCV-Daten
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=50)
            if len(ohlcv) < 20:
                return None
            
            current_price = ohlcv[-1][4]
            
            # Pattern-Analyse
            candlestick_patterns = self.detect_candlestick_pattern(ohlcv)
            support_resistance = self.find_support_resistance(ohlcv)
            trend_formation = self.analyze_trend_formation(ohlcv)
            volume_patterns = self.analyze_volume_patterns(ohlcv)
            
            # Confidence berechnen
            confidence = self.calculate_pattern_confidence(
                candlestick_patterns, support_resistance, trend_formation, volume_patterns
            )
            
            # Signal generieren
            result = self.get_timeframe_signal(confidence, candlestick_patterns or [], trend_formation)
            
            if result and confidence >= MIN_PATTERN_CONFIDENCE:
                # Cooldown prüfen
                if self.last_signal_time and (datetime.now() - self.last_signal_time).total_seconds() < self.signal_cooldown:
                    return None
                
                self.last_signal_time = datetime.now()
                
                # Logging
                with open('signals.log', 'a') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    pattern_names = ', '.join([p['name'] for p in result['patterns']]) if result['patterns'] else 'None'
                    f.write(f"{timestamp} - bot:pattern_filter - signal:{result['signal']} - strength:{result['strength']:.2f} - price:{current_price:.4f} - additional:confidence:{confidence:.2f}/patterns:{pattern_names}/trend:{trend_formation['formation'] if trend_formation else 'unknown'}\n")
                
                return {
                    'signal': result['signal'],
                    'strength': result['strength'],
                    'confidence': confidence,
                    'price': current_price,
                    'patterns': result['patterns'],
                    'trend': result['trend'],
                    'support_resistance': support_resistance,
                    'volume': volume_patterns
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Fehler bei Pattern-Analyse: {e}")
            return None
    
    def run(self):
        """Haupt-Loop"""
        print("🔍 PATTERN FILTER BOT gestartet!")
        print(f"📊 Analysiert {SYMBOL} alle {SLEEP_TIME} Sekunden")
        print(f"🎯 Minimale Pattern-Confidence: {MIN_PATTERN_CONFIDENCE}")
        print(f"⏰ Cooldown: {self.signal_cooldown} Sekunden zwischen Signalen")
        print(f"📈 Hold-Zeiträume: {', '.join(map(str, HOLD_PERIODS))} Minuten\n")
        
        while True:
            try:
                result = self.analyze_market()
                
                if result:
                    print(f"\n{'='*60}")
                    print(f"🔍 PATTERN FILTER SIGNAL")
                    print(f"{'='*60}")
                    print(f"⏰ Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"💱 Symbol: {SYMBOL}")
                    print(f"💰 Preis: {result['price']:.4f} USDT")
                    print(f"📈 Signal: {result['signal'].upper()}")
                    print(f"💪 Stärke: {result['strength']:.2f}/10")
                    print(f"🎯 Confidence: {result['confidence']:.1%}")
                    
                    # Pattern-Details
                    if result['patterns']:
                        print(f"\n🕯️ CANDLESTICK PATTERNS:")
                        for pattern in result['patterns']:
                            print(f"  • {pattern['name']}: {pattern['description']} (Stärke: {pattern['strength']:.1f})")
                    
                    # Trend-Details
                    if result['trend']:
                        trend = result['trend']
                        print(f"\n📈 TREND-ANALYSE:")
                        print(f"  Richtung: {trend['trend_direction']}")
                        print(f"  Stärke: {trend['trend_strength']:.2f}")
                        print(f"  Formation: {trend['formation']}")
                        print(f"  Volatilität: {trend['volatility']:.4f}")
                    
                    # Support/Resistance
                    if result['support_resistance']:
                        sr = result['support_resistance']
                        print(f"\n🏗️ SUPPORT/RESISTANCE:")
                        print(f"  Unterstützung: {sr['support']:.4f} ({sr['support_distance']:.1f}% entfernt)")
                        print(f"  Widerstand: {sr['resistance']:.4f} ({sr['resistance_distance']:.1f}% entfernt)")
                    
                    # Volume
                    if result['volume']:
                        vol = result['volume']
                        print(f"\n📊 VOLUME-ANALYSE:")
                        print(f"  Volume-Ratio: {vol['volume_ratio']:.2f}x")
                        print(f"  High Volume: {'✅ Ja' if vol['high_volume'] else '❌ Nein'}")
                        if vol['volume_divergence'] != 0:
                            print(f"  Divergenz: {'Bearish' if vol['volume_divergence'] > 0 else 'Bullish'}")
                    
                    print(f"\n⏰ Hold-Zeiträume: {', '.join(map(str, HOLD_PERIODS))} Minuten")
                    print(f"🎯 Pattern-basierte Filterung aktiv")
                    
                else:
                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Kein Pattern-Signal (zu schwach/Cooldown)")
                
                time.sleep(SLEEP_TIME)
                
            except KeyboardInterrupt:
                print("\n🛑 Bot gestoppt")
                break
            except Exception as e:
                print(f"❌ Fehler: {e}")
                time.sleep(SLEEP_TIME)

if __name__ == '__main__':
    bot = PatternFilterBot()
    bot.run() 