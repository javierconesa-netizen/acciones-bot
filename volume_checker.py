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
EARNINGS_THREAD_ID = 419  # Tema: Resultados (earnings)
FEAR_GREED_THREAD_ID = 420  # Tema: Índice de Miedo
TECHNICAL_THREAD_ID = 421  # Tema: Sobrecompra sobreventa y medias

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

# Respaldo de seguridad para dividendos
FALLBACK_DIVIDENDS = {
    'KO': {'div_rate': 1.94, 'yield_pct': 3.10, 'ex_date': 'Próximamente'},
    'MC.PA': {'div_rate': 13.00, 'yield_pct': 2.05, 'ex_date': 'Próximamente'},
    'NOV.DE': {'div_rate': 3.20, 'yield_pct': 1.40, 'ex_date': 'Próximamente'},
    'TSM': {'div_rate': 1.60, 'yield_pct': 1.20, 'ex_date': 'Próximamente'},
    'NVDA': {'div_rate': 0.04, 'yield_pct': 0.03, 'ex_date': 'Próximamente'},
    'GOOGL': {'div_rate': 0.80, 'yield_pct': 0.45, 'ex_date': 'Próximamente'},
}

SEEN_NEWS_FILE = 'seen_news.json'

# Sesión personalizada para evitar bloqueos
session = requests.Session()
session.headers['User-Agent'] = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like'
    ' Gecko) Chrome/120.0.0.0 Safari/537.36'
)


# --- FUNCIONES DE ENVÍO A TELEGRAM ---
def send_alert_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  requests.post(
      url,
      json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'},
  )


def send_summary_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  requests.post(
      url,
      json={
          'chat_id': CHAT_ID,
          'text': message,
          'parse_mode': 'Markdown',
          'message_thread_id': SUMMARY_THREAD_ID,
      },
  )


def send_dividends_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  requests.post(
      url,
      json={
          'chat_id': CHAT_ID,
          'text': message,
          'parse_mode': 'Markdown',
          'message_thread_id': DIVIDENDS_THREAD_ID,
      },
  )


def send_news_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  requests.post(
      url,
      json={
          'chat_id': CHAT_ID,
          'text': message,
          'parse_mode': 'Markdown',
          'message_thread_id': 3,
      },
  )


def send_earnings_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  requests.post(
      url,
      json={
          'chat_id': CHAT_ID,
          'text': message,
          'parse_mode': 'Markdown',
          'message_thread_id': EARNINGS_THREAD_ID,
      },
  )


def send_fear_greed_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  requests.post(
      url,
      json={
          'chat_id': CHAT_ID,
          'text': message,
          'parse_mode': 'Markdown',
          'message_thread_id': FEAR_GREED_THREAD_ID,
      },
  )


