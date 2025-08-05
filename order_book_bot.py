"""
ORDER BOOK INTELLIGENCE BOT

Nutzt MEXC Order Book Daten um Market Maker Aktivitäten zu erkennen:
✅ Support/Resistance Walls
✅ Order Book Imbalance  
✅ Liquidation Level Estimates
✅ Market Maker Bias Detection

Basiert auf verfügbaren MEXC API Daten
"""

import ccxt
import os
import time
from datetime import datetime
from collections import defaultdict

API_KEY = os.getenv('MEXC_API_KEY', '')
API_SECRET = os.getenv('MEXC_SECRET', '')

exchange = ccxt.mexc({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {'defaultType': 'future'},
    'enableRateLimit': True,
})

SYMBOL = 'SOL/USDT'
SLEEP_TIME = 60  # 1 Minute zwischen Updates

# Order Book Analysis Parameter
MIN_WALL_SIZE = 500  # Minimum SOL für "Wall"
IMBALANCE_THRESHOLD = 0.6  # 60% für starken Bias
LIQUIDATION_THRESHOLD = 2.0  # 2% für Liquidation Estimate

class OrderBookBot:
    
    def __init__(self):
        self.last_signal_time = None
        self.signal_cooldown = 300  # 5 Minuten zwischen Signalen
        self.order_book_history = []
        
    def analyze_order_book(self):
        """Analysiert Order Book für Market Maker Signals"""
        try:
            # Hole Order Book
            orderbook = exchange.fetch_order_book(SYMBOL, limit=50)
            ticker = exchange.fetch_ticker(SYMBOL)
            
            current_price = ticker['last']
            bids = orderbook['bids']
            asks = orderbook['asks']
            
            # Analyse durchführen
            analysis = {
                'timestamp': datetime.now(),
                'price': current_price,
                'bid_walls': self.find_walls(bids, 'bid'),
                'ask_walls': self.find_walls(asks, 'ask'),
                'imbalance': self.calculate_imbalance(bids, asks),
                'liquidation_zones': self.estimate_liquidations(bids, asks, current_price),
                'market_bias': None
            }
            
            # Market Bias bestimmen
            analysis['market_bias'] = self.determine_market_bias(analysis)
            
            # Signal generieren
            signal = self.generate_signal(analysis)
            
            return analysis, signal
            
        except Exception as e:
            print(f"❌ Order Book Analyse Fehler: {e}")
            return None, None
    
    def find_walls(self, orders, side):
        """Findet große Order Walls"""
        walls = []
        
        for price, volume in orders:
            if volume >= MIN_WALL_SIZE:
                walls.append({
                    'price': price,
                    'volume': volume,
                    'side': side
                })
        
        # Sortiere nach Volume (größte zuerst)
        walls.sort(key=lambda x: x['volume'], reverse=True)
        return walls[:5]  # Top 5 Walls
    
    def calculate_imbalance(self, bids, asks):
        """Berechnet Order Book Imbalance"""
        # Summe der Top 20 Levels
        bid_volume = sum([volume for price, volume in bids[:20]])
        ask_volume = sum([volume for price, volume in asks[:20]])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.5
            
        bid_ratio = bid_volume / total_volume
        
        return {
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'bid_ratio': bid_ratio,
            'ask_ratio': 1 - bid_ratio
        }
    
    def estimate_liquidations(self, bids, asks, current_price):
        """Schätzt Liquidation Zones"""
        liquidations = {
            'long_liquidations': [],  # Unter current price
            'short_liquidations': []  # Über current price
        }
        
        # Long Liquidations (Bids unter current - X%)
        for price, volume in bids:
            distance_pct = (current_price - price) / current_price * 100
            if distance_pct >= LIQUIDATION_THRESHOLD:
                liquidations['long_liquidations'].append({
                    'price': price,
                    'volume': volume,
                    'distance_pct': distance_pct
                })
        
        # Short Liquidations (Asks über current + X%)
        for price, volume in asks:
            distance_pct = (price - current_price) / current_price * 100
            if distance_pct >= LIQUIDATION_THRESHOLD:
                liquidations['short_liquidations'].append({
                    'price': price,
                    'volume': volume,
                    'distance_pct': distance_pct
                })
        
        return liquidations
    
    def determine_market_bias(self, analysis):
        """Bestimmt Market Maker Bias"""
        signals = []
        
        # Imbalance Analysis
        bid_ratio = analysis['imbalance']['bid_ratio']
        if bid_ratio > IMBALANCE_THRESHOLD:
            signals.append('bid_dominance')
        elif bid_ratio < (1 - IMBALANCE_THRESHOLD):
            signals.append('ask_dominance')
        
        # Wall Analysis
        if len(analysis['bid_walls']) > len(analysis['ask_walls']):
            signals.append('strong_support')
        elif len(analysis['ask_walls']) > len(analysis['bid_walls']):
            signals.append('strong_resistance')
        
        # Liquidation Analysis
        long_liq_count = len(analysis['liquidation_zones']['long_liquidations'])
        short_liq_count = len(analysis['liquidation_zones']['short_liquidations'])
        
        if long_liq_count > short_liq_count * 1.5:
            signals.append('long_heavy')
        elif short_liq_count > long_liq_count * 1.5:
            signals.append('short_heavy')
        
        return signals
    
    def generate_signal(self, analysis):
        """Generiert Trading Signal basierend auf Order Book mit Strong/Weak Classification"""
        market_bias = analysis['market_bias']
        current_price = analysis['price']
        imbalance = analysis['imbalance']
        
        # Signal Logic mit verschiedenen Stärken
        bullish_signals = sum([
            1 for signal in market_bias 
            if signal in ['bid_dominance', 'strong_support', 'short_heavy']
        ])
        
        bearish_signals = sum([
            1 for signal in market_bias 
            if signal in ['ask_dominance', 'strong_resistance', 'long_heavy']
        ])
        
        # Zusätzliche Stärke-Faktoren
        wall_strength = len(analysis['bid_walls']) - len(analysis['ask_walls'])
        imbalance_strength = abs(imbalance['bid_ratio'] - 0.5) * 2  # 0-1 scale
        
        # Cooldown prüfen
        if self.last_signal_time and (datetime.now() - self.last_signal_time).total_seconds() < self.signal_cooldown:
            return None
        
        signal = None
        strength = 0
        signal_type = None  # 'strong' or 'weak'
        
        if bullish_signals >= 2:
            signal = 'buy'
            base_strength = bullish_signals * 2.0
            
            # Bestimme ob STRONG oder WEAK BUY
            if (bullish_signals >= 3 and 
                imbalance['bid_ratio'] > 0.7 and 
                len(analysis['bid_walls']) >= 2):
                signal_type = 'strong'
                strength = base_strength + wall_strength + imbalance_strength * 3
            else:
                signal_type = 'weak'
                strength = base_strength + wall_strength + imbalance_strength
                
        elif bearish_signals >= 2:
            signal = 'sell'
            base_strength = bearish_signals * 2.0
            
            # Bestimme ob STRONG oder WEAK SELL
            if (bearish_signals >= 3 and 
                imbalance['bid_ratio'] < 0.3 and 
                len(analysis['ask_walls']) >= 2):
                signal_type = 'strong'
                strength = base_strength + abs(wall_strength) + imbalance_strength * 3
            else:
                signal_type = 'weak'
                strength = base_strength + abs(wall_strength) + imbalance_strength
        
        if signal:
            self.last_signal_time = datetime.now()
            
            # Logging mit Strong/Weak Classification
            with open('signals.log', 'a') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                bias_str = ','.join(market_bias)
                f.write(f"{timestamp} - bot:order_book - signal:{signal} - strength:{strength:.2f} - price:{current_price:.4f} - additional:type:{signal_type}/bias:{bias_str}/bid_ratio:{analysis['imbalance']['bid_ratio']:.2f}/walls:bid_{len(analysis['bid_walls'])}_ask_{len(analysis['ask_walls'])}\n")
            
            return {
                'signal': signal,
                'signal_type': signal_type,  # 'strong' or 'weak'
                'strength': strength,
                'price': current_price,
                'bias': market_bias,
                'analysis': analysis
            }
        
        return None
    
    def print_analysis(self, analysis):
        """Druckt detaillierte Order Book Analyse"""
        print(f"\n{'='*60}")
        print(f"📊 ORDER BOOK INTELLIGENCE")
        print(f"{'='*60}")
        print(f"⏰ Zeit: {analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💰 Preis: {analysis['price']:.4f} USDT")
        
        # Imbalance
        imbalance = analysis['imbalance']
        print(f"\n⚖️ ORDER BOOK IMBALANCE:")
        print(f"  🟢 Bid Volume: {imbalance['bid_volume']:.0f} SOL ({imbalance['bid_ratio']:.1%})")
        print(f"  🔴 Ask Volume: {imbalance['ask_volume']:.0f} SOL ({imbalance['ask_ratio']:.1%})")
        
        # Walls
        if analysis['bid_walls']:
            print(f"\n🏗️ BID WALLS (Support):")
            for wall in analysis['bid_walls']:
                distance = (analysis['price'] - wall['price']) / analysis['price'] * 100
                print(f"  💪 {wall['price']:.4f} USDT | {wall['volume']:.0f} SOL (-{distance:.2f}%)")
        
        if analysis['ask_walls']:
            print(f"\n🏗️ ASK WALLS (Resistance):")
            for wall in analysis['ask_walls']:
                distance = (wall['price'] - analysis['price']) / analysis['price'] * 100
                print(f"  💪 {wall['price']:.4f} USDT | {wall['volume']:.0f} SOL (+{distance:.2f}%)")
        
        # Market Bias
        print(f"\n🎯 MARKET BIAS:")
        for bias in analysis['market_bias']:
            bias_emoji = {
                'bid_dominance': '🟢 BID DOMINANCE',
                'ask_dominance': '🔴 ASK DOMINANCE', 
                'strong_support': '🏗️ STRONG SUPPORT',
                'strong_resistance': '🏗️ STRONG RESISTANCE',
                'long_heavy': '⚠️ LONG HEAVY',
                'short_heavy': '⚠️ SHORT HEAVY'
            }
            print(f"  {bias_emoji.get(bias, bias)}")
    
    def run(self):
        """Haupt-Loop"""
        print("📊 ORDER BOOK INTELLIGENCE BOT gestartet!")
        print(f"🎯 Symbol: {SYMBOL}")
        print(f"⏰ Update Interval: {SLEEP_TIME} Sekunden")
        print(f"🏗️ Min Wall Size: {MIN_WALL_SIZE} SOL")
        print(f"⚖️ Imbalance Threshold: {IMBALANCE_THRESHOLD}")
        print(f"🎯 Liquidation Threshold: {LIQUIDATION_THRESHOLD}%\n")
        
        while True:
            try:
                analysis, signal = self.analyze_order_book()
                
                if analysis:
                    self.print_analysis(analysis)
                    
                    if signal:
                        print(f"\n🚨 ORDER BOOK SIGNAL:")
                        print(f"  📈 Signal: {signal['signal'].upper()}")
                        print(f"  💪 Stärke: {signal['strength']:.2f}")
                        print(f"  🎯 Bias: {', '.join(signal['bias'])}")
                        print(f"  💰 Preis: {signal['price']:.4f} USDT")
                    else:
                        print(f"\n⏰ Kein Signal (zu schwach/Cooldown)")
                
                time.sleep(SLEEP_TIME)
                
            except KeyboardInterrupt:
                print("\n🛑 Order Book Bot gestoppt")
                break
            except Exception as e:
                print(f"❌ Fehler: {e}")
                time.sleep(SLEEP_TIME)

if __name__ == '__main__':
    bot = OrderBookBot()
    bot.run() 