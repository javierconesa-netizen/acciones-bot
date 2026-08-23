import os
import requests
import yfinance as yf
import json
from datetime import datetime
import xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

TICKERS = [
    "KO", "NFLX", "MC.PA", "NVO", "ACHR", "TSM", "OPEN", "NVDA", 
    "IREN", "GOSS", "ASTS", "BSIN", "ONDS", "RKLB", "GOOGL", 
    "SLNH", "RZLV", "LAES", "BTC-USD"
]

SEEN_NEWS_FILE = 'seen_btc_news.json'

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def check_crypto_news():
    seen_news = []
    if os.path.exists(SEEN_NEWS_FILE):
        with open(SEEN_NEWS_FILE, 'r') as f:
            seen_news = json.load(f)
            
    try:
        url = "https://news.google.com/rss/search?q=Bitcoin+BTC&hl=es&gl=ES&ceid=ES:es"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')[:3]
            for item in items:
                title_elem = item.find('title')
                link_elem = item.find('link')
                if title_elem is not None and link_elem is not None:
                    title = title_elem.text
                    link = link_elem.text
                    if title not in seen_news:
                        msg = f"📰 *Noticia Bitcoin (BTC)*\n• {title}\n[Leer noticia]({link})"
                        send_telegram(msg)
                        seen_news.append(title)
                        
        with open(SEEN_NEWS_FILE, 'w') as f:
            json.dump(seen_news[-30:], f)
    except Exception as e:
        print(f"Error buscando noticias de BTC: {e}")

def check_market():
    for ticker in TICKERS:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="10d")
            
            if len(hist) < 2:
                continue
                
            today_data = hist.iloc[-1]
            prev_data = hist.iloc[-2]
            
            vol_today = today_data['Volume']
            close_today = today_data['Close']
            close_prev = prev_data['Close']
            
            avg_volume = hist['Volume'][:-1].mean() if len(hist) > 1 else vol_today
            price_change = ((close_today - close_prev) / close_prev) * 100
            
            # Condiciones de precio y volumen escalonadas
            is_big_price_move = abs(price_change) >= 1.5
            
            vol_label = ""
            if avg_volume > 0:
                if vol_today >= (avg_volume * 2.0):
                    vol_label = "🚨 *¡Volumen doblado (200%+ vs media)!*"
                elif vol_today >= avg_volume:
                    vol_label = "⚠️ *¡Volumen ha alcanzado el 100% de la media diaria!*"
                elif vol_today >= (avg_volume * 0.5):
                    vol_label = "ℹ️ *¡Volumen ya ha llegado a la mitad (50%) de la media!*"

            is_volume_triggered = bool(vol_label)
            
            if is_big_price_move or is_volume_triggered:
                msg = (
                    f"📊 *Alerta Mercado: {ticker}*\n"
                    f"• *Precio:* ${close_today:.2f} ({price_change:+.2f}%)\n"
                    f"• *Volumen hoy:* {vol_today:,.0f}\n"
                    f"• *Volumen medio:* {avg_volume:,.0f}\n"
                    f"{vol_label if vol_label else ''}\n"
                    f"{'🚨 *¡Movimiento de precio del 1.5% o más!*' if is_big_price_move else ''}"
                )
                send_telegram(msg)
                
        except Exception as e:
            print(f"Error procesando {ticker}: {e}")

if __name__ == "__main__":
    check_market()
    check_crypto_news()
