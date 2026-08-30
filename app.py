import sys
import os
import base64
import requests
import json
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
        background-color: #090d16;
        color: #f0f2f6;
    }
    .metric-card {
        background: linear-gradient(135deg, #131b2e 0%, #0d1117 100%);
        border: 1px solid #21262d;
        padding: 16px;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        margin-bottom: 14px;
        transition: all 0.2s ease-in-out;
    }
    .metric-card:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
    }
    h1, h2, h3 {
        color: #f0f6fc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# Configuración de GitHub
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = "javierconesa-netizen/acciones-bot"
FILE_PATH = "portfolio_data.json"

def load_from_github():
    if not GITHUB_TOKEN:
        return None, None, None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        file_content = response.json()
        decoded_content = base64.b64decode(file_content["content"]).decode("utf-8")
        data = json.loads(decoded_content)
        return data.get("tickers"), data.get("custom_names"), data.get("portfolio_positions")
    return None, None, None

def save_to_github():
    if not GITHUB_TOKEN:
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    
    sha = None
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        sha = resp.json().get("sha")
        
    data_to_save = {
        "tickers": st.session_state.tickers,
        "custom_names": st.session_state.custom_names,
        "portfolio_positions": st.session_state.portfolio_positions
    }
    
    json_str = json.dumps(data_to_save, indent=4)
    encoded_content = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": "Actualizar datos de cartera automáticamente",
        "content": encoded_content,
    }
    if sha:
        payload["sha"] = sha
        
    requests.put(url, headers=headers, json=payload)

# Inicializar estado cargando desde GitHub o usando valores por defecto
cloud_tickers, cloud_names, cloud_positions = load_from_github()

if 'tickers' not in st.session_state:
    if cloud_tickers:
        st.session_state.tickers = cloud_tickers
    else:
        st.session_state.tickers = [
            'KO', 'NFLX', 'MC.PA', 'NOV.DE', 'ACHR', 'TSM', 'OPEN', 
            'NVDA', 'IREN', 'ASTS', 'ONDS', 'RKLB', 'GOOGL', 'SLNH', 
            'RZLV', 'LAES', 'BTC-USD', 'MU'
        ]

if 'portfolio_positions' not in st.session_state:
    if cloud_positions:
        st.session_state.portfolio_positions = cloud_positions
    else:
        st.session_state.portfolio_positions = {}

if 'custom_names' not in st.session_state:
    if cloud_names:
        st.session_state.custom_names = cloud_names
    else:
        st.session_state.custom_names = {
            'KO': 'Coca-Cola', 'MC.PA': 'LVMH', 'BTC-USD': 'Bitcoin',
            'NOV.DE': 'Novo Nordisk', 'OPEN': 'Opendoor Technologies',
            'NFLX': 'Netflix', 'NVDA': 'NVIDIA', 'TSM': 'TSMC',
            'GOOGL': 'Alphabet (Google)', 'ACHR': 'Archer Aviation',
            'IREN': 'Iris Energy', 'ASTS': 'AST SpaceMobile',
            'ONDS': 'Ondas Holdings', 'RKLB': 'Rocket Lab',
            'SLNH': 'Soluna Holdings', 'RZLV': 'Rezolve AI',
            'LAES': 'Sealsq / LAES', 'MU': 'Micron'
        }

# Asegurar nombre correcto para Micron
if st.session_state.custom_names.get('MU') in [None, '', 'MU']:
    st.session_state.custom_names['MU'] = 'Micron'

