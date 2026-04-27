import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Multi-Asset Algo Tester", layout="wide")

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("🕹️ Panel de Control")

# 1. Selección de Activo
dict_activos = {
    "Euro / Dólar": "EURUSD=X",
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Apple (Acciones)": "AAPL",
    "Oro": "GC=F"
}
seleccion = st.sidebar.selectbox("Selecciona el Activo", list(dict_activos.keys()))
ticker = dict_activos[seleccion]

# 2. Configuración de Dinero
saldo_inicial = st.sidebar.number_input("Saldo Inicial ($)", value=10000.0, step=1000.0)
tamano_trade = st.sidebar.number_input("Cantidad por Trade ($)", value=200.0, step=50.0)

# 3. Temporalidad
periodo = st.sidebar.selectbox("Periodo de Backtesting", ["6mo", "1y", "2y"], index=1)

st.title(f"🚀 Visualizador: {seleccion}")
st.write(f"Probando estrategia agresiva en **{ticker}** con trades de **${tamano_trade}**")

# --- PROCESAMIENTO DE DATOS ---
@st.cache_data
def load_data(symbol, p):
    df = yf.download(symbol, period=p, interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

data = load_data(ticker, periodo)

# Indicadores
data['MA10'] = data['Close'].rolling(10).mean()
data['MA20'] = data['Close'].rolling(20).mean()
data['STD20'] = data['Close'].rolling(20).std()
data['Upper'] = data['MA20'] + (data['STD20'] * 2)
data['Lower'] = data['MA20'] - (data['STD20'] * 2)
data = data.dropna()

# --- MOTOR DE SIMULACIÓN ---
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
            posicion = {'tipo': 'LONG', 'entrada': price}
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA LONG", "Precio": price, "Balance": f"${balance:.2f}"})
        elif row['MA10'] < row['MA20'] and price < row['MA20']:
            posicion = {'tipo': 'SHORT', 'entrada': price}
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA SHORT", "Precio": price, "Balance": f"${balance:.2f}"})
            
    elif posicion['tipo'] == 'LONG':
        # SALIDA
        razon = ""
        if price <= row['Lower']: razon = "STOP LOSS (Banda Inf)"
        elif price < row['MA10']: razon = "SALIDA RÁPIDA (MA10)"
        
        if razon:
            pnl = tamano_trade * ((price - posicion['entrada']) / posicion['entrada'])
            balance += pnl
            log_eventos.append({"Fecha": current_time, "Acción": razon, "Precio": price, "PnL": f"${pnl:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None
            
    elif posicion['tipo'] == 'SHORT':
        # SALIDA
        razon = ""
        if price >= row['Upper']: razon = "STOP LOSS (Banda Sup)"
        elif price > row['MA10']: razon = "SALIDA RÁPIDA (MA10)"
        
        if razon:
            pnl = tamano_trade * ((posicion['entrada'] - price) / posicion['entrada'])
            balance += pnl
            log_eventos.append({"Fecha": current_time, "Acción": razon, "Precio": price, "PnL": f"${pnl:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None

# --- INTERFAZ DE RESULTADOS ---
c1, c2, c3 = st.columns(3)
retorno_total = ((balance - saldo_inicial) / saldo_inicial) * 100
c1.metric("Balance Final", f"${balance:.2f}")
c2.metric("Retorno Total", f"{retorno_total:.2f}%")
c3.metric("Trades Realizados", len([x for x in log_eventos if "ENTRADA" in x['Acción']]))

# Gráfico Principal
fig = go.Figure()
fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Precio"))
fig.add_trace(go.Scatter(x=data.index, y=data['MA10'], line=dict(color='yellow', width=1), name="MA10"))
fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='cyan', width=1), name="MA20"))
fig.update_layout(xaxis_rangeslider_visible=False, height=600)
st.plotly_chart(fig, use_container_width=True)

# Tabla de Historial
st.subheader("📝 Bitácora Detallada")
if log_eventos:
    st.dataframe(pd.DataFrame(log_eventos), use_container_width=True)
else:
    st.warning("No se encontraron trades con la configuración actual.")

