
import streamlit as st
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Crypto Swing-Scanner", page_icon="🪙", layout="wide")

st.title("🪙 Automatischer Krypto-Swing-Scanner")
st.markdown("Dieser High-Speed-Scanner prüft die Top-Kryptowährungen nach Marktkapitalisierung und filtert die besten Swing-Trading-Setups heraus.")

# --- DIE TOP KRYPTO-LISTE (FEST IM CODE HINTERLEGT) ---
# Das Format bei Yahoo Finance erfordert immer das Suffix "-USD"
KRYPTO_LISTE = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOT-USD", "AVAX-USD",
    "DOGE-USD", "SHIB-USD", "LINK-USD", "MATIC-USD", "TRX-USD", "UNI-USD", "LTC-USD", "NEAR-USD",
    "APT-USD", "ICP-USD", "ATOM-USD", "XLM-USD", "ETC-USD", "FIL-USD", "HBAR-USD", "KMD-USD",
    "INJ-USD", "RNDR-USD", "GRT-USD", "STX-USD", "OP-USD", "IMX-USD", "SUI-USD", "THETA",
    "FTM-USD", "RUNE-USD", "MKR", "LDO-USD", "TIA-USD", "GALA-USD", "VET-USD", "EGLD-USD",
    "AAVE-USD", "FLOW-USD", "MINA-USD", "ALGO-USD", "QNT-USD", "AXS-USD", "SAND-USD", "MANA-USD",
    "CHZ-USD", "WIF-USD", "PEPE-USD", "FLOKI-USD", "BONK-USD", "JUP-USD", "PYTH-USD", "DYM-USD",
    "ENS-USD", "PENDLE-USD", "FET-USD", "AGIX-USD", "OCEAN-USD", "JTO-USD", "STRK-USD", "ARB-USD",
    "SEI-USD", "RON-USD", "BEAM-USD", "GNS-USD", "WOO-USD", "GMT-USD", "JASMY-USD", "WLD-USD",
    "ANKR-USD", "ONE-USD", "ZIL-USD", "CKB-USD", "IOTX-USD", "ROSE-USD", "KAVA-USD", "LRC-USD",
    "CRV-USD", "COMP-USD", "SNX-USD", "YFI-USD", "SUSHI-USD", "1INCH-USD", "BAT-USD", "ENJ-USD",
    "ZEC-USD", "DASH-USD", "QTUM-USD", "OMG-USD", "ONT-USD", "IOTA-USD", "NEO-USD", "RVN-USD",
    "WAVES-USD", "KSM-USD", "CELO-USD", "SUPER-USD", "AUDIO-USD", "STORJ-USD", "MASK-USD", "API3-USD"
]

# Bereinigung der Liste
KRYPTO_LISTE = sorted(list(set(KRYPTO_LISTE)))

