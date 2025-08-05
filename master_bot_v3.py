"""
MASTER BOT V3 - 4-Bot Konsens System

Koordiniert alle 4 Trading Bots:
✅ Smart Indicator Bot
✅ Pattern Filter Bot  
✅ Order Book Bot (NEW!)
✅ Master Consensus Logic

Features:
✅ Strong/Weak Signal Classification
✅ 4-Bot Consensus Scoring
✅ Order Book Intelligence Integration
✅ Advanced Setup Quality Scoring
"""

import ccxt
import os
import time
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import subprocess
import threading
import sys

API_KEY = os.getenv('MEXC_API_KEY', '')
API_SECRET = os.getenv('MEXC_SECRET', '')

exchange = ccxt.mexc({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {'defaultType': 'future'},
    'enableRateLimit': True,
})

SYMBOL = 'SOL_USDT'
SIGNAL_FILE = 'signals.log'
SLEEP_TIME = 30  # 30 Sekunden zwischen Master-Analysen

# Setup-Qualitäts-Schwellenwerte (V3 - strenger für 4 Bots)
MIN_CONSENSUS_STRENGTH = 4.0  # war 5.0 (mehr Bots = höhere Anforderungen)
MIN_CONSENSUS_CONFIDENCE = 0.65  # war 0.6
MIN_SETUP_SCORE = 7.0  # war 6.0 (4-Bot Konsens = höhere Qualität)

# Hold-Zeiträume
HOLD_PERIODS = [5, 10, 20]  # Minuten

