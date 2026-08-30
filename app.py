import sys
import os
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import pandas as pd
import streamlit as st

packages_dir = "/tmp/pip_packages"
os.makedirs(packages_dir, exist_ok=True)
if packages_dir not in sys.path:
    sys.path.insert(0, packages_dir)

try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "yfinance", "lxml", "beautifulsoup4", "multitasking", "websockets<17", 
        "--target", packages_dir
    ])
    import yfinance as yf

st.set_page_config(
    page_title='Panel Financiero Profesional', page_icon='💎', layout='wide'
)

st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e222d 0%, #161b22 100%);
        border: 1px solid #30363d;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-bottom: 15px;
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    h1, h2, h3 {
        color: #f0f6fc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 8px 8px 0px 0px;
        color: #8b949e;
        padding: 10px 20px;
        font-weight: 600;
        border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important;
        color: white !important;
        border-color: #2ea043 !important;
    }
    .news-card {
        background-color: #161b22;
        border-left: 4px solid #238636;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
        border-top: 1px solid #30363d;
        border-right: 1px solid #30363d;
        border-bottom: 1px solid #30363d;
    }
    .ticker-badge {
        background: #21262d;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 6px 2px;
        text-align: center;
        font-weight: bold;
        color: #58a6ff;
        font-size: 11px;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

TICKERS = [
    'KO', 'NFLX', 'MC.PA', 'NOV.DE', 'ACHR', 'TSM', 'OPEN', 
    'NVDA', 'IREN', 'ASTS', 'ONDS', 'RKLB', 'GOOGL', 'SLNH', 
    'RZLV', 'LAES', 'BTC-USD'
]

TRACKING_TICKERS = ['GOSS', 'BSIN']

NAMES = {
    'KO': 'Coca-Cola',
    'MC.PA': 'LVMH',
    'BTC-USD': 'Bitcoin',
    'NOV.DE': 'Novo Nordisk',
    'OPEN': 'Opendoor Technologies',
    'NFLX': 'Netflix',
    'NVDA': 'NVIDIA',
    'TSM': 'TSMC',
    'GOOGL': 'Alphabet (Google)',
    'ACHR': 'Archer Aviation',
    'IREN': 'Iris Energy',
    'ASTS': 'AST SpaceMobile',
    'ONDS': 'Ondas Holdings',
    'RKLB': 'Rocket Lab',
    'SLNH': 'Silver牛 Mining',
    'RZLV': 'Rezolve AI',
    'LAES': 'Sealsq / LAES',
    'GOSS': 'Gossamer Bio',
    'BSIN': 'Black Spade Acquisition'
}

FALLBACK_DIVIDENDS = {
    'KO': {'div_rate': 1.94, 'yield_pct': 3.10, 'ex_date': '15/09/2026'},
    'MC.PA': {'div_rate': 13.00, 'yield_pct': 2.05, 'ex_date': '28/10/2026'},
    'NOV.DE': {'div_rate': 3.20, 'yield_pct': 1.40, 'ex_date': '14/09/2026'},
    'TSM': {'div_rate': 1.60, 'yield_pct': 1.20, 'ex_date': '10/09/2026'},
    'NVDA': {'div_rate': 0.04, 'yield_pct': 0.03, 'ex_date': '05/09/2026'},
    'GOOGL': {'div_rate': 0.80, 'yield_pct': 0.45, 'ex_date': 'Próximamente'},
}

@st.cache_data(ttl=300)
def get_comprehensive_market_data(tickers_list):
  data = []
  for ticker in tickers_list:
    search_term = NAMES.get(ticker, ticker)
    try:
      stock = yf.Ticker(ticker)
      hist = stock.history(period='3mo')
      if len(hist) >= 2:
        today_data = hist.iloc[-1]
        prev_data = hist.iloc[-2]

        close_today = today_data['Close']
        close_prev = prev_data['Close']
        vol_today = today_data['Volume']
        avg_volume = hist['Volume'][:-1].mean() if len(hist) > 1 else vol_today

        price_change_abs = close_today - close_prev
        price_change_pct = (price_change_abs / close_prev) * 100
        currency = '€' if ticker in ['MC.PA', 'NOV.DE'] else '$'
        vol_ratio = (vol_today / avg_volume) * 100 if avg_volume > 0 else 0.0

        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50.0

        rsi_label = 'Normal'
        if current_rsi > 70:
          rsi_label = '🔴 Sobrecompra (>70)'
        elif current_rsi < 30:
          rsi_label = '🟢 Sobreventa (<30)'
        else:
          rsi_label = '⚪ Neutral'

        div_rate = 0.0
        yield_pct = 0.0
        ex_date_str = 'Próximamente'
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
                yield_pct = (div_rate / close_today) * 100 if close_today > 0 else 0.0
                ex_date_str = divs.index[-1].strftime('%d/%m/%Y')
          except Exception:
            pass

        edate_str = 'No programada'
        try:
          cal = stock.calendar
          if cal is not None:
            if isinstance(cal, dict) and 'Earnings Date' in cal:
              edates = cal['Earnings Date']
              if edates:
                edate_str = str(edates[0])[:10]
            elif hasattr(cal, 'loc') and 'Earnings Date' in cal.index:
              edate_str = str(cal.loc['Earnings Date'].values[0])[:10]
        except Exception:
          pass

        data.append({
            'Ticker': ticker,
            'Nombre': search_term,
            'Precio': close_today,
            'Moneda': currency,
            'Cambio (%)': price_change_pct,
            'Cambio Abs': price_change_abs,
            'Volumen Hoy': vol_today,
            'Volumen vs Media (%)': vol_ratio,
            'RSI': current_rsi,
            'RSI_Label': rsi_label,
            'Div_Rate': div_rate,
            'Yield_Pct': yield_pct,
            'Ex_Date': ex_date_str,
            'Earnings': edate_str,
        })
    except Exception as e:
      print(f'Error procesando {ticker}: {e}')
  return pd.DataFrame(data)

@st.cache_data(ttl=600)
def fetch_google_news(tickers_list):
    forbidden_words = [
        'tenis', 'alcaraz', 'williams', 'us open', 'partido', 'torneo',
        'enfrentamiento', 'deporte', 'fútbol', 'boxeo', 'muay thai',
        'combate', 'ufc', 'mma', 'ejercicios', 'entrenamiento', 'método ko',
    ]
    news_items = []
    for ticker in tickers_list:
        search_term = NAMES.get(ticker, ticker)
        try:
            url = f'https://news.google.com/rss/search?q={search_term}&hl=es&gl=ES&ceid=ES:es'
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')[:2]
                for item in items:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_date_elem = item.find('pubDate')
                    if title_elem is not None and link_elem is not None:
                        title = title_elem.text
                        link = link_elem.text
                        pub_date = pub_date_elem.text if pub_date_elem is not None else ''

                        title_lower = title.lower()
                        if any(fw in title_lower for fw in forbidden_words):
                            continue

                        news_items.append({
                            'Ticker': ticker,
                            'Activo': search_term,
                            'Titulo': title,
                            'Enlace': link,
                            'Fecha': pub_date
                        })
        except Exception as e:
            print(f'Error buscando noticias de {ticker}: {e}')
    return news_items

st.title('💎 Terminal de Inversión y Seguimiento Financiero')
st.markdown(f'<p style="color: #8b949e; font-size: 15px;">🚀 Sincronización en tiempo real — Actualizado a fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>', unsafe_allow_html=True)

with st.spinner('Actualizando mercados y descargando perfiles corporativos...'):
  df_main = get_comprehensive_market_data(TICKERS)
  df_track = get_comprehensive_market_data(TRACKING_TICKERS)
  all_news = fetch_google_news(TICKERS + TRACKING_TICKERS)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    '🚀 Cartera Principal',
    '🔍 Cartera Seguimiento',
    '📈 Análisis Técnico & RSI',
    '💰 Dividendos & Earnings',
    '📰 Noticias RSS',
    '📉 Gráficos Avanzados',
])

