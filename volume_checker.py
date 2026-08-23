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
    "IREN", "GOSS", "ASTS", "USEG", "ONDS", "RKLB", "GOOGL", 
    "SLNH", "RZLV", "LAES", "BTC-USD"
]

ALERT_FILE = 'last_market_alerts.json'
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
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    alerts_sent = {}
    if os.path.exists(ALERT_FILE):
        with open(ALERT_FILE, 'r') as f:
            alerts_sent = json.load(f)
            
    if today_str not in alerts_sent:
        alerts_sent[today_str] = []

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
            
            is_unusual_volume = vol_today > (avg_volume * 2) if avg_volume > 0 else False
            is_big_price_move = abs(price_change) > 5.0
            
            identifier = f"{ticker}_{today_str}"
            
            if (is_unusual_volume or is_big_price_move) and identifier not in alerts_sent[today_str]:
                msg = (
                    f"📊 *Alerta Mercado: {ticker}*\n"
                    f"• *Precio:* ${close_today:.2f} ({price_change:+.2f}%)\n"
                    f"• *Volumen hoy:* {vol_today:,.0f}\n"
                    f"• *Volumen medio:* {avg_volume:,.0f}\n"
                    f"{'🚨 *¡Movimiento o volumen inusual!*' if is_unusual_volume or is_big_price_move else ''}"
                )
                send_telegram(msg)
                alerts_sent[today_str].append(identifier)
                
        except Exception as e:
            print(f"Error procesando {ticker}: {e}")
            
    with open(ALERT_FILE, 'w') as f:
        json.dump(alerts_sent, f)

if __name__ == "__main__":
    check_market()
    check_crypto_news()
