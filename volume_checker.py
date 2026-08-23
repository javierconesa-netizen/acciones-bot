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
    'OPEN': 'Opendoor Technologies',
}

FALLBACK_DIVIDENDS = {
    'KO': {'div_rate': 1.94, 'yield_pct': 3.10, 'ex_date': '15/09/2026'},
    'MC.PA': {'div_rate': 13.00, 'yield_pct': 2.05, 'ex_date': '28/10/2026'},
    'NOV.DE': {'div_rate': 3.20, 'yield_pct': 1.40, 'ex_date': '14/09/2026'},
    'TSM': {'div_rate': 1.60, 'yield_pct': 1.20, 'ex_date': '10/09/2026'},
    'NVDA': {'div_rate': 0.04, 'yield_pct': 0.03, 'ex_date': '05/09/2026'},
    'GOOGL': {'div_rate': 0.80, 'yield_pct': 0.45, 'ex_date': 'Próximamente'},
}

SEEN_NEWS_FILE = 'seen_news.json'
LAST_SUMMARY_FILE = 'last_summary.json'  # Control para el resumen diario
LAST_ALERT_FILE = 'last_alert_prices.json'  # Control para spam de precios
LAST_VOLUME_FILE = 'last_alert_volumes.json'  # Control para spam de volumen

session = requests.Session()
session.headers['User-Agent'] = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like'
    ' Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def send_telegram(message, thread_id=None):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
  if thread_id:
    payload['message_thread_id'] = thread_id
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f'Error enviando mensaje a Telegram: {e}')


# --- NOTICIAS ---
def check_all_news():
  seen_news = []
  if os.path.exists(SEEN_NEWS_FILE):
    with open(SEEN_NEWS_FILE, 'r') as f:
      seen_news = json.load(f)

  forbidden_words = [
      'tenis',
      'alcaraz',
      'williams',
      'us open',
      'partido',
      'torneo',
      'enfrentamiento',
      'deporte',
      'fútbol',
  ]

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

            title_lower = title.lower()
            if any(fw in title_lower for fw in forbidden_words):
              continue

            news_id = f'{ticker}_{title}'
            if news_id not in seen_news:
              msg = f'📰 *Noticia ({search_term})*\n• {title}\n[Leer noticia]({link})'
              send_telegram(msg, thread_id=3)
              seen_news.append(news_id)
    except Exception as e:
      print(f'Error buscando noticias de {ticker}: {e}')

  with open(SEEN_NEWS_FILE, 'w') as f:
    json.dump(seen_news[-60:], f)