with tab1:
  st.subheader('🚀 Cartera Principal')
  if not df_main.empty:
    df_main_sorted = df_main.sort_values(by='Cambio (%)', ascending=False)
    
    col1, col2, col3 = st.columns(3)
    best_asset = df_main_sorted.iloc[0]
    worst_asset = df_main_sorted.iloc[-1]
    
    with col1:
        st.markdown(f'<div class="metric-card"><h4>📊 Activos Totales</h4><h2>{len(df_main)}</h2></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h4>🚀 Mayor Subida</h4><h2>{best_asset["Nombre"]} <span style="color: #238636; font-size: 18px;">({best_asset["Cambio (%)"]:+.2f}%)</span></h2></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><h4>🔻 Mayor Bajada</h4><h2>{worst_asset["Nombre"]} <span style="color: #da3633; font-size: 18px;">({worst_asset["Cambio (%)"]:+.2f}%)</span></h2></div>', unsafe_allow_html=True)

    st.markdown('---')
    
    for index, row in df_main_sorted.iterrows():
        color_change = "#238636" if row['Cambio (%)'] >= 0 else "#da3633"
        sign = "+" if row['Cambio (%)'] >= 0 else ""
        
        c1, c2 = st.columns([1.5, 1.5])
        with c1:
            st.markdown(f"""
                <div style="line-height: 1.3;">
                    <span style="font-size: 15px; font-weight: bold; color: #f0f6fc;">{row['Nombre']}</span><br>
                    <span style="color: #8b949e; font-size: 12px;">🕒 {datetime.now().strftime("%d/%m")} | {row['Ticker']}</span>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div style="text-align: right; line-height: 1.3;">
                    <span style="font-size: 16px; font-weight: bold; color: #f0f6fc;">{row['Moneda']}{row['Precio']:.3f}</span><br>
                    <span style="color: {color_change}; font-size: 13px; font-weight: bold;">{sign}{row['Cambio Abs']:.3f} ({sign}{row['Cambio (%)']:.2f}%)</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("<hr style='margin: 8px 0px; border-color: #21262d;'>", unsafe_allow_html=True)

with tab2:
  st.subheader('🔍 Cartera de Seguimiento (Radar)')
  if not df_track.empty:
    df_track_sorted = df_track.sort_values(by='Cambio (%)', ascending=False)
    for index, row in df_track_sorted.iterrows():
        color_change = "#238636" if row['Cambio (%)'] >= 0 else "#da3633"
        sign = "+" if row['Cambio (%)'] >= 0 else ""
        
        c1, c2 = st.columns([1.5, 1.5])
        with c1:
            st.markdown(f"""
                <div style="line-height: 1.3;">
                    <span style="font-size: 15px; font-weight: bold; color: #f0f6fc;">{row['Nombre']}</span><br>
                    <span style="color: #8b949e; font-size: 12px;">🕒 {datetime.now().strftime("%d/%m")} | {row['Ticker']}</span>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div style="text-align: right; line-height: 1.3;">
                    <span style="font-size: 16px; font-weight: bold; color: #f0f6fc;">{row['Moneda']}{row['Precio']:.3f}</span><br>
                    <span style="color: {color_change}; font-size: 13px; font-weight: bold;">{sign}{row['Cambio Abs']:.3f} ({sign}{row['Cambio (%)']:.2f}%)</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("<hr style='margin: 8px 0px; border-color: #21262d;'>", unsafe_allow_html=True)

with tab3:
  st.subheader('📈 Análisis Técnico (Indicador RSI 14 Periodos)')
  if not df_main.empty:
    df_rsi = df_main[['Ticker', 'Nombre', 'RSI', 'RSI_Label']].sort_values(by='RSI', ascending=False)
    for index, row in df_rsi.iterrows():
        c1, c2, c3, c4 = st.columns([0.6, 2.5, 1.5, 2.4])
        with c1:
            st.markdown(f'<div class="ticker-badge">{row["Ticker"]}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f"**{row['Nombre']}**")
        with c3:
            st.markdown(f"RSI: **{row['RSI']:.1f}**")
        with c4:
            st.markdown(f"**{row['RSI_Label']}**")
        st.markdown("<hr style='margin: 5px 0px; border-color: #21262d;'>", unsafe_allow_html=True)

with tab4:
  st.subheader('💰 Dividendos y Próximos Resultados (Earnings)')
  if not df_main.empty:
    st.markdown('### 📅 Calendario de Dividendos')
    for index, row in df_main.iterrows():
        if row['Yield_Pct'] > 0:
            c1, c2, c3, c4 = st.columns([0.6, 2.5, 1.8, 2.1])
            with c1:
                st.markdown(f'<div class="ticker-badge">{row["Ticker"]}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{row['Nombre']}**")
            with c3:
                st.markdown(f"Ex-Fecha: <b>{row['Ex_Date']}</b>", unsafe_allow_html=True)
            with c4:
                st.markdown(f"Rentabilidad: <span style='color: #238636; font-weight: bold;'>{row['Yield_Pct']:.2f}%</span>", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 5px 0px; border-color: #21262d;'>", unsafe_allow_html=True)

    st.markdown('<br>### 📊 Próximos Resultados (Earnings)', unsafe_allow_html=True)
    for index, row in df_main.iterrows():
        c1, c2, c3 = st.columns([0.6, 3.0, 3.0])
        with c1:
            st.markdown(f'<div class="ticker-badge">{row["Ticker"]}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f"**{row['Nombre']}**")
        with c3:
            st.markdown(f"📅 Fecha estimada: **{row['Earnings']}**")
        st.markdown("<hr style='margin: 5px 0px; border-color: #21262d;'>", unsafe_allow_html=True)

with tab5:
  st.subheader('📰 Noticias Financieras en Vivo')
  if all_news:
    for news in all_news:
      st.markdown(f"""
        <div class="news-card">
            <span style="background-color: #238636; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{news['Activo']}</span>
            <br><br>
            <a href="{news['Enlace']}" target="_blank" style="color: #58a6ff; text-decoration: none; font-size: 16px; font-weight: bold;">{news['Titulo']}</a>
            <p style="color: #8b949e; font-size: 11px; margin-top: 5px;">Publicado: {news['Fecha']}</p>
        </div>
      """, unsafe_allow_html=True)
  else:
    st.info('No se encontraron noticias recientes o el servicio RSS no devolvió elementos.')

with tab6:
  st.subheader('📉 Evolución Gráfica Avanzada (Últimos 3 Meses)')
  all_available_tickers = TICKERS + TRACKING_TICKERS
  selected_ticker = st.selectbox('Selecciona el activo para ver el gráfico de precios:', all_available_tickers)

  if selected_ticker:
    try:
      stock_obj = yf.Ticker(selected_ticker)
      hist_data = stock_obj.history(period='3mo')['Close']
      st.line_chart(hist_data, color="#238636")
    except Exception as e:
      st.error(f'No se pudo cargar el gráfico para {selected_ticker}: {e}')
