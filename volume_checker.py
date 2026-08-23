from datetime import datetime
import json
import os
import xml.etree.ElementTree as ET
import requests
import yfinance as yf

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

TICKERS = [
    'KO',
    'NFLX',
    'MC.PA',
    'NVO',
    'ACHR',
    'TSM',
    'OPEN',
    'NVDA',
    'IREN',
    'GOSS',
    'ASTS',
    'BSIN',
    'ONDS',
    'RKLB',
    'GOOGL',
    'SLNH',
    'RZLV',
    'LAES',
    'BTC-USD',
]

# Nombres más limpios para las búsquedas de noticias si el ticker no es intuitivo
NAMES = {'MC.PA': 'LVMH', 'BTC-USD': 'Bitcoin'}

SEEN_NEWS_FILE = 'seen_news.json'


# 1. Envía alertas de precios y volumen al TEMA 1 (Acciones cartera)
def send_alert_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {
      'chat_id': CHAT_ID,
      'text': message,
      'parse_mode': 'Markdown',
      'message_thread_id': 1,  # <--- Tema 1
  }
  requests.post(url, json=payload)


# 2. Envía noticias de todas las acciones al TEMA 3 (Noticias Cartera)
def send_news_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {
      'chat_id': CHAT_ID,
      'text': message,
      'parse_mode': 'Markdown',
      'message_thread_id': 3,  # <--- Tema 3
  }
  requests.post(url, json=payload)


def check_all_news():
  seen_news = []
  if os.path.exists(SEEN_NEWS_FILE):
    with open(SEEN_NEWS_FILE, 'r') as f:
      seen_news = json.load(f)

  for ticker in TICKERS:
    search_term = NAMES.get(ticker, ticker)
    try:
      url = f'https://news.google.com/rss/search?q={search_term}&hl=es&gl=ES&ceid=ES:es'
      response = requests.get(url, timeout=10)
      if response.status_code == 200:
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[
            :1
        ]  # Coge la noticia más reciente de cada activo
        for item in items:
          title_elem = item.find('title')
          link_elem = item.find('link')
          if title_elem is not None and link_elem is not None:
            title = title_elem.text
            link = link_elem.text
            news_id = f'{ticker}_{title}'

            if news_id not in seen_news:
              msg = f'📰 *Noticia ({search_term})*\n• {title}\n[Leer noticia]({link})'
              send_news_telegram(msg)
              seen_news.append(news_id)
    except Exception as e:
      print(f'Error buscando noticias de {ticker}: {e}')

  with open(SEEN_NEWS_FILE, 'w') as f:
    json.dump(seen_news[-60:], f)


def check_market():
  for ticker in TICKERS:
    try:
      stock = yf.Ticker(ticker)
      hist = stock.history(period='10d')

      if len(hist) < 2:
        continue

      today_data = hist.iloc[-1]
      prev_data = hist.iloc[-2]

      vol_today = today_data['Volume']
      close_today = today_data['Close']
      close_prev = prev_data['Close']

      avg_volume = hist['Volume'][:-1].mean() if len(hist) > 1 else vol_today
      price_change = ((close_today - close_prev) / close_prev) * 100

      is_big_price_move = abs(price_change) >= 1.5

      vol_label = ''
      if avg_volume > 0:
        if vol_today >= (avg_volume * 2.0):
          vol_label = '🚨 *¡Volumen doblado (200%+ vs media)!*'
        elif vol_today >= avg_volume:
          vol_label = '⚠️ *¡Volumen ha alcanzado el 100% de la media diaria!*'
        elif vol_today >= (avg_volume * 0.5):
          vol_label = (
              'ℹ️ *¡Volumen ya ha llegado a la mitad (50%) de la media!*'
          )

      is_volume_triggered = bool(vol_label)

      if is_big_price_move or is_volume_triggered:
        msg = (
            f'📊 *Alerta Mercado: {ticker}*\n'
            f'• *Precio:* ${close_today:.2f} ({price_change:+.2f}%)\n'
            f'• *Volumen hoy:* {vol_today:,.0f}\n'
            f'• *Volumen medio:* {avg_volume:,.0f}\n'
            f'{vol_label if vol_label else ""}\n'
            f'{"🚨 *¡Movimiento de precio del 1.5% o más!*" if is_big_price_move else ""}'
        )
        send_alert_telegram(msg)

    except Exception as e:
      print(f'Error procesando {ticker}: {e}')


if __name__ == '__main__':
  check_market()
  check_all_news()