def generate_svg_sparkline(prices, is_positive):
    if not prices or len(prices) < 2:
        return ""
    min_p, max_p = min(prices), max(prices)
    rng = max_p - min_p if max_p != min_p else 1
    width, height = 75, 28
    points = []
    for i, p in enumerate(prices):
        x = (i / (len(prices) - 1)) * width
        y = height - ((p - min_p) / rng) * (height - 6) - 3
        points.append(f"{x:.1f},{y:.1f}")
    pts_str = " ".join(points)
    color = "#3fb950" if is_positive else "#f85149"
    return f'<svg width="{width}" height="{height}" style="overflow:visible;"><polyline fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" points="{pts_str}" /></svg>'

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
        if ticker == 'MU' and search_term == 'MU':
            search_term = 'Micron'
            
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

                recent_prices = hist['Close'].tail(15).tolist()
                sparkline_svg = generate_svg_sparkline(recent_prices, price_change_pct >= 0)

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
                    'Sparkline': sparkline_svg
                })
        except Exception as e:
            print(f'Error procesando {ticker}: {e}')
    return pd.DataFrame(data)

# Botón de Ajustes (Engranaje) alineado a la derecha
col_empty, col_gear = st.columns([5, 1])
with col_gear:
    with st.popover("⚙️", help="Panel de Control"):
        st.markdown("### ⚙️ Panel de Control")
        
        with st.expander("Gestionar Activos", expanded=True):
            new_m = st.text_input('Añadir ticker (ej: AAPL, SLNH):', key='pop_new_main')
            if st.button('➕ Añadir', key='pop_btn_main'):
                clean_m = new_m.strip().upper()
                if clean_m and clean_m not in st.session_state.tickers:
                    st.session_state.tickers.append(clean_m)
                    if clean_m not in st.session_state.custom_names:
                        if clean_m == 'MU':
                            real_name = 'Micron'
                        else:
                            try:
                                t_info = yf.Ticker(clean_m).info
                                real_name = t_info.get('longName') or t_info.get('shortName') or clean_m
                            except Exception:
                                real_name = clean_m
                        st.session_state.custom_names[clean_m] = real_name
                    save_to_github()
                    st.success(f'¡{clean_m} añadido con éxito!')
                    st.rerun()

            st.markdown('**Activos actuales:**')
            for t in list(st.session_state.tickers):
                cc1, cc2 = st.columns([3, 1])
                with cc1:
                    display_name = st.session_state.custom_names.get(t, t)
                    if t == 'MU' and display_name == 'MU':
                        display_name = 'Micron'
                    st.text(f"{display_name} ({t})")
                with cc2:
                    if len(st.session_state.tickers) > 1:
                        if st.button('🗑️', key=f'pop_del_m_{t}'):
                            st.session_state.tickers.remove(t)
                            if t in st.session_state.portfolio_positions:
                                del st.session_state.portfolio_positions[t]
                            if t in st.session_state.custom_names:
                                del st.session_state.custom_names[t]
                            save_to_github()
                            st.rerun()
                    else:
                        st.text('Mín 1')

        with st.expander("💼 Configurar Posiciones"):
            st.markdown("Introduce tus datos por activo:")
            changed_pos = False
            for t in st.session_state.tickers:
                asset_display_name = st.session_state.custom_names.get(t, t)
                if t == 'MU' and asset_display_name == 'MU':
                    asset_display_name = 'Micron'
                st.markdown(f"**{asset_display_name} ({t})**")
                current_pos = st.session_state.portfolio_positions.get(t, {'shares': 0.0, 'buy_price': 0.0})
                
                # Configurar precisión decimal alta para Bitcoin
                if 'BTC' in t:
                    sh = st.number_input(f"Acciones {t}", value=float(current_pos.get('shares', 0.0)), min_value=0.0, step=0.00001, format="%.5f", key=f"shares_{t}")
                else:
                    sh = st.number_input(f"Acciones {t}", value=float(current_pos.get('shares', 0.0)), min_value=0.0, step=1.0, key=f"shares_{t}")
                
                bp = st.number_input(f"Precio Compra {t}", value=float(current_pos.get('buy_price', 0.0)), min_value=0.0, step=0.01, key=f"buy_price_{t}")
                
                new_pos_dict = {'shares': sh, 'buy_price': bp}
                if st.session_state.portfolio_positions.get(t) != new_pos_dict:
                    st.session_state.portfolio_positions[t] = new_pos_dict
                    changed_pos = True
            
            if changed_pos:
                save_to_github()

