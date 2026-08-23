from datetime import datetime
import json
import os
import xml.etree.ElementTree as ET
import pandas as pd
import pytz
import requests
import yfinance as yf

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

# IDs de los temas en Telegram
SUMMARY_THREAD_ID = 137  # Tema: Precio de cierre
DIVIDENDS_THREAD_ID = 257  # Tema: Dividendos y ex-dividendos

TICKERS = [
    'KO',
    'NFLX',
    'MC.PA',
    'NOV.DE',
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

NAMES = {
    'MC.PA': 'LVMH',
    'BTC-USD': 'Bitcoin',
    'NOV.DE': 'Novo Nordisk',
}
SEEN_NEWS_FILE = 'seen_news.json'


# 1. Alertas individuales -> Chat general (Acciones cartera)
def send_alert_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {
      'chat_id': CHAT_ID,
      'text': message,
      'parse_mode': 'Markdown',
  }
  requests.post(url, json=payload)


# 2. Resumen ordenado de cierre -> Tema "Precio de cierre" (ID: 137)
def send_summary_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {
      'chat_id': CHAT_ID,
      'text': message,
      'parse_mode': 'Markdown',
      'message_thread_id': SUMMARY_THREAD_ID,
  }
  requests.post(url, json=payload)


# 3. Dividendos y ex-dividendos -> Tema "Dividendos y ex-dividendos" (ID: 257)
def send_dividends_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {
      'chat_id': CHAT_ID,
      'text': message,
      'parse_mode': 'Markdown',
      'message_thread_id': DIVIDENDS_THREAD_ID,
  }
  requests.post(url, json=payload)


# 4. Noticias -> Tema 3 (Noticias Cartera)
def send_news_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {
      'chat_id': CHAT_ID,
      'text': message,
      'parse_mode': 'Markdown',
      'message_thread_id': 3,
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
        items = root.findall('.//item')[:1]
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
  tz_spain = pytz.timezone('Europe/Madrid')
  now_spain = datetime.now(tz_spain)

  is_manual_run = os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
  is_closing_time = (
      now_spain.hour == 22 and now_spain.minute < 15
  ) or is_manual_run

  summary_data = []
  dividend_data = []

  summary_lines = [
      '📊 *Resumen Cierre de Mercado* 📊',
      f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}',
      f'🕒 *Hora:* {now_spain.strftime("%H:%M:%S")}\n',
  ]

  dividend_lines = [
      '💰 *Calendario de Dividendos (Ordenado por Yield)* 💰',
      f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}\n',
  ]

  for ticker in TICKERS:
    search_term = NAMES.get(ticker, ticker)
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

      currency = '€' if ticker in ['MC.PA', 'NOV.DE'] else '$'

      # --- OBTENCIÓN ROBUSTA DE DIVIDENDOS SIN CONFLICTOS DE ZONA HORARIA ---
      if is_closing_time:
        try:
          divs = stock.dividends
          if divs is not None and not divs.empty:
            
            # 1. Quitamos la zona horaria del índice de dividendos para poder compararlo
            if divs.index.tz is not None:
                divs.index = divs.index.tz_convert(None)
            
            # 2. Creamos la fecha de "hace un año" sin zona horaria
            one_year_ago = datetime.utcnow() - pd.DateOffset(years=1)
            
            # 3. Filtramos los dividendos de los últimos 365 días
            recent_divs = divs[divs.index >= one_year_ago]
            div_rate = recent_divs.sum()

            if div_rate > 0:
              yield_pct = (div_rate / close_today) * 100 if close_today > 0 else 0.0
              last_date = divs.index[-1]
              ex_date_str = last_date.strftime('%d/%m/%Y')

              dividend_data.append({
                  'name': search_term,
                  'div_rate': div_rate,
                  'yield_pct': yield_pct,
                  'ex_date': ex_date_str,
                  'currency': currency,
              })
        except Exception as div_err:
          print(f'Error procesando dividendo para {ticker}: {div_err}')

      # --- LÓGICA 1: Alertas individuales en tiempo real ---
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
            f'📊 *Alerta Mercado: {search_term}*\n'
            f'• *Precio:* {currency}{close_today:.2f} ({price_change:+.2f}%)\n'
            f'• *Volumen hoy:* {vol_today:,.0f}\n'
            f'• *Volumen medio:* {avg_volume:,.0f}\n'
            f'{vol_label if vol_label else ""}\n'
            f'{"🚨 *¡Movimiento de precio del 1.5% o más!*" if is_big_price_move else ""}'
        )
        send_alert_telegram(msg)

      # --- LÓGICA 2: Datos para el resumen de precios ---
      if is_closing_time:
        summary_data.append({
            'name': search_term,
            'price': close_today,
            'change': price_change,
            'currency': currency,
        })

    except Exception as e:
      print(f'Error procesando {ticker}: {e}')

  # Enviar resumen de precios al Tema 137
  if is_closing_time and summary_data:
    summary_data.sort(key=lambda x: x['change'], reverse=True)
    for item in summary_data:
      emoji = '🟢' if item['change'] >= 0 else '🔴'
      summary_lines.append(
          f"{emoji} *{item['name']}*: {item['currency']}{item['price']:.2f}"
          f" (`{item['change']:+.2f}%`)"
      )
    send_summary_telegram('\n'.join(summary_lines))

  # Enviar resumen de dividendos al Tema 257 (ordenado de mayor a menor yield %)
  if is_closing_time and dividend_data:
    dividend_data.sort(key=lambda x: x['yield_pct'], reverse=True)
    for item in dividend_data:
      dividend_lines.append(
          f"💵 *{item['name']}*: `{item['yield_pct']:.2f}%` anual"
          f" ({item['currency']}{item['div_rate']:.2f}) | Ex-div:"
          f" `{item['ex_date']}`"
      )
    send_dividends_telegram('\n'.join(dividend_lines))


if __name__ == '__main__':
  check_market()
  check_all_news()
