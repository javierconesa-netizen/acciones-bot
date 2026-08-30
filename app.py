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
    page_title='Mi Cartera', page_icon='💎', layout='wide'
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
    </style>
""", unsafe_allow_html=True)

if 'tickers' not in st.session_state:
    st.session_state.tickers = [
        'KO', 'NFLX', 'MC.PA', 'NOV.DE', 'ACHR', 'TSM', 'OPEN', 
        'NVDA', 'IREN', 'ASTS', 'ONDS', 'RKLB', 'GOOGL', 'SLNH', 
        'RZLV', 'LAES', 'BTC-USD'
    ]

if 'portfolio_positions' not in st.session_state:
    st.session_state.portfolio_positions = {}

if 'custom_names' not in st.session_state:
    st.session_state.custom_names = {
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
        'SLNH': 'Soluna Holdings',
        'RZLV': 'Rezolve AI',
        'LAES': 'Sealsq / LAES'
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
def get_comprehensive_market_data_extended(tickers_tuple):
    if not tickers_tuple:
        return pd.DataFrame()
    
    data = []
    try:
        hist_data = yf.download(list(tickers_tuple), period='1y', progress=False, group_by='ticker')
    except Exception:
        hist_data = None

    for ticker in tickers_tuple:
        search_term = st.session_state.custom_names.get(ticker, ticker)
        try:
            if hist_data is not None and len(tickers_tuple) > 1:
                try:
                    hist = hist_data[ticker].dropna(subset=['Close'])
                except Exception:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period='1y')
            else:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='1y')

            if len(hist) >= 2:
                today_data = hist.iloc[-1]
                prev_data = hist.iloc[-2]

                close_today = float(today_data['Close'])
                close_prev = float(prev_data['Close'])

                price_change_abs = close_today - close_prev
                price_change_pct = (price_change_abs / close_prev) * 100
                currency = '€' if ticker in ['MC.PA', 'NOV.DE'] else '$'

                def get_perf(days_offset):
                    if len(hist) > days_offset:
                        past_price = float(hist['Close'].iloc[-days_offset])
                        return ((close_today - past_price) / past_price) * 100
                    return 0.0

                perf_1m = get_perf(21)
                perf_3m = get_perf(63)
                perf_6m = get_perf(126)
                perf_1y = get_perf(252)

                current_year = datetime.now().year
                hist_ytd = hist[hist.index.year == current_year]
                if not hist_ytd.empty:
                    start_ytd_price = float(hist_ytd['Close'].iloc[0])
                    perf_ytd = ((close_today - start_ytd_price) / start_ytd_price) * 100
                else:
                    perf_ytd = 0.0

                data.append({
                    'Ticker': ticker,
                    'Nombre': search_term,
                    'Precio': close_today,
                    'Moneda': currency,
                    'Cambio (%)': price_change_pct,
                    'Cambio Abs': price_change_abs,
                    'Perf_1M': perf_1m,
                    'Perf_3M': perf_3m,
                    'Perf_6M': perf_6m,
                    'Perf_1Y': perf_1y,
                    'Perf_YTD': perf_ytd,
                })
        except Exception as e:
            print(f'Error procesando {ticker}: {e}')
    return pd.DataFrame(data)

# Cabecera principal con Título y Botón de Ajustes (Engranaje)
col_title, col_gear = st.columns([5, 1])
with col_title:
    st.title('Mi Cartera')
    st.markdown(f'<p style="color: #8b949e; font-size: 15px; margin-top: -10px;">🚀 Sincronización en tiempo real — Actualizado a fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>', unsafe_allow_html=True)

with col_gear:
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    with st.popover("⚙️", help="Panel de Control"):
        st.markdown("### ⚙️ Panel de Control")
        
        with st.expander("Gestionar Activos", expanded=True):
            new_m = st.text_input('Añadir ticker (ej: AAPL, SLNH):', key='pop_new_main')
            if st.button('➕ Añadir', key='pop_btn_main'):
                clean_m = new_m.strip().upper()
                if clean_m and clean_m not in st.session_state.tickers:
                    with st.spinner(f"Consultando información de {clean_m}..."):
                        try:
                            tk_info = yf.Ticker(clean_m).info
                            fetched_name = tk_info.get('longName') or tk_info.get('shortName') or clean_m
                        except Exception:
                            fetched_name = clean_m
                        
                        st.session_state.tickers.append(clean_m)
                        st.session_state.custom_names[clean_m] = fetched_name
                        st.success(f'¡{fetched_name} ({clean_m}) añadido!')
                        st.rerun()
            st.markdown('**Activos actuales:**')
            for t in list(st.session_state.tickers):
                cc1, cc2 = st.columns([3, 1])
                with cc1:
                    st.text(f"{st.session_state.custom_names.get(t, t)} ({t})")
                with cc2:
                    if len(st.session_state.tickers) > 1:
                        if st.button('🗑️', key=f'pop_del_m_{t}'):
                            st.session_state.tickers.remove(t)
                            if t in st.session_state.portfolio_positions:
                                del st.session_state.portfolio_positions[t]
                            if t in st.session_state.custom_names:
                                del st.session_state.custom_names[t]
                            st.rerun()
                    else:
                        st.text('Mín 1')

        with st.expander("💼 Configurar Posiciones"):
            st.markdown("Introduce tus datos por activo:")
            for t in st.session_state.tickers:
                asset_display_name = st.session_state.custom_names.get(t, t)
                st.markdown(f"**{asset_display_name} ({t})**")
                current_pos = st.session_state.portfolio_positions.get(t, {'shares': 0.0, 'buy_price': 0.0})
                sh = st.number_input(f"Acciones {t}", value=float(current_pos.get('shares', 0.0)), min_value=0.0, step=1.0, key=f"shares_{t}")
                bp = st.number_input(f"Precio Compra {t}", value=float(current_pos.get('buy_price', 0.0)), min_value=0.0, step=0.01, key=f"buy_price_{t}")
                st.session_state.portfolio_positions[t] = {'shares': sh, 'buy_price': bp}

with st.spinner('Actualizando mercados y posiciones...'):
    df_main = get_comprehensive_market_data_extended(tuple(st.session_state.tickers))

if not df_main.empty:
    total_invested = 0.0
    total_current_value = 0.0
    has_positions = False

    for _, row in df_main.iterrows():
        t = row['Ticker']
        if t in st.session_state.portfolio_positions:
            pos = st.session_state.portfolio_positions[t]
            sh = pos.get('shares', 0.0)
            bp = pos.get('buy_price', 0.0)
            if sh > 0 and bp > 0:
                has_positions = True
                total_invested += sh * bp
                total_current_value += sh * row['Precio']

    if has_positions:
        total_pl = total_current_value - total_invested
        total_pl_pct = (total_pl / total_invested) * 100 if total_invested > 0 else 0.0
        pl_color = "#238636" if total_pl >= 0 else "#da3633"
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><h4>💰 Inversión Total</h4><h2>${total_invested:,.2f}</h2></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><h4>📈 Valor Actual</h4><h2>${total_current_value:,.2f}</h2></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><h4>⚖️ Plusvalía Global</h4><h2><span style="color: {pl_color};">${total_pl:+,.2f} ({total_pl_pct:+.2f}%)</span></h2></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background: #161b22; border: 1px solid #30363d; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; color: #8b949e;">📊 <b>Activos Totales:</b> <span style="color: #f0f6fc; font-weight: bold;">{len(df_main)}</span></div>', unsafe_allow_html=True)

    st.markdown('---')

    c_f1, c_f2 = st.columns(2)
    with c_f1:
        timeframe_label = st.selectbox(
            "⏱️ Seleccionar Periodo", 
            ['Actual', '1 Mes', '3 Meses', '6 Meses', '1 Año', 'Año en curso (YTD)'],
            key='main_tf_select'
        )
    
    tf_mapping = {
        'Actual': 'Cambio (%)',
        '1 Mes': 'Perf_1M',
        '3 Meses': 'Perf_3M',
        '6 Meses': 'Perf_6M',
        '1 Año': 'Perf_1Y',
        'Año en curso (YTD)': 'Perf_YTD'
    }
    active_perf_col = tf_mapping[timeframe_label]

    with c_f2:
        sort_option = st.selectbox(
            "🔄 Ordenar Cartera por", 
            ['Cambio Diario (%) [Mayor a Menor]', 'Cambio Diario (%) [Menor a Mayor]', 
             f'Histórico ({timeframe_label}) [Mayor a Menor]', f'Histórico ({timeframe_label}) [Menor a Mayor]',
             'Ganancias Reales (€) [Mayor a Menor]', 'Ganancias Reales (€) [Menor a Mayor]'],
            key='main_sort_select'
        )

    def calc_abs_pl(row):
        t = row['Ticker']
        pos = st.session_state.portfolio_positions.get(t, {})
        sh = pos.get('shares', 0.0)
        bp = pos.get('buy_price', 0.0)
        if sh > 0 and bp > 0:
            return (row['Precio'] - bp) * sh
        return 0.0

    df_main['Temp_P_L'] = df_main.apply(calc_abs_pl, axis=1)

    if 'Diario (%) [Mayor a Menor]' in sort_option:
        df_main = df_main.sort_values(by='Cambio (%)', ascending=False)
    elif 'Diario (%) [Menor a Mayor]' in sort_option:
        df_main = df_main.sort_values(by='Cambio (%)', ascending=True)
    elif '[Mayor a Menor]' in sort_option and 'Histórico' in sort_option:
        df_main = df_main.sort_values(by=active_perf_col, ascending=False)
    elif '[Menor a Mayor]' in sort_option and 'Histórico' in sort_option:
        df_main = df_main.sort_values(by=active_perf_col, ascending=True)
    elif 'Ganancias Reales (€) [Mayor a Menor]' in sort_option:
        df_main = df_main.sort_values(by='Temp_P_L', ascending=False)
    elif 'Ganancias Reales (€) [Menor a Mayor]' in sort_option:
        df_main = df_main.sort_values(by='Temp_P_L', ascending=True)

    csv_main = df_main.drop(columns=['Temp_P_L']).to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Cartera Principal (CSV)",
        data=csv_main,
        file_name='cartera_principal.csv',
        mime='text/csv',
    )
    st.markdown('---')

    def render_portfolio_card_grid(row, perf_col, tf_label):
        color_daily = "#238636" if row['Cambio (%)'] >= 0 else "#da3633"
        sign_daily = "+" if row['Cambio (%)'] >= 0 else ""
        
        hist_val = row[perf_col]
        color_hist = "#238636" if hist_val >= 0 else "#da3633"
        sign_hist = "+" if hist_val >= 0 else ""

        t = row['Ticker']
        pos = st.session_state.portfolio_positions.get(t, {'shares': 0.0, 'buy_price': 0.0})
        sh = pos.get('shares', 0.0)
        bp = pos.get('buy_price', 0.0)
        
        pos_html = ""
        if sh > 0 and bp > 0:
            cur_val = sh * row['Precio']
            inv_val = sh * bp
            diff = cur_val - inv_val
            diff_pct = (diff / inv_val) * 100
            p_color = "#238636" if diff >= 0 else "#da3633"
            p_sign = "+" if diff >= 0 else ""
            pos_html = f'<div style="border-top: 1px solid #30363d; margin-top: 6px; padding-top: 4px; font-size: 11px;">💼 {sh:g} acc. | P&L: <span style="color: {p_color}; font-weight: bold;">{p_sign}{row["Moneda"]}{diff:,.2f} ({p_sign}{diff_pct:.1f}%)</span></div>'

        card_html = f'<div style="background: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 8px; margin-bottom: 10px;"><span style="font-size: 13px; font-weight: bold; color: #f0f6fc;">{row["Nombre"]}</span><br><span style="color: #8b949e; font-size: 10px;">{row["Ticker"]}</span><div style="margin-top: 4px;"><span style="font-size: 15px; font-weight: bold; color: #f0f6fc;">{row["Moneda"]}{row["Precio"]:.3f}</span></div><div style="font-size: 11px; margin-top: 6px;"><span>Día: <span style="color: {color_daily}; font-weight: bold;">{sign_daily}{row["Cambio (%)"]:.2f}%</span></span><br><span>{tf_label}: <span style="color: {color_hist}; font-weight: bold;">{sign_hist}{hist_val:.2f}%</span></span></div>{pos_html}</div>'

        st.markdown(card_html, unsafe_allow_html=True)

    assets_list = list(df_main.iterrows())
    for i in range(0, len(assets_list), 2):
        col_a, col_b = st.columns(2)
        with col_a:
            if i < len(assets_list):
                _, row = assets_list[i]
                render_portfolio_card_grid(row, active_perf_col, timeframe_label)
        with col_b:
            if i + 1 < len(assets_list):
                _, row = assets_list[i + 1]
                render_portfolio_card_grid(row, active_perf_col, timeframe_label)