with st.spinner('Actualizando mercados y posiciones...'):
    df_main = get_comprehensive_market_data_extended(tuple(st.session_state.tickers))
    
    eur_to_usd = 1.05
    try:
        ex_hist = yf.Ticker("EURUSD=X").history(period="1d")
        if not ex_hist.empty:
            eur_to_usd = float(ex_hist['Close'].iloc[-1])
    except Exception:
        pass

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
                price = row['Precio']
                
                if row['Moneda'] == '€':
                    total_invested += (sh * bp) * eur_to_usd
                    total_current_value += (sh * price) * eur_to_usd
                else:
                    total_invested += sh * bp
                    total_current_value += sh * price

    if has_positions:
        total_pl = total_current_value - total_invested
        total_pl_pct = (total_pl / total_invested) * 100 if total_invested > 0 else 0.0
        pl_color = "#3fb950" if total_pl >= 0 else "#f85149"
        
        total_invested_eur = total_invested / eur_to_usd
        total_current_value_eur = total_current_value / eur_to_usd
        total_pl_eur = total_pl / eur_to_usd
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><h4 style="color: #8b949e; font-size: 12px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">💰 Inversión Total</h4><h2 style="color: #f0f6fc; font-size: 18px;">${total_invested:,.2f} <span style="font-size: 14px; color: #8b949e; font-weight: normal;">(€{total_invested_eur:,.2f})</span></h2></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><h4 style="color: #8b949e; font-size: 12px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">📈 Valor Actual</h4><h2 style="color: #f0f6fc; font-size: 18px;">${total_current_value:,.2f} <span style="font-size: 14px; color: #8b949e; font-weight: normal;">(€{total_current_value_eur:,.2f})</span></h2></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><h4 style="color: #8b949e; font-size: 12px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">⚖️ Plusvalía Global</h4><h2 style="font-size: 18px;"><span style="color: {pl_color};">${total_pl:+,.2f} ({total_pl_pct:+.2f}%)</span> <span style="color: {pl_color}; font-size: 18px;">(€{total_pl_eur:+,.2f})</span></h2></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background: #131b2e; border: 1px solid #21262d; padding: 12px 16px; border-radius: 12px; margin-bottom: 15px; font-size: 14px; color: #8b949e;">📊 <b>Activos Totales en Seguimiento:</b> <span style="color: #f0f6fc; font-weight: bold;">{len(df_main)}</span></div>', unsafe_allow_html=True)

    st.markdown('---')

    c_f1, c_f2 = st.columns(2)
    with c_f1:
        timeframe_label = st.selectbox(
            "⏱️ Periodo", 
            ['Actual', '1 Mes', '3 Meses', '6 Meses', '1 Año', 'YTD'],
            key='main_tf_select'
        )
    with c_f2:
        sort_option = st.selectbox(
            "🔄 Ordenar", 
            ['Diario [Alto a Bajo]', 'Diario [Bajo a Alto]', 
             f'Histórico [Alto a Bajo]', f'Histórico [Bajo a Alto]',
             'Ganancia (€) [Alto a Bajo]'],
            key='main_sort_select'
        )

    tf_mapping = {
        'Actual': 'Cambio (%)',
        '1 Mes': 'Perf_1M',
        '3 Meses': 'Perf_3M',
        '6 Meses': 'Perf_6M',
        '1 Año': 'Perf_1Y',
        'YTD': 'Perf_YTD'
    }
    active_perf_col = tf_mapping[timeframe_label]

    def calc_abs_pl(row):
        t = row['Ticker']
        pos = st.session_state.portfolio_positions.get(t, {})
        sh = pos.get('shares', 0.0)
        bp = pos.get('buy_price', 0.0)
        if sh > 0 and bp > 0:
            diff = (row['Precio'] - bp) * sh
            return diff * eur_to_usd if row['Moneda'] == '€' else diff
        return 0.0

    df_main['Temp_P_L'] = df_main.apply(calc_abs_pl, axis=1)

    if 'Diario [Alto a Bajo]' in sort_option:
        df_main = df_main.sort_values(by='Cambio (%)', ascending=False)
    elif 'Diario [Bajo a Alto]' in sort_option:
        df_main = df_main.sort_values(by='Cambio (%)', ascending=True)
    elif '[Alto a Bajo]' in sort_option and 'Histórico' in sort_option:
        df_main = df_main.sort_values(by=active_perf_col, ascending=False)
    elif '[Bajo a Alto]' in sort_option and 'Histórico' in sort_option:
        df_main = df_main.sort_values(by=active_perf_col, ascending=True)
    elif 'Ganancia (€) [Alto a Bajo]' in sort_option:
        df_main = df_main.sort_values(by='Temp_P_L', ascending=False)

    st.markdown('---')

    def render_portfolio_card_grid(row, perf_col, tf_label):
        color_daily = "#3fb950" if row['Cambio (%)'] >= 0 else "#f85149"
        sign_daily = "+" if row['Cambio (%)'] >= 0 else ""
        
        show_hist = tf_label != 'Actual'
        hist_badge = ""
        if show_hist:
            hist_val = row[perf_col]
            color_hist = "#3fb950" if hist_val >= 0 else "#f85149"
            sign_hist = "+" if hist_val >= 0 else ""
            hist_badge = f'<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 11px; color: #8b949e;"><span>{tf_label}:</span><span style="color: {color_hist}; font-weight: bold;">{sign_hist}{hist_val:.2f}%</span></div>'

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
            p_color = "#3fb950" if diff >= 0 else "#f85149"
            p_sign = "+" if diff >= 0 else ""
            
            # Mostrar más decimales en las unidades si es Bitcoin
            shares_str = f"{sh:.5f}".rstrip('0').rstrip('.') if 'BTC' in t else f"{sh:g}"
            pos_html = f'<div style="background: rgba(19, 27, 46, 0.8); border-left: 3px solid {p_color}; margin-top: 8px; padding: 6px 8px; border-radius: 4px; font-size: 11px; display: flex; justify-content: space-between; align-items: center;"><span>💼 {shares_str} acc.</span><span style="color: {p_color}; font-weight: bold;">{p_sign}{row["Moneda"]}{diff:,.2f} ({p_sign}{diff_pct:.1f}%)</span></div>'

        card_html = (
            f'<div style="background: linear-gradient(145deg, #131b2e 0%, #090d16 100%); border: 1px solid #21262d; border-radius: 14px; padding: 14px; margin-bottom: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">'
            f'<div style="display: flex; justify-content: space-between; align-items: flex-start;">'
            f'<div><span style="font-size: 14px; font-weight: bold; color: #f0f6fc;">{row["Nombre"]}</span><br>'
            f'<span style="color: #8b949e; font-size: 10px; background: #1f2937; padding: 1px 5px; border-radius: 4px;">{row["Ticker"]}</span></div>'
            f'<div style="text-align: right;"><span style="font-size: 16px; font-weight: 800; color: #ffffff;">{row["Moneda"]}{row["Precio"]:.3f}</span></div>'
            f'</div>'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">'
            f'<div><span style="font-size: 11px; color: #8b949e;">Hoy:</span><br>'
            f'<span style="color: {color_daily}; font-weight: bold; font-size: 12px;">{sign_daily}{row["Cambio (%)"]:.2f}%</span></div>'
            f'<div>{row["Sparkline"]}</div>'
            f'</div>'
            f'{hist_badge}'
            f'{pos_html}'
            f'</div>'
        )

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

    st.markdown('---')
    csv_main = df_main.drop(columns=['Temp_P_L', 'Sparkline']).to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Cartera Principal (CSV)",
        data=csv_main,
        file_name='cartera_principal.csv',
        mime='text/csv',
    )