# --- SWING-ANALYSATOR FUNKTION FÜR KRYPTO ---
def analyze_single_crypto(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist.empty or len(hist) < 20:
            return None
        
        current_price = round(hist['Close'].iloc[-1], 4) if hist['Close'].iloc[-1] < 1 else round(hist['Close'].iloc[-1], 2)
        prev_close = hist['Close'].iloc[-2]
        perf_24h = ((current_price - prev_close) / prev_close) * 100
        
        hist['EMA20'] = hist['Close'].ewm(span=20, adjust=False).mean()
        hist['SMA50'] = hist['Close'].rolling(window=50).mean()
        last_close = hist['Close'].iloc[-1]
        last_ema20 = hist['EMA20'].iloc[-1]
        last_sma50 = hist['SMA50'].iloc[-1]
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        hist['RSI'] = 100 - (100 / (1 + rs))
        current_rsi = hist['RSI'].iloc[-1]
        
        exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
        exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
        hist['MACD'] = exp1 - exp2
        hist['Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
        last_macd = hist['MACD'].iloc[-1]
        last_sig = hist['Signal'].iloc[-1]
        
        avg_volume = hist['Volume'].mean()
        last_volume = hist['Volume'].iloc[-1]
        
        score = 0
        
        # 1. RSI Logik (Mittelzone = Perfekter Pullback im Bullenmarkt)
        if 40 <= current_rsi <= 55: score += 20
        elif 30 <= current_rsi < 40: score += 15
        elif 55 < current_rsi <= 68: score += 12
            
        # 2. Trend (Über EMAs)
        if last_close > last_ema20 and last_close > last_sma50: score += 20
        elif last_close > last_ema20: score += 10
            
        # 3. MACD Crossover
        if last_macd > last_sig: score += 20
            
        # 4. Krypto-Volumen-Ausbruch
        if last_volume > avg_volume: score += 15
        else: score += 7
            
        # 5. 24h Momentum (Krypto schlägt schnell aus, daher angepasste Volatilität)
        if perf_24h > 5.0: score += 25
        elif 0.0 <= perf_24h <= 5.0: score += 15
        elif -5.0 <= perf_24h < 0.0: score += 5
            
        # Krypto Risikomanagement (Standardmäßig etwas weiter gefasst, da Krypto mehr schwankt: -6% / +18%)
        stop_loss = round(current_price * 0.94, 4) if current_price < 1 else round(current_price * 0.94, 2)
        take_profit = round(current_price * 1.18, 4) if current_price < 1 else round(current_price * 1.18, 2)
        
        # Reines Kürzel ohne "-USD" für TradingView extrahieren (z.B. BTC-USD -> BTCUSDT)
        clean_symbol = ticker.replace("-USD", "")
        chart_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{clean_symbol}USDT"
        
        return {
            "Coin": clean_symbol,
            "Chart-Link": chart_url,
            "Kurs": current_price,
            "RSI": round(current_rsi, 1),
            "Perf. 24h": f"{round(perf_24h, 2)}%",
            "Swing-Score": score,
            "Signal": "STARKER KAUF" if score >= 75 else ("KAUFEN" if score >= 60 else ("BEOBACHTEN" if score >= 40 else "MEIDEN")),
            "Stop-Loss (-6%)": stop_loss,
            "Take-Profit (+18%)": take_profit
        }
    except:
        return None

# --- APP-OBERFLÄCHE ---
st.info(f"Der Krypto-Scanner ist geladen mit **{len(KRYPTO_LISTE)}** Liquiditäts-Coins (gepaart gegen USD).")

if st.button("🚀 Krypto-Markt-Scan jetzt starten"):
    fortschritts_balken = st.progress(0)
    status_text = st.empty()
    ergebnisse = []
    
    status_text.write("Scanne Krypto-Märkte mit maximaler Geschwindigkeit...")
    
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(analyze_single_crypto, t) for t in KRYPTO_LISTE]
        
        for i, future in enumerate(futures):
            res = future.result()
            if res: ergebnisse.append(res)
            fortschritts_balken.progress((i + 1) / len(KRYPTO_LISTE))
            
    status_text.write("✅ Krypto-Scan abgeschlossen!")
    
    if ergebnisse:
        df = pd.DataFrame(ergebnisse)
        # Sortieren nach den besten Scores
        df = df.sort_values(by="Swing-Score", ascending=False).reset_index(drop=True)
        
        # Zeige die 100 besten Krypto-Setups
        df = df.head(100)
        
        def color_signal(val):
            if val == "STARKER KAUF": return "background-color: #2ecc71; color: white; font-weight: bold;"
            elif val == "KAUFEN": return "background-color: #27ae60; color: white;"
            elif val == "BEOBACHTEN": return "background-color: #f39c12; color: white;"
            else: return "background-color: #e74c3c; color: white;"

        st.markdown("### 🏆 Die 100 besten Krypto-Setups (Beste Signale zuerst)")
        
        st.data_editor(
            df,
            column_config={
                "Chart-Link": st.column_config.LinkColumn(
                    "Live-Chart", 
                    help="Öffnet den Binance-Tageschart auf TradingView",
                    display_text="↗ Chart öffnen"
                )
            },
            disabled=True,
            use_container_width=True,
            height=600
        )
        st.balloons()
    else:
        st.error("Es konnten keine Krypto-Marktdaten geladen werden.")
