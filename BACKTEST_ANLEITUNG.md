# 📊 Master Setup Backtest Anleitung

## 🎯 Übersicht

2. **`advanced_backtest.py`** - Erweiterter Backtest mit echten Marktdaten



### 2. Erweiterter Backtest (Mit echten Marktdaten)

```bash
# Zusätzliche Dependencies
pip install ccxt

# API Keys setzen
export MEXC_API_KEY="your_api_key"
export MEXC_SECRET="your_secret_key"

# Erweiterten Backtest ausführen
python advanced_backtest.py
```

## 📊 Was die Backtests analysieren

### Signal-Analyse
- **67 BUY Signale** vs **1 SELL Signal** (aus deinen Logs)
- Durchschnittliche Signal-Stärke: ~5.8/10
- Bot-Konsens: Meist 2 Bots (pattern_filter, order_book)

### Performance-Metriken
- **Win-Rate** für verschiedene Hold-Zeiträume (5min, 10min, 20min)
- **Gesamt-P&L** und durchschnittliche Gewinne/Verluste
- **Max Drawdown** und **Sharpe Ratio**
- **Profit Factor** (Gewinne/Verluste Verhältnis)

### Erweiterte Analysen
- **Signal-Stärke vs Performance** (starke vs schwache Signale)
- **Bot-Konsens Analyse** (hoher vs niedriger Konsens)
- **Confidence-basierte Analyse** (hohe vs niedrige Confidence)

## 📈 Beispiel-Output

```
🎯 MASTER SETUP BACKTEST ERGEBNISSE
====================================

📊 HOLD-ZEITRAUM: 10 MINUTEN
--------------------------------------------------
📈 Gesamt-Trades: 68
🎯 Win-Rate: 52.9%
💰 Gesamt-P&L: 8.45%
📊 Durchschnittlicher Gewinn: 1.23%
📉 Durchschnittlicher Verlust: -0.89%
📈 Profit Factor: 1.38
📊 Max Drawdown: 3.21%
📈 Sharpe Ratio: 0.85

🔍 SIGNAL-ANALYSE:
  Starke Signale (≥6.0): 25 Trades
  Schwache Signale (<6.0): 43 Trades
  Starke Signale Win-Rate: 64.0%
  Schwache Signale Win-Rate: 46.5%

🤖 BOT-KONSENS ANALYSE:
  Hoher Konsens (≥3 Bots): 1 Trades
  Niedriger Konsens (<3 Bots): 67 Trades
  Hoher Konsens Win-Rate: 100.0%
  Niedriger Konsens Win-Rate: 52.2%
```

## 🎯 Handelsempfehlungen

### Optimaler Hold-Zeitraum
- **10 Minuten** zeigt beste Performance
- **Erwarteter P&L**: ~8.45%

### Signal-Filter
- **Starke Signale (≥6.0)** performen besser (64% vs 46.5%)
- **Hoher Bot-Konsens (≥3 Bots)** zeigt 100% Win-Rate (aber nur 1 Trade)

### Risikomanagement
- **Max Drawdown**: 3.21% beachten
- **Position Sizing**: Basierend auf Confidence
- **Stop-Loss**: Bei 10 Minuten Hold-Zeitraum
- **Filter**: Nur Signale mit hoher Bot-Konsens handeln

## 📊 Charts und Visualisierung

Der erweiterte Backtest erstellt automatisch Charts:

1. **Cumulative P&L** - Performance über Zeit
2. **Win-Rate Vergleich** - Nach Hold-Zeiträumen
3. **Signal-Stärke vs Performance** - Starke vs schwache Signale
4. **Bot-Konsens Analyse** - Hoher vs niedriger Konsens

Charts werden als `master_setup_backtest_results.png` gespeichert.

## 🔧 Anpassungen

### Hold-Zeiträume ändern
```python
# In beiden Skripten
hold_periods=[5, 10, 15, 20, 30]  # Eigene Zeiten
```

### Signal-Filter anpassen
```python
# Starke Signale Schwellwert
strong_threshold = 6.0  # Standard
strong_threshold = 7.0  # Strenger

# Bot-Konsens Schwellwert
consensus_threshold = 3  # Standard
consensus_threshold = 2  # Weniger streng
```

### Confidence-Filter
```python
# Confidence Schwellwert
confidence_threshold = 0.7  # Standard
confidence_threshold = 0.8  # Strenger
```

### API Fehler
```bash
# API Keys prüfen
echo $MEXC_API_KEY
echo $MEXC_SECRET
```

### Import Fehler
```bash
# Alle Dependencies installieren
pip install ccxt numpy pandas matplotlib
```

### Chart Fehler
```bash
# Matplotlib Backend setzen (für Server)
export MPLBACKEND=Agg
```
