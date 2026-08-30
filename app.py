import subprocess
import sys

try:
  import yfinance as yf
except ImportError:
  subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
  import yfinance as yf
  from datetime import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

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


@st.cache_data(ttl=300)
def get_market_data(tickers_list):
  data = []
  for ticker in tickers_list:
    try:
      stock = yf.Ticker(ticker)
      hist = stock.history(period='3mo')
      if len(hist) >= 2:
        today_data = hist.iloc[-1]
        prev_data = hist.iloc[-2]

        close_today = today_data['Close']
        close_prev = prev_data['Close']
        vol_today = today_data['Volume']
        avg_volume = (
            hist['Volume'][:-1].mean() if len(hist) > 1 else vol_today
        )

        price_change = ((close_today - close_prev) / close_prev) * 100
        currency = '€' if ticker in ['MC.PA', 'NOV.DE'] else '$'
        search_term = NAMES.get(ticker, ticker)

        vol_ratio = (
            (vol_today / avg_volume) * 100 if avg_volume > 0 else 0.0
        )

        data.append({
            'Ticker': ticker,
            'Nombre': search_term,
            'Precio': close_today,
            'Moneda': currency,
            'Cambio (%)': price_change,
            'Volumen Hoy': vol_today,
            'Volumen vs Media (%)': vol_ratio,
        })
    except Exception as e:
      print(f'Error obteniendo datos para {ticker}: {e}')
  return pd.DataFrame(data)


# Interfaz visual de la Web
st.title('📊 Panel de Control y Seguimiento Financiero')
st.markdown(
    f'*Actualizado a fecha:* {datetime.now().strftime("%d/%m/%Y %H:%M")}'
)

with st.spinner('Cargando cotizaciones de mercado en tiempo real...'):
  df_main = get_market_data(TICKERS)
  df_track = get_market_data(TRACKING_TICKERS)

# Pestañas de navegación de la web
tab1, tab2, tab3 = st.tabs([
    '🚀 Cartera Principal',
    '🔍 Cartera de Seguimiento',
    '📈 Gráficos de Evolución',
])

with tab1:
  st.subheader('Cartera Principal (Cierre, Dividendos y Métricas)')
  if not df_main.empty:
    df_main_sorted = df_main.sort_values(by='Cambio (%)', ascending=False)
    df_display = df_main_sorted.copy()
    df_display['Precio_Fmt'] = df_display.apply(
        lambda x: f"{x['Moneda']}{x['Precio']:.2f}", axis=1
    )
    df_display['Cambio_Fmt'] = df_display['Cambio (%)'].map(
        lambda x: f'{x:+.2f}%'
    )
    df_display['Volumen_Fmt'] = df_display['Volumen Hoy'].map(
        lambda x: f'{x:,.0f}'
    )
    df_display['Vol_Media_Fmt'] = df_display['Volumen vs Media (%)'].map(
        lambda x: f'{x:.0f}%'
    )

    # Métricas superiores rápidas
    col1, col2, col3 = st.columns(3)
    best_asset = df_main_sorted.iloc[0]
    worst_asset = df_main_sorted.iloc[-1]
    col1.metric(
        'Activos Monitoreados',
        len(df_main),
        help='Total de activos en cartera principal',
    )
    col2.metric(
        'Mayor Subida',
        best_asset['Nombre'],
        f"{best_asset['Cambio (%)']:+.2f}%",
    )
    col3.metric(
        'Mayor Bajada',
        worst_asset['Nombre'],
        f"{worst_asset['Cambio (%)']:+.2f}%",
    )

    st.markdown('---')
    st.dataframe(
        df_display[[
            'Ticker',
            'Nombre',
            'Precio_Fmt',
            'Cambio_Fmt',
            'Volumen_Fmt',
            'Vol_Media_Fmt',
        ]].rename(
            columns={
                'Precio_Fmt': 'Precio',
                'Cambio_Fmt': 'Cambio',
                'Volumen_Fmt': 'Volumen',
                'Vol_Media_Fmt': 'Vol vs Media',
            }
        ),
        use_container_width=True,
    )

with tab2:
  st.subheader('Cartera de Seguimiento (GOSS, BSIN...)')
  st.markdown(
      'Control exclusivo de precios y volúmenes para activos secundarios.'
  )
  if not df_track.empty:
    df_track_sorted = df_track.sort_values(by='Cambio (%)', ascending=False)
    df_track_display = df_track_sorted.copy()
    df_track_display['Precio_Fmt'] = df_track_display.apply(
        lambda x: f"{x['Moneda']}{x['Precio']:.2f}", axis=1
    )
    df_track_display['Cambio_Fmt'] = df_track_display['Cambio (%)'].map(
        lambda x: f'{x:+.2f}%'
    )
    df_track_display['Volumen_Fmt'] = df_track_display['Volumen Hoy'].map(
        lambda x: f'{x:,.0f}'
    )
    df_track_display['Vol_Media_Fmt'] = df_track_display[
        'Volumen vs Media (%)'
    ].map(lambda x: f'{x:.0f}%')

    st.dataframe(
        df_track_display[[
            'Ticker',
            'Nombre',
            'Precio_Fmt',
            'Cambio_Fmt',
            'Volumen_Fmt',
            'Vol_Media_Fmt',
        ]].rename(
            columns={
                'Precio_Fmt': 'Precio',
                'Cambio_Fmt': 'Cambio',
                'Volumen_Fmt': 'Volumen',
                'Vol_Media_Fmt': 'Vol vs Media',
            }
        ),
        use_container_width=True,
    )

with tab3:
  st.subheader('Evolución Gráfica de Activos (Últimos 3 Meses)')
  all_available_tickers = TICKERS + TRACKING_TICKERS
  selected_ticker = st.selectbox(
      'Selecciona el activo que deseas graficar:', all_available_tickers
  )

  if selected_ticker:
    try:
      stock_obj = yf.Ticker(selected_ticker)
      hist_data = stock_obj.history(period='3mo')['Close']
      st.line_chart(hist_data)
    except Exception as e:
      st.error(f'No se pudo cargar el gráfico para {selected_ticker}: {e}')