def send_technical_telegram(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  requests.post(
      url,
      json={
          'chat_id': CHAT_ID,
          'text': message,
          'parse_mode': 'Markdown',
          'message_thread_id': TECHNICAL_THREAD_ID,
      },
  )


# --- NOTICIAS ---
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


# --- MERCADO Y NUEVAS FUNCIONALIDADES ---
def check_market():
  tz_spain = pytz.timezone('Europe/Madrid')
  now_spain = datetime.now(tz_spain)

  is_manual_run = os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
  is_closing_time = (
      now_spain.hour == 22 and now_spain.minute < 15
  ) or is_manual_run

  summary_data = []
  dividend_data = []
  earnings_data = []
  technical_data = []

  summary_lines = [
      '📊 *Resumen Cierre de Mercado* 📊',
      f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}',
      f'🕒 *Hora:* {now_spain.strftime("%H:%M:%S")}\n',
  ]

  dividend_lines = [
      '💰 *Calendario de Dividendos* 💰',
      f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}\n',
  ]

  earnings_lines = [
      '📅 *Próximos Resultados (Earnings)* 📅',
      f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}\n',
  ]

  technical_lines = [
      '📈 *Análisis Técnico (RSI y Medias)* 📈',
      f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}\n',
  ]

  for ticker in TICKERS:
    search_term = NAMES.get(ticker, ticker)
    try:
      stock = yf.Ticker(ticker, session=session)
      hist = stock.history(period='3mo')  # Ampliado para cálculos técnicos

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

      if is_closing_time:
        # --- 1. DIVIDENDOS ---
        div_rate = None
        ex_date_str = 'No disponible'
        yield_pct = 0.0

        try:
          divs = stock.dividends
          if divs is not None and not divs.empty:
            if divs.index.tz is not None:
              divs.index = divs.index.tz_localize(None)
            one_year_ago = datetime.utcnow() - pd.DateOffset(years=1)
            recent_divs = divs[divs.index >= one_year_ago]
            div_rate = recent_divs.sum()

            if div_rate > 0:
              yield_pct = (
                  (div_rate / close_today) * 100 if close_today > 0 else 0.0
              )
              last_date = divs.index[-1]
              ex_date_str = last_date.strftime('%d/%m/%Y')
        except Exception:
          pass

        if (not div_rate or div_rate == 0) and ticker in FALLBACK_DIVIDENDS:
          fb = FALLBACK_DIVIDENDS[ticker]
          div_rate = fb['div_rate']
          yield_pct = fb['yield_pct']
          ex_date_str = fb['ex_date']

        if div_rate and div_rate > 0:
          dividend_data.append({
              'name': search_term,
              'div_rate': div_rate,
              'yield_pct': yield_pct,
              'ex_date': ex_date_str,
              'currency': currency,
          })

        # --- 2. TÉCNICO (RSI Y MEDIAS) ---
        try:
          delta = hist['Close'].diff()
          gain = delta.where(delta > 0, 0.0)
          loss = -delta.where(delta < 0, 0.0)
          avg_gain = gain.rolling(window=14).mean()
          avg_loss = loss.rolling(window=14).mean()
          rs = avg_gain / avg_loss
          rsi = 100 - (100 / (1 + rs))
          current_rsi = rsi.iloc[-1]

          sma_50 = (
              hist['Close'].rolling(window=50).mean().iloc[-1]
              if len(hist) >= 50
              else None
          )

          rsi_label = '🟢 Normal'
          if current_rsi > 70:
            rsi_label = '🔴 Sobrecompra (>70)'
          elif current_rsi < 30:
            rsi_label = '🟢 Sobreventa (<30)'

          technical_data.append({
              'name': search_term,
              'rsi': current_rsi,
              'rsi_label': rsi_label,
              'price': close_today,
              'currency': currency,
          })
        except Exception:
          pass

        # --- 3. EARNINGS (RESULTADOS) ---
        try:
          cal = stock.calendar
          edate_str = 'Próximamente'
          if cal is not None:
            if isinstance(cal, dict) and 'Earnings Date' in cal:
              edates = cal['Earnings Date']
              if edates:
                edate_str = str(edates[0])[:10]
            elif hasattr(cal, 'loc') and 'Earnings Date' in cal.index:
              edate_str = str(cal.loc['Earnings Date'].values[0])[:10]

          earnings_data.append({'name': search_term, 'date': edate_str})
        except Exception:
          pass

      # --- ALERTAS EN TIEMPO REAL ---
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

      if is_big_price_move or bool(vol_label):
        msg = (
            f'📊 *Alerta Mercado: {search_term}*\n'
            f'• *Precio:* {currency}{close_today:.2f} ({price_change:+.2f}%)\n'
            f'• *Volumen hoy:* {vol_today:,.0f}\n'
            f'• *Volumen medio:* {avg_volume:,.0f}\n'
            f'{vol_label if vol_label else ""}\n'
            f'{"🚨 *¡Movimiento de precio del 1.5% o más!*" if is_big_price_move else ""}'
        )
        send_alert_telegram(msg)

      if is_closing_time:
        summary_data.append({
            'name': search_term,
            'price': close_today,
            'change': price_change,
            'currency': currency,
        })

    except Exception as e:
      print(f'Error procesando {ticker}: {e}')

  # --- ENVÍOS FINALES A CADA TEMA ---
  if is_closing_time:
    # 1. Resumen de Cierre (ID: 137)
    if summary_data:
      summary_data.sort(key=lambda x: x['change'], reverse=True)
      for item in summary_data:
        emoji = '🟢' if item['change'] >= 0 else '🔴'
        summary_lines.append(
            f"{emoji} *{item['name']}*: {item['currency']}{item['price']:.2f}"
            f" (`{item['change']:+.2f}%`)"
        )
      send_summary_telegram('\n'.join(summary_lines))

    # 2. Dividendos (ID: 257)
    if dividend_data:
      dividend_data.sort(key=lambda x: x['yield_pct'], reverse=True)
      for item in dividend_data:
        dividend_lines.append(
            f"💵 *{item['name']}*: `{item['yield_pct']:.2f}%` anual"
            f" ({item['currency']}{item['div_rate']:.2f}) | Ex-div:"
            f" `{item['ex_date']}`"
        )
      send_dividends_telegram('\n'.join(dividend_lines))

    # 3. Earnings (ID: 419)
    if earnings_data:
      for item in earnings_data:
        earnings_lines.append(f'• *{item["name"]}*: `{item["date"]}`')
      send_earnings_telegram('\n'.join(earnings_lines))

    # 4. Índice de Miedo / Fear & Greed (ID: 420)
    try:
      fng_res = requests.get(
          'https://api.alternative.me/fng/?limit=1', timeout=10
      ).json()
      fng_val = fng_res['data'][0]['value']
      fng_class = fng_res['data'][0]['value_classification']
      fng_msg = (
          '📉 *Índice de Miedo y Codicia (Crypto/Mercado)* 📉\n'
          f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}\n\n'
          f'• *Valor:* `{fng_val}/100`\n'
          f'• *Sentimiento:* *{fng_class}*'
      )
      send_fear_greed_telegram(fng_msg)
    except Exception as e:
      print(f'Error obteniendo Fear & Greed: {e}')

    # 5. Análisis Técnico - RSI y Medias (ID: 421)
    if technical_data:
      for item in technical_data:
        technical_lines.append(
            f"• *{item['name']}*: RSI `{item['rsi']:.1f}` ({item['rsi_label']})"
        )
      send_technical_telegram('\n'.join(technical_lines))


if __name__ == '__main__':
  check_market()
  check_all_news()