class MasterBotV3:
    def __init__(self):
        self.last_setup_time = None
        self.setup_cooldown = 450  # 7.5 Minuten zwischen Setups (weniger für 4 Bots)
        self.bot_signals = {
            'smart_indicator': None,
            'pattern_filter': None,
            'order_book': None
        }
        self.signal_history = []
        self.sub_bot_processes = []  # Speichert die gestarteten Bot-Prozesse
        self.bots_started = False
        
    def read_recent_signals(self, window_minutes=3):  # Kürzeres Fenster für 4 Bots
        """Liest kürzliche Signale aus signals.log"""
        signals = []
        
        if not os.path.exists(SIGNAL_FILE):
            return signals
        
        try:
            with open(SIGNAL_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        parts = line.split(' - ')
                        if len(parts) < 4:
                            continue
                        
                        # Parse Zeitstempel
                        time_str = parts[0].strip()
                        signal_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        
                        # Prüfe ob Signal innerhalb des Fensters liegt
                        if (datetime.now() - signal_time).total_seconds() > window_minutes * 60:
                            continue
                        
                        # Parse Bot-Name
                        bot_part = parts[1].strip()
                        if bot_part.startswith('bot:'):
                            bot_name = bot_part[4:]
                        else:
                            continue
                        
                        # Parse Signal
                        signal_part = parts[2].strip()
                        if signal_part.startswith('signal:'):
                            signal_type = signal_part[7:]
                            if signal_type not in ['buy', 'sell']:
                                continue
                        else:
                            continue
                        
                        # Parse Stärke
                        strength = 1.0
                        if len(parts) > 3:
                            strength_part = parts[3].strip()
                            if strength_part.startswith('strength:'):
                                try:
                                    strength = float(strength_part[9:])
                                except ValueError:
                                    pass
                        
                        # Parse Preis
                        price = None
                        if len(parts) > 4:
                            price_part = parts[4].strip()
                            if price_part.startswith('price:'):
                                try:
                                    price = float(price_part[6:])
                                except ValueError:
                                    pass
                        
                        # Parse zusätzliche Informationen (Confidence, Type, etc.)
                        additional_info = {}
                        if len(parts) > 5:
                            additional = parts[5].strip()
                            if additional.startswith('additional:'):
                                # Parse key:value pairs
                                info_str = additional[11:]  # Remove 'additional:'
                                for pair in info_str.split('/'):
                                    if ':' in pair:
                                        key, value = pair.split(':', 1)
                                        additional_info[key] = value
                        
                        # Extrahiere Confidence
                        confidence = 0.5  # Default
                        if 'confidence' in additional_info:
                            try:
                                confidence = float(additional_info['confidence'])
                            except:
                                pass
                        
                        # Extrahiere Signal Type (für Order Book Bot)
                        signal_strength_type = additional_info.get('type', 'normal')
                        
                        signals.append({
                            'time': signal_time,
                            'bot': bot_name,
                            'signal': signal_type,
                            'strength': strength,
                            'price': price,
                            'confidence': confidence,
                            'signal_type': signal_strength_type,  # 'strong', 'weak', 'normal'
                            'additional': additional_info
                        })
                        
                    except Exception as e:
                        continue
            
            return signals
            
        except Exception as e:
            print(f"❌ Fehler beim Lesen der Signale: {e}")
            return []
    
    def get_current_bot_signals(self):
        """Holt aktuelle Signale aller 4 Bots"""
        recent_signals = self.read_recent_signals(window_minutes=3)
        
        # Gruppiere nach Bot
        bot_signals = defaultdict(list)
        for signal in recent_signals:
            bot_signals[signal['bot']].append(signal)
        
        # Finde die neuesten Signale für jeden Bot
        current_signals = {}
        for bot_name, signals in bot_signals.items():
            if signals:
                # Sortiere nach Zeit und nimm das neueste
                latest_signal = max(signals, key=lambda x: x['time'])
                current_signals[bot_name] = latest_signal
        
        return current_signals
    
    def calculate_4bot_consensus_score(self, signals):
        """Berechnet 4-Bot Konsens Score"""
        if len(signals) < 2:  # Mindestens 2 Bots müssen Signale haben
            return 0, None
        
        # Sammle Signale nach Typ
        buy_signals = [s for s in signals.values() if s['signal'] == 'buy']
        sell_signals = [s for s in signals.values() if s['signal'] == 'sell']
        
        # Prüfe Konsens
        if len(buy_signals) == 0 and len(sell_signals) == 0:
            return 0
        
        consensus_direction = 'buy' if len(buy_signals) > len(sell_signals) else 'sell'
        consensus_signals = buy_signals if consensus_direction == 'buy' else sell_signals
        
        if len(consensus_signals) < 2:  # Mindestens 2 Bots müssen übereinstimmen
            return 0, None
        
        # Base Score: Anzahl übereinstimmender Bots
        base_score = len(consensus_signals) * 2.0  # 2-8 Punkte möglich
        
        # Bot-spezifische Gewichtung
        bot_weights = {
            'smart_indicator': 1.0,
            'pattern_filter': 1.0,
            'order_book': 1.2,  # Order Book bekommt leicht höhere Gewichtung
            'stable_signal': 0.8   # Falls vorhanden
        }
        
        # Stärke-Konsens
        weighted_strength = 0
        total_weight = 0
        for signal in consensus_signals:
            weight = bot_weights.get(signal['bot'], 1.0)
            
            # Bonus für "strong" Order Book Signale
            if signal['bot'] == 'order_book' and signal.get('signal_type') == 'strong':
                weight *= 1.5
            
            weighted_strength += abs(signal['strength']) * weight
            total_weight += weight
        
        strength_score = (weighted_strength / total_weight) if total_weight > 0 else 0
        strength_score = min(3.0, strength_score)  # Max 3 Punkte
        
        # Confidence-Konsens
        avg_confidence = sum(s['confidence'] for s in consensus_signals) / len(consensus_signals)
        confidence_score = avg_confidence * 2.0  # Max 2 Punkte
        
        # Zeit-Nähe Score
        if len(consensus_signals) > 1:
            times = [s['time'] for s in consensus_signals]
            time_span = (max(times) - min(times)).total_seconds()
            time_score = max(0, 1 - (time_span / 180))  # 3 Minuten = optimal
        else:
            time_score = 1.0
        
        # Order Book Bonus
        orderbook_bonus = 0
        if any(s['bot'] == 'order_book' for s in consensus_signals):
            orderbook_signal = next(s for s in consensus_signals if s['bot'] == 'order_book')
            if orderbook_signal.get('signal_type') == 'strong':
                orderbook_bonus = 1.0  # Starker Order Book Bonus
            else:
                orderbook_bonus = 0.5  # Schwacher Order Book Bonus
        
        # Gesamt-Score
        total_score = base_score + strength_score + confidence_score + time_score + orderbook_bonus
        
        return min(10.0, total_score), {
            'direction': consensus_direction,
            'consensus_signals': consensus_signals,
            'base_score': base_score,
            'strength_score': strength_score,
            'confidence_score': confidence_score,
            'time_score': time_score,
            'orderbook_bonus': orderbook_bonus,
            'bot_count': len(consensus_signals)
        }
    
    def identify_master_setup_v3(self):
        """Identifiziert Master Setup mit 4-Bot Konsens"""
        try:
            # Hole aktuelle Bot-Signale
            current_signals = self.get_current_bot_signals()
            
            print(f"📊 Aktuelle Bot-Signale (4-Bot System):")
            for bot, signal in current_signals.items():
                signal_type_info = f" ({signal.get('signal_type', 'normal')})" if signal.get('signal_type') else ""
                print(f"  {bot}: {signal['signal'].upper()}{signal_type_info} (Stärke: {signal['strength']:.2f}, Confidence: {signal['confidence']:.2f})")
            
            if len(current_signals) < 2:
                print("  ⚠️ Mindestens 2 Bots müssen Signale haben")
                return None
            
            # Berechne 4-Bot Konsens Score
            result = self.calculate_4bot_consensus_score(current_signals)
            if result[1] is None:  # Kein gültiger Konsens
                return None
                
            consensus_score, details = result
            
            if consensus_score < MIN_SETUP_SCORE:
                print(f"  ⚠️ Konsens Score zu niedrig: {consensus_score:.2f} < {MIN_SETUP_SCORE}")
                return None
            
            # Prüfe minimale Stärke und Confidence
            consensus_signals = details['consensus_signals']
            min_strength = min(abs(s['strength']) for s in consensus_signals)
            avg_confidence = sum(s['confidence'] for s in consensus_signals) / len(consensus_signals)
            
            if min_strength < MIN_CONSENSUS_STRENGTH:
                print(f"  ⚠️ Minimale Signal-Stärke zu schwach: {min_strength:.2f}")
                return None
            
            if avg_confidence < MIN_CONSENSUS_CONFIDENCE:
                print(f"  ⚠️ Durchschnittliche Confidence zu schwach: {avg_confidence:.2f}")
                return None
            
            # Cooldown prüfen
            if self.last_setup_time and (datetime.now() - self.last_setup_time).total_seconds() < self.setup_cooldown:
                print("  ⚠️ Cooldown aktiv")
                return None
            
            # Master Setup erstellen
            representative_signal = consensus_signals[0]  # Nehme erstes Signal für Preis
            
            setup = {
                'timestamp': datetime.now(),
                'signal': details['direction'],
                'price': representative_signal['price'],
                'consensus_score': consensus_score,
                'consensus_details': details,
                'participating_bots': [s['bot'] for s in consensus_signals],
                'min_strength': min_strength,
                'avg_confidence': avg_confidence,
                'bot_count': len(consensus_signals)
            }
            
            self.last_setup_time = datetime.now()
            self.signal_history.append(setup)
            
            return setup
            
        except Exception as e:
            print(f"❌ Master Setup V3 Fehler: {e}")
            return None
    
    def log_master_setup_v3(self, setup):
        """Loggt Master Setup V3 für Backtesting"""
        try:
            with open('master_setups_v3.log', 'a') as f:
                timestamp = setup['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                bot_list = ','.join(setup['participating_bots'])
                details = setup['consensus_details']
                
                f.write(f"{timestamp} - master:4bot_consensus - signal:{setup['signal']} - strength:{setup['min_strength']:.2f} - price:{setup['price']:.4f} - additional:score:{setup['consensus_score']:.2f}/confidence:{setup['avg_confidence']:.2f}/bots:{bot_list}/bot_count:{setup['bot_count']}/base:{details['base_score']:.1f}/orderbook_bonus:{details['orderbook_bonus']:.1f}\n")
        except Exception as e:
            print(f"❌ Logging Fehler: {e}")
    
    def start_sub_bots(self):
        """Startet alle Sub-Bots automatisch"""
        bot_files = [
            'smart_indicator_bot.py',
            'pattern_filter_bot.py', 
            'order_book_bot.py',
            'breakout_bot.py'
        ]
        
        print("🚀 Starte alle Sub-Bots automatisch...")
        print("="*60)
        
        for bot_file in bot_files:
            if os.path.exists(bot_file):
                try:
                    # Starte Bot in separatem Prozess
                    if sys.platform.startswith('win'):
                        # Windows: Verwende start für neues Fenster
                        process = subprocess.Popen(
                            f'start cmd /k "python {bot_file}"',
                            shell=True,
                            creationflags=subprocess.CREATE_NEW_CONSOLE
                        )
                    else:
                        # Linux/Mac: Starte im Hintergrund
                        process = subprocess.Popen(
                            ['python', bot_file],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                    
                    self.sub_bot_processes.append({
                        'name': bot_file,
                        'process': process
                    })
                    
                    print(f"✅ {bot_file} gestartet")
                    time.sleep(2)  # Kurze Pause zwischen Starts
                    
                except Exception as e:
                    print(f"❌ Fehler beim Starten von {bot_file}: {e}")
            else:
                print(f"⚠️ {bot_file} nicht gefunden!")
        
        print("="*60)
        print(f"🎯 {len(self.sub_bot_processes)} Sub-Bots gestartet")
        print("⏰ Warte 10 Sekunden auf Bot-Initialisierung...\n")
        time.sleep(10)  # Warte auf Bot-Startup
        
        self.bots_started = True
    
    def stop_sub_bots(self):
        """Stoppt alle Sub-Bots beim Master Bot Exit"""
        print("\n🛑 Stoppe alle Sub-Bots...")
        
        for bot_info in self.sub_bot_processes:
            try:
                bot_info['process'].terminate()
                print(f"🛑 {bot_info['name']} gestoppt")
            except Exception as e:
                print(f"⚠️ Fehler beim Stoppen von {bot_info['name']}: {e}")
        
        print("✅ Alle Sub-Bots gestoppt")
    
    def check_bot_health(self):
        """Prüft ob alle Bots noch laufen"""
        if not self.bots_started:
            return True
            
        running_bots = 0
        for bot_info in self.sub_bot_processes:
            if bot_info['process'].poll() is None:  # Process is still running
                running_bots += 1
            else:
                print(f"⚠️ {bot_info['name']} ist gestoppt!")
        
        if running_bots < len(self.sub_bot_processes):
            print(f"⚠️ Nur {running_bots}/{len(self.sub_bot_processes)} Bots laufen noch")
            return False
        
        return True
    
    def run(self):
        """Haupt-Loop für Master Bot V3 mit automatischem Sub-Bot Start"""
        print("🎯 MASTER BOT V3 - ALL-IN-ONE TRADING SYSTEM")
        print("="*80)
        print("🚀 Startet automatisch alle Sub-Bots:")
        print("  📊 Smart Indicator Bot")
        print("  🔍 Pattern Filter Bot") 
        print("  📈 Order Book Bot")
        print("  🎯 Master Koordination")
        print("="*80)
        
        try:
            # Starte alle Sub-Bots automatisch
            self.start_sub_bots()
            
            print("🎯 MASTER BOT V3 - 4-Bot Konsens System aktiv!")
            print(f"📊 Koordiniert: Smart Indicator + Pattern Filter + Order Book")
            print(f"🎯 Minimale Konsens-Score: {MIN_SETUP_SCORE}")
            print(f"🎯 Minimale Konsens-Stärke: {MIN_CONSENSUS_STRENGTH}")
            print(f"🎯 Minimale Konsens-Confidence: {MIN_CONSENSUS_CONFIDENCE}")
            print(f"⏰ Cooldown: {self.setup_cooldown} Sekunden zwischen Setups")
            print(f"📈 Hold-Zeiträume: {', '.join(map(str, HOLD_PERIODS))} Minuten")
            print(f"⏰ Prüft alle {SLEEP_TIME} Sekunden auf neue 4-Bot Signale\n")
            
            # Haupt-Trading-Loop
            health_check_counter = 0
            while True:
                try:
                    # Alle 10 Zyklen: Bot Health Check
                    health_check_counter += 1
                    if health_check_counter % 10 == 0:
                        if not self.check_bot_health():
                            print("⚠️ Einige Bots sind gestoppt - Master läuft weiter...")
                    
                    setup = self.identify_master_setup_v3()
                    
                    if setup:
                        print(f"\n{'='*80}")
                        print(f"🎯 MASTER SETUP V3 - 4-BOT KONSENS!")
                        print(f"{'='*80}")
                        print(f"⏰ Zeit: {setup['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"💱 Symbol: {SYMBOL}")
                        print(f"💰 Preis: {setup['price']:.4f} USDT")
                        print(f"📈 Signal: {setup['signal'].upper()}")
                        print(f"⭐ Konsens-Score: {setup['consensus_score']:.2f}/10")
                        print(f"🤖 Teilnehmende Bots: {setup['bot_count']}/3")
                        print(f"💪 Min. Stärke: {setup['min_strength']:.2f}")
                        print(f"🎯 Ø Confidence: {setup['avg_confidence']:.1%}")
                        
                        # Konsens-Details
                        details = setup['consensus_details']
                        print(f"\n📊 KONSENS-BREAKDOWN:")
                        print(f"  🏗️ Base Score: {details['base_score']:.1f} ({details['bot_count']} Bots)")
                        print(f"  💪 Stärke Score: {details['strength_score']:.1f}")
                        print(f"  🎯 Confidence Score: {details['confidence_score']:.1f}")
                        print(f"  ⏰ Zeit Score: {details['time_score']:.1f}")
                        print(f"  📊 Order Book Bonus: {details['orderbook_bonus']:.1f}")
                        
                        # Beteiligte Bots
                        print(f"\n🤖 BETEILIGTE BOTS:")
                        for signal in details['consensus_signals']:
                            signal_type_info = f" ({signal.get('signal_type', 'normal')})" if signal.get('signal_type') else ""
                            print(f"  ✅ {signal['bot']}: {signal['signal'].upper()}{signal_type_info} | Stärke: {signal['strength']:.2f} | Confidence: {signal['confidence']:.1%}")
                        
                        print(f"\n⏰ Hold-Zeiträume: {', '.join(map(str, HOLD_PERIODS))} Minuten")
                        print(f"🎯 4-Bot Konsens Setup geloggt für Backtesting")
                        
                        # Logging
                        self.log_master_setup_v3(setup)
                        
                    else:
                        print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Kein 4-Bot Konsens gefunden")
                    
                    time.sleep(SLEEP_TIME)
                    
                except KeyboardInterrupt:
                    print("\n🛑 Master Bot V3 wird gestoppt...")
                    break
                except Exception as e:
                    print(f"❌ Trading Loop Fehler: {e}")
                    time.sleep(SLEEP_TIME)
            
        except KeyboardInterrupt:
            print("\n🛑 Shutdown initiiert...")
        except Exception as e:
            print(f"❌ Master Bot Startup Fehler: {e}")
        finally:
            # Cleanup: Stoppe alle Sub-Bots
            if self.bots_started:
                self.stop_sub_bots()
            print("👋 Master Bot V3 komplett gestoppt")

if __name__ == '__main__':
    master = MasterBotV3()
    master.run() 
