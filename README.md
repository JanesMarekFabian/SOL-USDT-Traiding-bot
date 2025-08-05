# 🚀 Trading Bot System - Multi-Bot Konsens System

Ein fortschrittliches Trading Bot System mit 4 spezialisierten Bots und einem Master-Konsens-System für MEXC Futures Trading.

## 📋 Übersicht

Das System besteht aus 5 Hauptkomponenten:

### 🤖 Trading Bots
1. **Smart Indicator Bot** - Klassische technische Indikatoren (RSI, SMA, Bollinger Bands, MACD)
2. **Pattern Filter Bot** - Candlestick-Pattern Erkennung und Trend-Formationen
3. **Breakout Bot** - Support/Resistance Breakout Detection
4. **Order Book Bot** - Order Book Intelligence und Market Maker Aktivitäten

### 🎯 Master System
5. **Master Bot V3** - Koordiniert alle 4 Bots und erstellt Konsens-Signale

### 📊 Monitoring
6. **Market Data Monitor** - Live Marktdaten Überwachung (ohne Trading)

## 🛠️ Installation

### Voraussetzungen
- Python 3.8+
- MEXC API Zugang
- CCXT Library

### Setup
```bash
# Dependencies installieren
pip install ccxt numpy

# Environment Variables setzen
export MEXC_API_KEY="your_api_key"
export MEXC_SECRET="your_secret_key"
```

## 🚀 Verwendung

### 1. Master Bot (Empfohlen)
Startet alle Bots automatisch und erstellt Konsens-Signale:

```bash
python master_bot_v3.py
```

### 2. Einzelne Bots
Für spezifische Strategien:

```bash
# Smart Indicator Bot
python smart_indicator_bot.py

# Pattern Filter Bot  
python pattern_filter_bot.py

# Breakout Bot
python breakout_bot.py

# Order Book Bot
python order_book_bot.py

# Market Data Monitor
python market_data_monitor.py
```

## 📊 Bot Details

### Smart Indicator Bot
- **Strategie**: Klassische technische Indikatoren
- **Indikatoren**: RSI, SMA, Bollinger Bands, MACD, Volume
- **Risikomanagement**: Max 3% Tagesverlust, Position Size Control
- **Signale**: Weniger, aber qualitativere Signale

### Pattern Filter Bot
- **Strategie**: Candlestick-Pattern Erkennung
- **Patterns**: Doji, Hammer, Shooting Star, etc.
- **Features**: Support/Resistance, Trend-Formationen, Volume-Patterns
- **Zeitfenster**: 5min, 10min, 20min Hold-Zeiträume

### Breakout Bot
- **Strategie**: Support/Resistance Breakout Detection
- **Features**: Dynamische S/R Erkennung, Volume-Bestätigung
- **Schutz**: False Breakout Filterung, Retest-Erkennung

### Order Book Bot
- **Strategie**: Order Book Intelligence
- **Features**: Support/Resistance Walls, Order Book Imbalance
- **Analyse**: Liquidation Level Estimates, Market Maker Bias

### Master Bot V3
- **Strategie**: 4-Bot Konsens System
- **Features**: Strong/Weak Signal Classification, Consensus Scoring
- **Qualität**: Erhöhte Setup-Qualitäts-Anforderungen

## 📈 Signal System

### Signal Format
```
2024-01-15 14:30:25 - bot:smart_indicator - signal:buy - strength:7.5 - price:123.45 - additional:confidence:0.8/position_size:2.5%/rsi:35.2/sma_alignment:1
```

### Konsens-System
- **Minimum Consensus Strength**: 4.0/10
- **Minimum Confidence**: 65%
- **Setup Score**: 7.0/10
- **Cooldown**: 7.5 Minuten zwischen Setups

## 📁 Dateien

- `master_bot_v3.py` - Hauptkoordinator
- `smart_indicator_bot.py` - Technische Indikatoren
- `pattern_filter_bot.py` - Pattern-Erkennung
- `breakout_bot.py` - Breakout Detection
- `order_book_bot.py` - Order Book Intelligence
- `market_data_monitor.py` - Marktüberwachung
- `signals.log` - Signal-Historie
- `master_setups_v3.log` - Master-Setup Log

## ⚙️ Konfiguration

### Trading Parameter
```python
SYMBOL = 'SOL_USDT'  # Trading Pair
TIMEFRAME = '1m'      # Zeitrahmen
SLEEP_TIME = 30       # Update-Intervall (Sekunden)
```

### Risikomanagement
```python
MAX_DAILY_LOSS = 3.0      # Maximaler Tagesverlust (%)
MAX_POSITION_SIZE = 3.0    # Maximale Positionsgröße (%)
MIN_SIGNAL_STRENGTH = 5.0  # Minimale Signal-Stärke
MIN_CONFIDENCE = 0.6       # Minimale Confidence
```

## 🔧 Anpassung

### Neue Trading Pairs
Ändern Sie `SYMBOL` in allen Bot-Dateien:
```python
SYMBOL = 'BTC_USDT'  # oder andere Pairs
```

### Parameter Optimierung
Passen Sie die Schwellenwerte in den jeweiligen Bot-Dateien an:
```python
MIN_SIGNAL_STRENGTH = 6.0  # Strenger
MIN_CONFIDENCE = 0.7       # Höhere Confidence
```

## 📊 Monitoring

### Logs überwachen
```bash
# Signal-Log in Echtzeit
tail -f signals.log

# Master-Setup Log
tail -f master_setups_v3.log
```

### Performance Tracking
- Alle Signale werden in `signals.log` gespeichert
- Master-Setups in `master_setups_v3.log`
- Strukturierte Ausgabe mit Zeitstempel und Metriken

## ⚠️ Wichtige Hinweise

### Risikowarnung
- **Nur für Bildungszwecke**
- **Keine Finanzberatung**
- **Verluste möglich**
- **Testen Sie mit kleinen Beträgen**

### API Limits
- MEXC API Rate Limits beachten
- `enableRateLimit: True` aktiviert
- Sleep-Zeiten zwischen Requests

### Sicherheit
- API Keys sicher aufbewahren
- Environment Variables verwenden
- Keine Keys im Code speichern

## 🆘 Troubleshooting

### Häufige Probleme

**API Fehler**
```bash
# API Keys prüfen
echo $MEXC_API_KEY
echo $MEXC_SECRET
```

**Import Fehler**
```bash
# Dependencies installieren
pip install ccxt numpy
```

**Rate Limit Fehler**
- Sleep-Zeiten erhöhen
- API Limits prüfen

## 📞 Support

Bei Fragen oder Problemen:
1. Logs überprüfen
2. API Keys testen
3. Dependencies aktualisieren
4. Parameter anpassen

## 📄 Lizenz

Dieses Projekt ist für Bildungszwecke erstellt. Verwendung auf eigene Verantwortung.

---

**⚠️ Disclaimer**: Dieses System ist für Bildungszwecke erstellt. Trading mit Kryptowährungen ist hochriskant. Verluste sind möglich. Konsultieren Sie einen Finanzberater vor dem Trading. 


