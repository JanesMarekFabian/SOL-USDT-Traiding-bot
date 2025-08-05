"""
ADVANCED MASTER SETUP BACKTEST - Mit echten Marktdaten

Erweiterte Backtest-Funktionen:
✅ Echte Marktdaten von MEXC API
✅ Realistische P&L Berechnung
✅ Detaillierte Performance-Analyse
✅ Visualisierung der Ergebnisse
✅ Optimierung von Parametern

ZIEL: Realistische Performance-Bewertung mit echten Daten
"""

import ccxt
import os
import re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

class AdvancedMasterBacktest:
    def __init__(self, log_file='master_setups_v3.log'):
        self.log_file = log_file
        self.signals = []
        self.trades = []
        self.performance_metrics = {}
        
        # MEXC API Setup
        self.api_key = os.getenv('MEXC_API_KEY', '')
        self.api_secret = os.getenv('MEXC_SECRET', '')
        
        self.exchange = ccxt.mexc({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'options': {'defaultType': 'future'},
            'enableRateLimit': True,
        })
        
        self.symbol = 'SOL/USDT'
        
    def parse_log_file(self):
        """Parst die Master-Setup Log-Datei"""
        if not os.path.exists(self.log_file):
            print(f"❌ Log-Datei {self.log_file} nicht gefunden!")
            return False
            
        print(f"📊 Parse {self.log_file}...")
        
        with open(self.log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    signal_data = self.parse_signal_line(line)
                    if signal_data:
                        self.signals.append(signal_data)
                        
                except Exception as e:
                    print(f"⚠️ Fehler beim Parsen von Zeile {line_num}: {e}")
                    continue
        
        print(f"✅ {len(self.signals)} Signale geparst")
        return True
    
    def parse_signal_line(self, line):
        """Parst eine einzelne Signal-Line"""
        parts = line.split(' - ')
        if len(parts) < 4:
            return None
            
        # Zeitstempel
        timestamp_str = parts[0].strip()
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        
        # Signal-Typ
        signal_part = parts[2].strip()
        if signal_part.startswith('signal:'):
            signal_type = signal_part[7:]
        else:
            return None
            
        # Stärke
        strength_part = parts[3].strip()
        if strength_part.startswith('strength:'):
            strength = float(strength_part[9:])
        else:
            strength = 0.0
            
        # Preis
        price_part = parts[4].strip()
        if price_part.startswith('price:'):
            price = float(price_part[6:])
        else:
            price = 0.0
            
        # Additional Data
        additional_part = parts[5].strip()
        additional_data = self.parse_additional_data(additional_part)
        
        return {
            'timestamp': timestamp,
            'signal': signal_type,
            'strength': strength,
            'price': price,
            'score': additional_data.get('score', 0.0),
            'confidence': additional_data.get('confidence', 0.0),
            'bot_count': additional_data.get('bot_count', 0),
            'bots': additional_data.get('bots', []),
            'base': additional_data.get('base', 0.0),
            'orderbook_bonus': additional_data.get('orderbook_bonus', 0.0)
        }
    
    def parse_additional_data(self, additional_str):
        """Parst additional Data String"""
        data = {}
        
        # Score
        score_match = re.search(r'score:([\d.]+)', additional_str)
        if score_match:
            data['score'] = float(score_match.group(1))
            
        # Confidence
        confidence_match = re.search(r'confidence:([\d.]+)', additional_str)
        if confidence_match:
            data['confidence'] = float(confidence_match.group(1))
            
        # Bot Count
        bot_count_match = re.search(r'bot_count:(\d+)', additional_str)
        if bot_count_match:
            data['bot_count'] = int(bot_count_match.group(1))
            
        # Bots
        bots_match = re.search(r'bots:([^/]+)', additional_str)
        if bots_match:
            data['bots'] = bots_match.group(1).split(',')
            
        # Base
        base_match = re.search(r'base:([\d.]+)', additional_str)
        if base_match:
            data['base'] = float(base_match.group(1))
            
        # Orderbook Bonus
        bonus_match = re.search(r'orderbook_bonus:([\d.]+)', additional_str)
        if bonus_match:
            data['orderbook_bonus'] = float(bonus_match.group(1))
            
        return data
    
    def get_historical_data(self, start_time, end_time):
        """Holt historische Marktdaten von MEXC"""
        try:
            print(f"📊 Hole Marktdaten von {start_time} bis {end_time}...")
            
            # Konvertiere zu Timestamp
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)
            
            # Hole OHLCV Daten (1-Minuten Kerzen)
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe='1m',
                since=start_ts,
                limit=1000
            )
            
            # Konvertiere zu DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            print(f"✅ {len(df)} Marktdaten-Punkte geladen")
            return df
            
        except Exception as e:
            print(f"❌ Fehler beim Laden der Marktdaten: {e}")
            return None
    
    def find_exit_price_realistic(self, entry_time, hold_minutes, signal_type):
        """Findet realistische Exit-Preise basierend auf Marktdaten"""
        try:
            exit_time = entry_time + timedelta(minutes=hold_minutes)
            
            # Hole Marktdaten für den Zeitraum
            start_time = entry_time - timedelta(minutes=5)  # Buffer
            end_time = exit_time + timedelta(minutes=5)     # Buffer
            
            market_data = self.get_historical_data(start_time, end_time)
            
            if market_data is None or market_data.empty:
                return None
            
            # Finde den Preis zur Exit-Zeit
            exit_data = market_data[market_data.index >= exit_time]
            
            if exit_data.empty:
                # Verwende den letzten verfügbaren Preis
                exit_price = market_data['close'].iloc[-1]
            else:
                # Verwende den ersten Preis nach Exit-Zeit
                exit_price = exit_data['close'].iloc[0]
            
            return exit_price
            
        except Exception as e:
            print(f"⚠️ Fehler beim Finden des Exit-Preises: {e}")
            return None
    
    def simulate_trades_advanced(self, hold_periods=[5, 10, 20]):
        """Simuliert Trades mit echten Marktdaten"""
        print(f"🔄 Simuliere Trades mit echten Marktdaten...")
        
        for hold_minutes in hold_periods:
            trades = []
            
            for i, signal in enumerate(self.signals):
                entry_price = signal['price']
                entry_time = signal['timestamp']
                signal_type = signal['signal']
                
                # Finde realistische Exit-Preis
                exit_price = self.find_exit_price_realistic(entry_time, hold_minutes, signal_type)
                
                if exit_price:
                    # Berechne P&L
                    if signal_type == 'buy':
                        pnl = ((exit_price - entry_price) / entry_price) * 100
                    else:  # sell
                        pnl = ((entry_price - exit_price) / entry_price) * 100
                    
                    trade = {
                        'entry_time': entry_time,
                        'exit_time': entry_time + timedelta(minutes=hold_minutes),
                        'signal': signal_type,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'hold_minutes': hold_minutes,
                        'strength': signal['strength'],
                        'score': signal['score'],
                        'confidence': signal['confidence'],
                        'bot_count': signal['bot_count'],
                        'bots': signal['bots']
                    }
                    trades.append(trade)
                    
                    print(f"  Trade {i+1}: {signal_type.upper()} @ {entry_price:.4f} → {exit_price:.4f} = {pnl:.2f}%")
            
            self.trades.append({
                'hold_minutes': hold_minutes,
                'trades': trades
            })
            
            print(f"✅ {hold_minutes}min: {len(trades)} Trades simuliert")
    
    def calculate_advanced_metrics(self):
        """Berechnet erweiterte Performance-Metriken"""
        print("📊 Berechne erweiterte Performance-Metriken...")
        
        for trade_set in self.trades:
            hold_minutes = trade_set['hold_minutes']
            trades = trade_set['trades']
            
            if not trades:
                continue
                
            # Grundlegende Metriken
            total_trades = len(trades)
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] < 0]
            
            win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
            
            # P&L Metriken
            total_pnl = sum(t['pnl'] for t in trades)
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            
            # Profit Factor
            gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
            gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Max Drawdown
            cumulative_pnl = []
            current_pnl = 0
            for trade in trades:
                current_pnl += trade['pnl']
                cumulative_pnl.append(current_pnl)
            
            max_drawdown = 0
            peak = 0
            for pnl in cumulative_pnl:
                if pnl > peak:
                    peak = pnl
                drawdown = peak - pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Sharpe Ratio
            returns = [t['pnl'] for t in trades]
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            
            # Erweiterte Analysen
            strong_signals = [t for t in trades if t['strength'] >= 6.0]
            weak_signals = [t for t in trades if t['strength'] < 6.0]
            
            strong_win_rate = len([t for t in strong_signals if t['pnl'] > 0]) / len(strong_signals) * 100 if strong_signals else 0
            weak_win_rate = len([t for t in weak_signals if t['pnl'] > 0]) / len(weak_signals) * 100 if weak_signals else 0
            
            high_consensus = [t for t in trades if t['bot_count'] >= 3]
            low_consensus = [t for t in trades if t['bot_count'] < 3]
            
            high_consensus_win_rate = len([t for t in high_consensus if t['pnl'] > 0]) / len(high_consensus) * 100 if high_consensus else 0
            low_consensus_win_rate = len([t for t in low_consensus if t['pnl'] > 0]) / len(low_consensus) * 100 if low_consensus else 0
            
            # Confidence-basierte Analyse
            high_confidence = [t for t in trades if t['confidence'] >= 0.7]
            low_confidence = [t for t in trades if t['confidence'] < 0.7]
            
            high_confidence_win_rate = len([t for t in high_confidence if t['pnl'] > 0]) / len(high_confidence) * 100 if high_confidence else 0
            low_confidence_win_rate = len([t for t in low_confidence if t['pnl'] > 0]) / len(low_confidence) * 100 if low_confidence else 0
            
            metrics = {
                'hold_minutes': hold_minutes,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'strong_signals': len(strong_signals),
                'weak_signals': len(weak_signals),
                'strong_win_rate': strong_win_rate,
                'weak_win_rate': weak_win_rate,
                'high_consensus_trades': len(high_consensus),
                'low_consensus_trades': len(low_consensus),
                'high_consensus_win_rate': high_consensus_win_rate,
                'low_consensus_win_rate': low_consensus_win_rate,
                'high_confidence_trades': len(high_confidence),
                'low_confidence_trades': len(low_confidence),
                'high_confidence_win_rate': high_confidence_win_rate,
                'low_confidence_win_rate': low_confidence_win_rate,
                'trades': trades,
                'cumulative_pnl': cumulative_pnl
            }
            
            self.performance_metrics[hold_minutes] = metrics
    
    def print_advanced_results(self):
        """Gibt erweiterte Backtest-Ergebnisse aus"""
        print("\n" + "="*80)
        print("🎯 ERWEITERTE MASTER SETUP BACKTEST ERGEBNISSE")
        print("="*80)
        
        for hold_minutes, metrics in self.performance_metrics.items():
            print(f"\n📊 HOLD-ZEITRAUM: {hold_minutes} MINUTEN")
            print("-" * 50)
            print(f"📈 Gesamt-Trades: {metrics['total_trades']}")
            print(f"🎯 Win-Rate: {metrics['win_rate']:.1f}%")
            print(f"💰 Gesamt-P&L: {metrics['total_pnl']:.2f}%")
            print(f"📊 Durchschnittlicher Gewinn: {metrics['avg_win']:.2f}%")
            print(f"📉 Durchschnittlicher Verlust: {metrics['avg_loss']:.2f}%")
            print(f"📈 Profit Factor: {metrics['profit_factor']:.2f}")
            print(f"📊 Max Drawdown: {metrics['max_drawdown']:.2f}%")
            print(f"📈 Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            
            print(f"\n🔍 SIGNAL-ANALYSE:")
            print(f"  Starke Signale (≥6.0): {metrics['strong_signals']} Trades")
            print(f"  Schwache Signale (<6.0): {metrics['weak_signals']} Trades")
            print(f"  Starke Signale Win-Rate: {metrics['strong_win_rate']:.1f}%")
            print(f"  Schwache Signale Win-Rate: {metrics['weak_win_rate']:.1f}%")
            
            print(f"\n🤖 BOT-KONSENS ANALYSE:")
            print(f"  Hoher Konsens (≥3 Bots): {metrics['high_consensus_trades']} Trades")
            print(f"  Niedriger Konsens (<3 Bots): {metrics['low_consensus_trades']} Trades")
            print(f"  Hoher Konsens Win-Rate: {metrics['high_consensus_win_rate']:.1f}%")
            print(f"  Niedriger Konsens Win-Rate: {metrics['low_consensus_win_rate']:.1f}%")
            
            print(f"\n🎯 CONFIDENCE-ANALYSE:")
            print(f"  Hohe Confidence (≥0.7): {metrics['high_confidence_trades']} Trades")
            print(f"  Niedrige Confidence (<0.7): {metrics['low_confidence_trades']} Trades")
            print(f"  Hohe Confidence Win-Rate: {metrics['high_confidence_win_rate']:.1f}%")
            print(f"  Niedrige Confidence Win-Rate: {metrics['low_confidence_win_rate']:.1f}%")
    
    def create_performance_charts(self):
        """Erstellt Performance-Charts"""
        try:
            print("📊 Erstelle Performance-Charts...")
            
            # Erstelle Figure mit Subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Master Setup Backtest Performance', fontsize=16)
            
            # 1. Cumulative P&L für alle Hold-Zeiträume
            ax1 = axes[0, 0]
            for hold_minutes, metrics in self.performance_metrics.items():
                if 'cumulative_pnl' in metrics:
                    ax1.plot(range(len(metrics['cumulative_pnl'])), 
                            metrics['cumulative_pnl'], 
                            label=f'{hold_minutes}min', 
                            marker='o', markersize=3)
            
            ax1.set_title('Cumulative P&L')
            ax1.set_xlabel('Trade Number')
            ax1.set_ylabel('Cumulative P&L (%)')
            ax1.legend()
            ax1.grid(True)
            
            # 2. Win-Rate Vergleich
            ax2 = axes[0, 1]
            hold_periods = list(self.performance_metrics.keys())
            win_rates = [metrics['win_rate'] for metrics in self.performance_metrics.values()]
            
            bars = ax2.bar(hold_periods, win_rates, color=['#2E8B57', '#4682B4', '#CD5C5C'])
            ax2.set_title('Win-Rate nach Hold-Zeitraum')
            ax2.set_xlabel('Hold-Zeitraum (Minuten)')
            ax2.set_ylabel('Win-Rate (%)')
            ax2.set_ylim(0, 100)
            
            # Füge Werte über Bars hinzu
            for bar, rate in zip(bars, win_rates):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                        f'{rate:.1f}%', ha='center', va='bottom')
            
            # 3. Signal-Stärke vs Performance
            ax3 = axes[1, 0]
            strong_pnls = []
            weak_pnls = []
            
            for hold_minutes, metrics in self.performance_metrics.items():
                strong_trades = [t for t in metrics['trades'] if t['strength'] >= 6.0]
                weak_trades = [t for t in metrics['trades'] if t['strength'] < 6.0]
                
                if strong_trades:
                    strong_pnls.append(np.mean([t['pnl'] for t in strong_trades]))
                if weak_trades:
                    weak_pnls.append(np.mean([t['pnl'] for t in weak_trades]))
            
            if strong_pnls and weak_pnls:
                x = np.arange(len(hold_periods))
                width = 0.35
                
                ax3.bar(x - width/2, strong_pnls, width, label='Starke Signale (≥6.0)', color='#2E8B57')
                ax3.bar(x + width/2, weak_pnls, width, label='Schwache Signale (<6.0)', color='#CD5C5C')
                
                ax3.set_title('Durchschnittlicher P&L nach Signal-Stärke')
                ax3.set_xlabel('Hold-Zeitraum (Minuten)')
                ax3.set_ylabel('Durchschnittlicher P&L (%)')
                ax3.set_xticks(x)
                ax3.set_xticklabels(hold_periods)
                ax3.legend()
                ax3.grid(True)
            
            # 4. Bot-Konsens Analyse
            ax4 = axes[1, 1]
            high_consensus_rates = []
            low_consensus_rates = []
            
            for hold_minutes, metrics in self.performance_metrics.items():
                high_consensus_rates.append(metrics['high_consensus_win_rate'])
                low_consensus_rates.append(metrics['low_consensus_win_rate'])
            
            x = np.arange(len(hold_periods))
            width = 0.35
            
            ax4.bar(x - width/2, high_consensus_rates, width, label='Hoher Konsens (≥3 Bots)', color='#4682B4')
            ax4.bar(x + width/2, low_consensus_rates, width, label='Niedriger Konsens (<3 Bots)', color='#FF6B6B')
            
            ax4.set_title('Win-Rate nach Bot-Konsens')
            ax4.set_xlabel('Hold-Zeitraum (Minuten)')
            ax4.set_ylabel('Win-Rate (%)')
            ax4.set_xticks(x)
            ax4.set_xticklabels(hold_periods)
            ax4.legend()
            ax4.grid(True)
            
            plt.tight_layout()
            plt.savefig('master_setup_backtest_results.png', dpi=300, bbox_inches='tight')
            print("✅ Charts gespeichert als 'master_setup_backtest_results.png'")
            
        except Exception as e:
            print(f"❌ Fehler beim Erstellen der Charts: {e}")
    
    def run_advanced_backtest(self):
        """Führt erweiterten Backtest durch"""
        print("🚀 STARTE ERWEITERTEN MASTER SETUP BACKTEST")
        print("="*50)
        
        # Parse Log-Datei
        if not self.parse_log_file():
            return
        
        # Simuliere Trades mit echten Marktdaten
        self.simulate_trades_advanced()
        
        # Berechne erweiterte Performance
        self.calculate_advanced_metrics()
        
        # Ergebnisse ausgeben
        self.print_advanced_results()
        
        # Charts erstellen
        self.create_performance_charts()
        
        print(f"\n✅ ERWEITERTER BACKTEST ABGESCHLOSSEN")
        print("="*50)

if __name__ == '__main__':
    backtest = AdvancedMasterBacktest()
    backtest.run_advanced_backtest() 