# --- MERCADO ---
def check_market():
  tz_spain = pytz.timezone('Europe/Madrid')
  now_spain = datetime.now(tz_spain)
  today_str = now_spain.strftime('%Y-%m-%d')

  # Cargar memorias anti-spam
  last_alert_prices = {}
  if os.path.exists(LAST_ALERT_FILE):
    try:
      with open(LAST_ALERT_FILE, 'r') as f:
        last_alert_prices = json.load(f)
    except Exception:
      pass
  updated_alerts = last_alert_prices.copy()

  last_alert_volumes = {}
  if os.path.exists(LAST_VOLUME_FILE):
    try:
      with open(LAST_VOLUME_FILE, 'r') as f:
        last_alert_volumes = json.load(f)
    except Exception:
      pass
  updated_volumes = last_alert_volumes.copy()

  summary_data = []
  dividend_data = []
  earnings_data = []
  technical_data = []

  summary_lines = [
      '📊 *Resumen Cierre de Mercado* 📊',
      f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}\n',
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
      hist = stock.history(period='3mo')

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

      summary_data.append({
          'name': search_term,
          'price': close_today,
          'change': price_change,
          'currency': currency,
      })

      # Dividendos
      div_rate = None
      ex_date_str = 'Próximamente'
      yield_pct = 0.0

      if ticker in FALLBACK_DIVIDENDS:
        fb = FALLBACK_DIVIDENDS[ticker]
        div_rate = fb['div_rate']
        yield_pct = fb['yield_pct']
        ex_date_str = fb['ex_date']
      else:
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
              ex_date_str = divs.index[-1].strftime('%d/%m/%Y')
        except Exception:
          pass

      if div_rate and div_rate > 0:
        dividend_data.append({
            'name': search_term,
            'div_rate': div_rate,
            'yield_pct': yield_pct,
            'ex_date': ex_date_str,
            'currency': currency,
        })

      # Análisis Técnico (RSI)
      try:
        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        rsi_label = '🟠 Normal'
        if current_rsi > 70:
          rsi_label = '🔴 Sobrecompra (>70)'
        elif current_rsi < 30:
          rsi_label = '🟢 Sobreventa (<30)'

        technical_data.append({
            'name': search_term,
            'rsi': current_rsi,
            'rsi_label': rsi_label,
        })
      except Exception:
        pass

      # Earnings
      try:
        cal = stock.calendar
        edate_str = 'No programada'
        if cal is not None:
          if isinstance(cal, dict) and 'Earnings Date' in cal:
            edates = cal['Earnings Date']
            if edates:
              edate_str = str(edates[0])[:10]
          elif hasattr(cal, 'loc') and 'Earnings Date' in cal.index:
            edate_str = str(cal.loc['Earnings Date'].values[0])[:10]
        earnings_data.append({'name': search_term, 'date': edate_str})
      except Exception:
        earnings_data.append({'name': search_term, 'date': 'No disponible'})

      # --- ALERTAS EN TIEMPO REAL (Con filtros anti-spam de 1% precio y 25% volumen) ---
      is_big_price_move = abs(price_change) >= 1.5
      should_alert_price = False
      if is_big_price_move:
        if ticker not in last_alert_prices:
          should_alert_price = True
        else:
          last_price_alerted = last_alert_prices[ticker]
          diff_from_last = (
              abs(close_today - last_price_alerted) / last_price_alerted
          ) * 100
          if diff_from_last >= 1.0:
            should_alert_price = True

      should_alert_vol = False
      vol_label = ''
      if avg_volume > 0:
        is_vol_high = vol_today >= avg_volume
        if is_vol_high:
          if ticker not in last_alert_volumes:
            should_alert_vol = True
          else:
            last_vol_alerted = last_alert_volumes[ticker]
            # Salta si el volumen actual es un 25% mayor que en el último aviso
            if vol_today >= (last_vol_alerted * 1.25):
              should_alert_vol = True

      if should_alert_price or should_alert_vol:
        if should_alert_vol:
          if vol_today >= (avg_volume * 2.0):
            vol_label = '🚨 *¡Volumen doblado (200%+ vs media)!*'
          else:
            vol_label = '⚠️ *¡Volumen al 100% de la media!*'

        msg = (
            f'📊 *Alerta Mercado: {search_term}*\n'
            f'• *Precio:* {currency}{close_today:.2f} ({price_change:+.2f}%)\n'
            f'• *Volumen hoy:* {vol_today:,.0f}\n{vol_label}'
        )
        send_telegram(msg)

        if is_big_price_move and should_alert_price:
          updated_alerts[ticker] = close_today
        if should_alert_vol:
          updated_volumes[ticker] = vol_today

    except Exception as e:
      print(f'Error procesando {ticker}: {e}')

  # Guardar memorias
  with open(LAST_ALERT_FILE, 'w') as f:
    json.dump(updated_alerts, f)
  with open(LAST_VOLUME_FILE, 'w') as f:
    json.dump(updated_volumes, f)

  # --- RESUMEN DE CIERRE ---
  should_send_summary = False
  if now_spain.hour >= 22:
    last_summary_date = ''
    if os.path.exists(LAST_SUMMARY_FILE):
      with open(LAST_SUMMARY_FILE, 'r') as f:
        last_summary_date = json.load(f)

    if last_summary_date != today_str:
      should_send_summary = True

  if should_send_summary:
    if summary_data:
      summary_data.sort(key=lambda x: x['change'], reverse=True)
      for item in summary_data:
        emoji = '🟢' if item['change'] >= 0 else '🔴'
        summary_lines.append(
            f"{emoji} *{item['name']}*: {item['currency']}{item['price']:.2f}"
            f" (`{item['change']:+.2f}%`)"
        )
      send_telegram('\n'.join(summary_lines), thread_id=SUMMARY_THREAD_ID)

    if dividend_data:
      now_date = now_spain.date()
      valid_dividends = []
      for item in dividend_data:
        ex_str = item['ex_date']
        if ex_str == 'Próximamente':
          valid_dividends.append(item)
        else:
          try:
            d = datetime.strptime(ex_str, '%d/%m/%Y').date()
            if d >= now_date:
              item['parsed_date'] = d
              valid_dividends.append(item)
          except Exception:
            pass

      valid_dividends.sort(
          key=lambda x: (
              0 if 'parsed_date' in x else 1,
              x.get('parsed_date', datetime.max.date()),
          )
      )
      for item in valid_dividends:
        date_display = (
            item['parsed_date'].strftime('%d/%m/%Y')
            if 'parsed_date' in item
            else item['ex_date']
        )
        dividend_lines.append(
            f"💵 *{item['name']}* — `{date_display}` (`{item['yield_pct']:.2f}%`"
            f' anual | {item["currency"]}{item["div_rate"]:.2f})'
        )
      send_telegram('\n'.join(dividend_lines), thread_id=DIVIDENDS_THREAD_ID)

    if earnings_data:
      earnings_data.sort(
          key=lambda x: (
              0 if (x['date'] and x['date'][0].isdigit()) else 1,
              x['date'],
          )
      )
      for item in earnings_data:
        earnings_lines.append(f'• *{item["name"]}*: `{item["date"]}`')
      send_telegram('\n'.join(earnings_lines), thread_id=EARNINGS_THREAD_ID)

    if technical_data:
      technical_data.sort(key=lambda x: x['rsi'], reverse=True)
      for item in technical_data:
        technical_lines.append(
            f"• *{item['name']}* - RSI: `{item['rsi']:.1f}` ({item['rsi_label']})"
        )
      send_telegram('\n'.join(technical_lines), thread_id=TECHNICAL_THREAD_ID)

    try:
      fng_res = requests.get(
          'https://api.alternative.me/fng/?limit=1', timeout=10
      ).json()
      fng_val = int(fng_res['data'][0]['value'])
      fng_class_en = fng_res['data'][0]['value_classification']

      translations = {
          'Extreme Fear': 'Miedo Extremo 😱',
          'Fear': 'Miedo 😨',
          'Neutral': 'Neutral 😐',
          'Greed': 'Codicia 🟢',
          'Extreme Greed': 'Codicia Extrema 🚀',
      }
      fng_class_es = translations.get(fng_class_en, fng_class_en)

      fng_msg = (
          '📉 *Índice de Miedo y Codicia* 📉\n'
          f'📅 *Fecha:* {now_spain.strftime("%d/%m/%Y")}\n\n'
          f'• *Valor:* `{fng_val}/100`\n'
          f'• *Sentimiento:* *{fng_class_es}*'
      )
      send_telegram(fng_msg, thread_id=FEAR_GREED_THREAD_ID)
    except Exception as e:
      print(f'Error obteniendo Fear & Greed: {e}')

    with open(LAST_SUMMARY_FILE, 'w') as f:
      json.dump(today_str, f)


if __name__ == '__main__':
  check_market()
  check_all_news()
