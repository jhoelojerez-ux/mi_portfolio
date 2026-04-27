import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Forex Algo Pro", layout="wide")

# --- BARRA LATERAL ---
st.sidebar.header("🕹️ Configuración del Bot")
dict_activos = {"Euro / Dólar": "EURUSD=X", "Bitcoin": "BTC-USD", "Oro": "GC=F"}
seleccion = st.sidebar.selectbox("Activo", list(dict_activos.keys()))
ticker = dict_activos[seleccion]

saldo_inicial = st.sidebar.number_input("Saldo Inicial ($)", value=10000.0)
tamano_trade = st.sidebar.number_input("Cantidad por Trade ($)", value=200.0)

# NUEVO: Control de Take Profit y Stop Loss
# Para Forex (EUR/USD) 0.0020 son 20 pips. Para BTC podrías usar 500 o más.
tp_ajuste = st.sidebar.slider("Objetivo de Ganancia (Take Profit)", 0.0005, 0.0500, 0.0030, format="%.4f")

# --- DATOS ---
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

data = load_data(ticker)

# Indicadores
data['MA10'] = data['Close'].rolling(10).mean()
data['MA20'] = data['Close'].rolling(20).mean()
data['STD20'] = data['Close'].rolling(20).std()
data['Lower'] = data['MA20'] - (data['STD20'] * 2)
data['Upper'] = data['MA20'] + (data['STD20'] * 2)
data = data.dropna()

# --- MOTOR CON TAKE PROFIT FIJO ---
log_eventos = []
balance = saldo_inicial
posicion = None

for i in range(len(data)):
    current_time = data.index[i]
    price = float(data['Close'].iloc[i])
    row = data.iloc[i]
    
    if posicion is None:
        # ENTRADA
        if row['MA10'] > row['MA20'] and price > row['MA20']:
            # Calculamos el precio de salida con ganancia al entrar
            precio_tp = price + tp_ajuste
            posicion = {'tipo': 'LONG', 'entrada': price, 'tp': precio_tp}
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA LONG", "Precio": price, "Balance": f"${balance:.2f}"})
            
        elif row['MA10'] < row['MA20'] and price < row['MA20']:
            precio_tp = price - tp_ajuste
            posicion = {'tipo': 'SHORT', 'entrada': price, 'tp': precio_tp}
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA SHORT", "Precio": price, "Balance": f"${balance:.2f}"})
            
    elif posicion['tipo'] == 'LONG':
        # LÓGICA DE SALIDA
        razon = ""
        if price >= posicion['tp']: 
            razon = "TAKE PROFIT 🎯"
        elif price <= row['Lower']: 
            razon = "STOP LOSS (Banda Inf)"
        elif price < row['MA10']: 
            razon = "SALIDA (Cruce MA10)"
        
        if razon:
            pnl = tamano_trade * ((price - posicion['entrada']) / posicion['entrada'])
            balance += pnl
            log_eventos.append({"Fecha": current_time, "Acción": razon, "Precio": price, "PnL": f"${pnl:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None
            
    elif posicion['tipo'] == 'SHORT':
        razon = ""
        if price <= posicion['tp']: 
            razon = "TAKE PROFIT 🎯"
        elif price >= row['Upper']: 
            razon = "STOP LOSS (Banda Sup)"
        elif price > row['MA10']: 
            razon = "SALIDA (Cruce MA10)"
        
        if razon:
            pnl = tamano_trade * ((posicion['entrada'] - price) / posicion['entrada'])
            balance += pnl
            log_eventos.append({"Fecha": current_time, "Acción": razon, "Precio": price, "PnL": f"${pnl:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None

# --- DASHBOARD ---
st.title(f"📊 Estrategia con Take Profit: {seleccion}")
c1, c2, c3 = st.columns(3)
c1.metric("Balance Final", f"${balance:.2f}", f"{balance-saldo_inicial:.2f}")
c2.metric("Retorno Total", f"{((balance-saldo_inicial)/saldo_inicial)*100:.2f}%")
c3.metric("Trades", len([x for x in log_eventos if "ENTRADA" in x['Acción']]))

st.plotly_chart(go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])]), use_container_width=True)
st.dataframe(pd.DataFrame(log_eventos), use_container_width=True)
