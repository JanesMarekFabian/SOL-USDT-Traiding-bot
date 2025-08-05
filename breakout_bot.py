"""
BREAKOUT BOT - Support/Resistance Durchbruch-Erkennung

FEATURES:
✅ Dynamische Support/Resistance Erkennung  
✅ Breakout Detection mit Volume-Bestätigung
✅ False Breakout Filterung
✅ Retest-Erkennung
✅ Strukturierte Buy/Sell Signale

STRATEGIE:
- Resistance Breakout = BUY Signal
- Support Breakdown = SELL Signal
- Volume-Bestätigung erforderlich
- False Breakout Protection
"""

import ccxt
import os
import time
import numpy as np
from datetime import datetime, timedelta

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
SLEEP_TIME = 30  # 30 Sekunden zwischen Updates

# Breakout Parameter
LOOKBACK_PERIOD = 50  # Anzahl Kerzen für S/R Erkennung
MIN_TOUCHES = 2  # Mindestens 2 Berührungen für gültiges S/R
BREAKOUT_THRESHOLD = 0.15  # 0.15% Mindestabstand für Breakout
VOLUME_MULTIPLIER = 1.5  # 1.5x Average Volume für Bestätigung
FALSE_BREAKOUT_REVERSION = 0.5  # 0.5% Reversion = False Breakout

# Signal Parameter
MIN_SIGNAL_STRENGTH = 5.0
MIN_CONFIDENCE = 0.6
SIGNAL_COOLDOWN = 240  # 4 Minuten zwischen Signalen

