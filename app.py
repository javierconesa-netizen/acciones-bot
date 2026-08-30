import sys
import os

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

from datetime import datetime
import pandas as pd
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title='Panel de Inversión y Seguimiento', page_icon='📈', layout='wide'
)

# Listas de activos idénticas a la estructura de tu bot
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
    'ASTS',
    'ONDS',
    'RKLB',
    'GOOGL',
    'SLNH',
    'RZLV',
    'LAES',
    'BTC-USD',
]

TRACKING_TICKERS = [
    'GOSS',
    'BSIN',
]

NAMES = {
    'KO': 'Coca-Cola',
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

        price_change = ((close_today - close_prev) / close_prev) * 100
        currency = '€' if ticker in ['MC.PA', 'NOV.DE'] else '$'
        vol_ratio = (vol_today / avg_volume) * 100 if avg_volume > 0 else 0.0

        # Cálculo de RSI (idéntico al bot)
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
          rsi_label = 'Sobrecompra (>70)'
        elif current_rsi < 30:
          rsi_label = 'Sobreventa (<30)'

        # Dividendos
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

        # Earnings
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
            'Cambio (%)': price_change,
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


# Interfaz visual de la Web
st.title('📊 Panel de Control y Seguimiento Financiero')
st.markdown(f'*Actualizado a fecha:* {datetime.now().strftime("%d/%m/%Y %H:%M")}')

with st.spinner('Cargando cotizaciones y métricas de mercado...'):
  df_main = get_comprehensive_market_data(TICKERS)
  df_track = get_comprehensive_market_data(TRACKING_TICKERS)

# Pestañas de navegación adaptadas al contenido del bot
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    '🚀 Cartera Principal',
    '🔍 Cartera Seguimiento',
    '📈 Análisis Técnico & RSI',
    '💰 Dividendos & Earnings',
    '📉 Gráficos',
])

with tab1:
  st.subheader('Cartera Principal (Precios y Volúmenes)')
  if not df_main.empty:
    df_main_sorted = df_main.sort_values(by='Cambio (%)', ascending=False)
    df_display = df_main_sorted.copy()
    df_display['Precio_Fmt'] = df_display.apply(lambda x: f"{x['Moneda']}{x['Precio']:.2f}", axis=1)
    df_display['Cambio_Fmt'] = df_display['Cambio (%)'].map(lambda x: f'{x:+.2f}%')
    df_display['Volumen_Fmt'] = df_display['Volumen Hoy'].map(lambda x: f'{x:,.0f}')
    df_display['Vol_Media_Fmt'] = df_display['Volumen vs Media (%)'].map(lambda x: f'{x:.0f}%')

    col1, col2, col3 = st.columns(3)
    best_asset = df_main_sorted.iloc[0]
    worst_asset = df_main_sorted.iloc[-1]
    col1.metric('Activos Monitoreados', len(df_main))
    col2.metric('Mayor Subida', best_asset['Nombre'], f"{best_asset['Cambio (%)']:+.2f}%")
    col3.metric('Mayor Bajada', worst_asset['Nombre'], f"{worst_asset['Cambio (%)']:+.2f}%")

    st.markdown('---')
    st.dataframe(
        df_display[['Ticker', 'Nombre', 'Precio_Fmt', 'Cambio_Fmt', 'Volumen_Fmt', 'Vol_Media_Fmt']].rename(
            columns={'Precio_Fmt': 'Precio', 'Cambio_Fmt': 'Cambio', 'Volumen_Fmt': 'Volumen', 'Vol_Media_Fmt': 'Vol vs Media'}
        ),
        width='stretch',
    )

with tab2:
  st.subheader('Cartera de Seguimiento (Secundarios)')
  if not df_track.empty:
    df_track_sorted = df_track.sort_values(by='Cambio (%)', ascending=False)
    df_track_display = df_track_sorted.copy()
    df_track_display['Precio_Fmt'] = df_track_display.apply(lambda x: f"{x['Moneda']}{x['Precio']:.2f}", axis=1)
    df_track_display['Cambio_Fmt'] = df_track_display['Cambio (%)'].map(lambda x: f'{x:+.2f}%')
    df_track_display['Volumen_Fmt'] = df_track_display['Volumen Hoy'].map(lambda x: f'{x:,.0f}')
    df_track_display['Vol_Media_Fmt'] = df_track_display['Volumen vs Media (%)'].map(lambda x: f'{x:.0f}%')

    st.dataframe(
        df_track_display[['Ticker', 'Nombre', 'Precio_Fmt', 'Cambio_Fmt', 'Volumen_Fmt', 'Vol_Media_Fmt']].rename(
            columns={'Precio_Fmt': 'Precio', 'Cambio_Fmt': 'Cambio', 'Volumen_Fmt': 'Volumen', 'Vol_Media_Fmt': 'Vol vs Media'}
        ),
        width='stretch',
    )

with tab3:
  st.subheader('📈 Análisis Técnico (RSI)')
  if not df_main.empty:
    df_rsi = df_main[['Ticker', 'Nombre', 'RSI', 'RSI_Label']].sort_values(by='RSI', ascending=False).copy()
    df_rsi['RSI'] = df_rsi['RSI'].map(lambda x: f'{x:.1f}')
    st.dataframe(df_rsi.rename(columns={'RSI_Label': 'Estado'}), width='stretch')

with tab4:
  st.subheader('💰 Dividendos y Próximos Resultados (Earnings)')
  if not df_main.empty:
    df_div_earn = df_main[['Ticker', 'Nombre', 'Ex_Date', 'Yield_Pct', 'Div_Rate', 'Moneda', 'Earnings']].copy()
    df_div_earn['Yield_Fmt'] = df_div_earn['Yield_Pct'].map(lambda x: f'{x:.2f}%')
    df_div_earn['Div_Fmt'] = df_div_earn.apply(lambda x: f"{x['Moneda']}{x['Div_Rate']:.2f}", axis=1)
    
    st.markdown('### Calendario de Dividendos')
    st.dataframe(
        df_div_earn[['Ticker', 'Nombre', 'Ex_Date', 'Yield_Fmt', 'Div_Fmt']].rename(
            columns={'Ex_Date': 'Fecha Ex-Dividendo', 'Yield_Fmt': 'Rentabilidad Anual', 'Div_Fmt': 'Dividendo Anual'}
        ),
        width='stretch',
    )

    st.markdown('### Próximos Earnings (Resultados)')
    st.dataframe(
        df_div_earn[['Ticker', 'Nombre', 'Earnings']].rename(columns={'Earnings': 'Fecha Estimada'}),
        width='stretch',
    )

with tab5:
  st.subheader('Evolución Gráfica de Activos (Últimos 3 Meses)')
  all_available_tickers = TICKERS + TRACKING_TICKERS
  selected_ticker = st.selectbox('Selecciona el activo que deseas graficar:', all_available_tickers)

  if selected_ticker:
    try:
      stock_obj = yf.Ticker(selected_ticker)
      hist_data = stock_obj.history(period='3mo')['Close']
      st.line_chart(hist_data)
    except Exception as e:
      st.error(f'No se pudo cargar el gráfico para {selected_ticker}: {e}')