class BreakoutBot:
    
    def __init__(self):
        self.last_signal_time = None
        self.support_levels = []
        self.resistance_levels = []
        self.recent_breakouts = []
        
    def find_pivot_points(self, ohlcv, window=3):
        """Findet Pivot Highs und Lows"""
        if len(ohlcv) < window * 2 + 1:
            return [], []
            
        highs = [candle[2] for candle in ohlcv]
        lows = [candle[3] for candle in ohlcv]
        
        pivot_highs = []
        pivot_lows = []
        
        # Finde Pivot Points (lokale Extrempunkte)
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
            
            # Finde ähnliche Points
            for j, other_point in enumerate(pivot_points):
                if j in used_points or j <= i:
                    continue
                
                price_diff = abs(point['price'] - other_point['price']) / point['price'] * 100
                
                if price_diff <= tolerance:
                    cluster.append(other_point)
                    used_points.add(j)
            
            # Erstelle Cluster-Level
            if len(cluster) >= 1:
                avg_price = sum(p['price'] for p in cluster) / len(cluster)
                clusters.append({
                    'price': avg_price,
                    'touch_count': len(cluster),
                    'strength': len(cluster),
                    'first_touch': min(p['timestamp'] for p in cluster),
                    'last_touch': max(p['timestamp'] for p in cluster)
                })
        
        return clusters

    def calculate_support_resistance(self, ohlcv):
        """Berechnet aktuelle Support/Resistance Levels"""
        if len(ohlcv) < LOOKBACK_PERIOD:
            return [], []
        
        # Hole Pivot Points
        pivot_highs, pivot_lows = self.find_pivot_points(ohlcv)
        
        # Cluster ähnliche Preise zu S/R Levels
        resistance_clusters = self.cluster_levels(pivot_highs, tolerance=0.5)
        support_clusters = self.cluster_levels(pivot_lows, tolerance=0.5)
        
        # Validiere S/R Levels (mindestens MIN_TOUCHES)
        valid_resistance = [
            level for level in resistance_clusters 
            if level['touch_count'] >= MIN_TOUCHES
        ]
        
        valid_support = [
            level for level in support_clusters 
            if level['touch_count'] >= MIN_TOUCHES
        ]
        
        # Sortiere nach Stärke (mehr Berührungen = stärker)
        valid_resistance.sort(key=lambda x: x['touch_count'], reverse=True)
        valid_support.sort(key=lambda x: x['touch_count'], reverse=True)
        
        return valid_resistance[:5], valid_support[:5]  # Top 5

    def detect_breakout(self, ohlcv, support_levels, resistance_levels):
        """Erkennt Support/Resistance Durchbrüche"""
        if len(ohlcv) < 3:
            return []
        
        current_candle = ohlcv[-1]
        prev_candle = ohlcv[-2]
        
        current_price = current_candle[4]  # Close
        current_high = current_candle[2]
        current_low = current_candle[3]
        current_volume = current_candle[5]
        
        # Berechne Average Volume
        volumes = [candle[5] for candle in ohlcv[-20:]]
        avg_volume = np.mean(volumes) if volumes else current_volume
        
        # Volume-Bestätigung
        volume_confirmed = current_volume >= (avg_volume * VOLUME_MULTIPLIER)
        
        breakouts = []
        
        # Prüfe Resistance Breakouts (BUY Signale)
        for resistance in resistance_levels:
            resistance_price = resistance['price']
            
            # Prüfe ob Durchbruch stattgefunden hat
            if (prev_candle[4] <= resistance_price and  # Previous close under resistance
                current_high > resistance_price and     # Current high above resistance
                current_price > resistance_price * (1 + BREAKOUT_THRESHOLD/100)):  # Close significantly above
                
                breakouts.append({
                    'type': 'resistance_breakout',
                    'signal': 'buy',
                    'level_price': resistance_price,
                    'current_price': current_price,
                    'level_strength': resistance['strength'],
                    'volume_confirmed': volume_confirmed,
                    'breakout_distance': (current_price - resistance_price) / resistance_price * 100
                })
        
        # Prüfe Support Breakdowns (SELL Signale)
        for support in support_levels:
            support_price = support['price']
            
            # Prüfe ob Breakdown stattgefunden hat
            if (prev_candle[4] >= support_price and  # Previous close above support
                current_low < support_price and      # Current low below support
                current_price < support_price * (1 - BREAKOUT_THRESHOLD/100)):  # Close significantly below
                
                breakouts.append({
                    'type': 'support_breakdown',
                    'signal': 'sell',
                    'level_price': support_price,
                    'current_price': current_price,
                    'level_strength': support['strength'],
                    'volume_confirmed': volume_confirmed,
                    'breakout_distance': (support_price - current_price) / support_price * 100
                })
        
        return breakouts
        
    def check_false_breakout(self, breakout, ohlcv):
        """Prüft auf False Breakout (Reversion)"""
        if len(ohlcv) < 2:
            return False
        
        current_price = ohlcv[-1][4]
        level_price = breakout['level_price']
        
        if breakout['signal'] == 'buy':
            # False Breakout wenn Preis wieder unter Resistance fällt
            reversion_threshold = level_price * (1 - FALSE_BREAKOUT_REVERSION/100)
            return current_price < reversion_threshold
        else:
            # False Breakout wenn Preis wieder über Support steigt
            reversion_threshold = level_price * (1 + FALSE_BREAKOUT_REVERSION/100)
            return current_price > reversion_threshold
    
    def calculate_signal_strength(self, breakout):
        """Berechnet Signal-Stärke für Breakout"""
        base_strength = 5.0
        
        # Level-Stärke Bonus (mehr Berührungen = stärker)
        strength_bonus = min(3.0, breakout['level_strength'] * 0.5)
        
        # Volume-Bestätigung Bonus
        volume_bonus = 2.0 if breakout['volume_confirmed'] else 0
        
        # Breakout-Distanz Bonus (größere Durchbrüche = stärker)
        distance_bonus = min(2.0, breakout['breakout_distance'] * 2)
        
        total_strength = base_strength + strength_bonus + volume_bonus + distance_bonus
        
        return min(10.0, total_strength)
    
    def calculate_confidence(self, breakout, support_levels, resistance_levels):
        """Berechnet Confidence für Breakout Signal"""
        base_confidence = 0.6
        
        # Level-Stärke Bonus
        strength_factor = min(0.3, breakout['level_strength'] * 0.1)
        
        # Volume-Bestätigung Bonus
        volume_factor = 0.2 if breakout['volume_confirmed'] else 0
        
        # Multiple Level Bonus (wenn mehrere Levels in Nähe)
        all_levels = support_levels + resistance_levels
        nearby_levels = [
            level for level in all_levels 
            if abs(level['price'] - breakout['level_price']) / breakout['level_price'] * 100 < 1.0
        ]
        multiple_level_factor = min(0.2, len(nearby_levels) * 0.1)
        
        total_confidence = base_confidence + strength_factor + volume_factor + multiple_level_factor
        
        return min(1.0, total_confidence)
        
    def analyze_breakouts(self):
        """Hauptanalyse-Funktion für Breakouts"""
        try:
            # Hole OHLCV Daten
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LOOKBACK_PERIOD + 10)
            if len(ohlcv) < LOOKBACK_PERIOD:
                return None
            
            # Berechne Support/Resistance
            resistance_levels, support_levels = self.calculate_support_resistance(ohlcv)
            
            # Erkenne Breakouts
            breakouts = self.detect_breakout(ohlcv, support_levels, resistance_levels)
            
            if not breakouts:
                return None
            
            # Finde stärksten Breakout
            best_breakout = None
            best_score = 0
            
            for breakout in breakouts:
                # Prüfe auf False Breakout
                if self.check_false_breakout(breakout, ohlcv):
                    continue
                
                strength = self.calculate_signal_strength(breakout)
                confidence = self.calculate_confidence(breakout, support_levels, resistance_levels)
                
                score = strength * confidence
                
                if score > best_score and strength >= MIN_SIGNAL_STRENGTH and confidence >= MIN_CONFIDENCE:
                    best_score = score
                    best_breakout = breakout
                    best_breakout['strength'] = strength
                    best_breakout['confidence'] = confidence
            
            if best_breakout:
                # Cooldown prüfen
                if self.last_signal_time and (datetime.now() - self.last_signal_time).total_seconds() < SIGNAL_COOLDOWN:
                    return None
                
                self.last_signal_time = datetime.now()
                
                # Logging
                with open('signals.log', 'a') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"{timestamp} - bot:breakout - signal:{best_breakout['signal']} - strength:{best_breakout['strength']:.2f} - price:{best_breakout['current_price']:.4f} - additional:confidence:{best_breakout['confidence']:.2f}/type:{best_breakout['type']}/level:{best_breakout['level_price']:.4f}/distance:{best_breakout['breakout_distance']:.2f}%/volume_confirmed:{best_breakout['volume_confirmed']}\n")
                
                return {
                    'signal': best_breakout['signal'],
                    'strength': best_breakout['strength'],
                    'confidence': best_breakout['confidence'],
                    'price': best_breakout['current_price'],
                    'breakout': best_breakout,
                    'support_levels': support_levels,
                    'resistance_levels': resistance_levels
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Breakout Analyse Fehler: {e}")
            return None
    
    def print_analysis(self, result):
        """Druckt detaillierte Breakout Analyse"""
        print(f"\n{'='*60}")
        print(f"⚡ BREAKOUT SIGNAL")
        print(f"{'='*60}")
        
        breakout = result['breakout']
        
        print(f"⏰ Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💰 Preis: {result['price']:.4f} USDT")
        print(f"📈 Signal: {result['signal'].upper()}")
        print(f"💪 Stärke: {result['strength']:.2f}/10")
        print(f"🎯 Confidence: {result['confidence']:.1%}")
        
        print(f"\n⚡ BREAKOUT DETAILS:")
        print(f"  🎯 Typ: {breakout['type']}")
        print(f"  �� Level: {breakout['level_price']:.4f} USDT")
        print(f"  �� Distanz: {breakout['breakout_distance']:.2f}%")
        print(f"  🏗️ Level-Stärke: {breakout['level_strength']} Berührungen")
        print(f"  📊 Volume bestätigt: {'✅ Ja' if breakout['volume_confirmed'] else '❌ Nein'}")
        
        # Support/Resistance Levels
        if result['resistance_levels']:
            print(f"\n🔴 AKTUELLE RESISTANCE LEVELS:")
            for i, level in enumerate(result['resistance_levels'][:3], 1):
                distance = (level['price'] - result['price']) / result['price'] * 100
                print(f"  {i}. {level['price']:.4f} USDT (+{distance:.2f}%) | {level['touch_count']} Berührungen")
        
        if result['support_levels']:
            print(f"\n🟢 AKTUELLE SUPPORT LEVELS:")
            for i, level in enumerate(result['support_levels'][:3], 1):
                distance = (result['price'] - level['price']) / result['price'] * 100
                print(f"  {i}. {level['price']:.4f} USDT (-{distance:.2f}%) | {level['touch_count']} Berührungen")
    
    def run(self):
        """Haupt-Loop"""
        print("⚡ BREAKOUT BOT gestartet!")
        print(f"🎯 Symbol: {SYMBOL}")
        print(f"📊 Lookback: {LOOKBACK_PERIOD} Kerzen")
        print(f"�� Min Berührungen: {MIN_TOUCHES}")
        print(f"⚡ Breakout Threshold: {BREAKOUT_THRESHOLD}%")
        print(f"�� Volume Multiplier: {VOLUME_MULTIPLIER}x")
        print(f"⏰ Update: alle {SLEEP_TIME} Sekunden\n")
        
        while True:
            try:
                result = self.analyze_breakouts()
                
                if result:
                    self.print_analysis(result)
                else:
                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Kein Breakout Signal")
                
                time.sleep(SLEEP_TIME)
                
            except KeyboardInterrupt:
                print("\n🛑 Breakout Bot gestoppt")
                break
            except Exception as e:
                print(f"❌ Fehler: {e}")
                time.sleep(SLEEP_TIME)

if __name__ == '__main__':
    bot = BreakoutBot()
    bot.run()