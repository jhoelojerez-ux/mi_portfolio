import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="QuantAlgo Pro", layout="wide")

# --- CONFIGURACIÓN ---
st.sidebar.header("⚙️ Parámetros de Trading")
dict_activos = {"Euro / Dólar": "EURUSD=X", "Bitcoin": "BTC-USD", "Nvidia": "NVDA"}
seleccion = st.sidebar.selectbox("Activo", list(dict_activos.keys()))
ticker = dict_activos[seleccion]

saldo_inicial = st.sidebar.number_input("Saldo Inicial ($)", value=10000.0)
tamano_trade = st.sidebar.number_input("Tamaño Posición ($)", value=1000.0)

# Filtro Horario (Basado en hora UTC que usa Yahoo Finance)
st.sidebar.subheader("🕒 Filtro de Sesión")
solo_sesion = st.sidebar.checkbox("Solo Sesión Londres/NY (8:00 - 18:00 UTC)", value=True)

# --- DESCARGA Y DATOS ---
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
data['Upper'] = data['MA20'] + (data['STD20'] * 2)
data['Lower'] = data['MA20'] - (data['STD20'] * 2)
data = data.dropna()

# --- MOTOR DE BACKTESTING ---
log_eventos = []
balance = saldo_inicial
posicion = None
historial_balance = [saldo_inicial]

for i in range(len(data)):
    current_time = data.index[i]
    price = float(data['Close'].iloc[i])
    row = data.iloc[i]
    hora_actual = current_time.hour
    
    # Lógica de Entrada
    if posicion is None:
        # Aplicar filtro de hora si está activo
        puede_operar = True
        if solo_sesion and (hora_actual < 8 or hora_actual > 18):
            puede_operar = False
            
        if puede_operar:
            if row['MA10'] > row['MA20'] and price > row['MA20']:
                posicion = {'tipo': 'LONG', 'entrada': price, 'max_price': price}
                log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA LONG", "Precio": price})
            elif row['MA10'] < row['MA20'] and price < row['MA20']:
                posicion = {'tipo': 'SHORT', 'entrada': price, 'min_price': price}
                log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA SHORT", "Precio": price})

    # Lógica de Salida / Trailing Stop
    elif posicion:
        pnl = 0
        razon = ""
        
        if posicion['tipo'] == 'LONG':
            # Actualizar precio máximo para el trailing
            posicion['max_price'] = max(posicion['max_price'], price)
            # Si el precio cae un 1% desde el máximo alcanzado (Trailing Stop)
            if price < posicion['max_price'] * 0.995: 
                razon = "TRAILING STOP 🛡️"
            elif price <= row['Lower']:
                razon = "STOP LOSS 🛑"
            elif price < row['MA10']:
                razon = "SALIDA CRUCE 📉"
            
            if razon:
                pnl = tamano_trade * ((price - posicion['entrada']) / posicion['entrada'])
                
        elif posicion['tipo'] == 'SHORT':
            posicion['min_price'] = min(posicion['min_price'], price)
            if price > posicion['min_price'] * 1.005:
                razon = "TRAILING STOP 🛡️"
            elif price >= row['Upper']:
                razon = "STOP LOSS 🛑"
            elif price > row['MA10']:
                razon = "SALIDA CRUCE 📈"
            
            if razon:
                pnl = tamano_trade * ((posicion['entrada'] - price) / posicion['entrada'])

        if razon:
            balance += pnl
            log_eventos[-1].update({"Salida": current_time, "Razón": razon, "PnL": f"${pnl:.2f}", "Balance": balance})
            posicion = None
            
    historial_balance.append(balance)

# --- CÁLCULO DE MÉTRICAS (Drawdown) ---
df_balance = pd.Series(historial_balance)
max_previo = df_balance.cummax()
drawdowns = (df_balance - max_previo) / max_previo
max_drawdown = drawdowns.min() * 100

# --- INTERFAZ ---
st.title(f"📈 Dashboard de Rendimiento: {seleccion}")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Balance Final", f"${balance:.2f}")
m2.metric("Retorno Total", f"{((balance-saldo_inicial)/saldo_inicial)*100:.2f}%")
m3.metric("Max Drawdown", f"{max_drawdown:.2f}%", delta_color="inverse")
m4.metric("Trades", len(log_eventos))

# Gráfico de Curva de Capital
fig_balance = go.Figure()
fig_balance.add_trace(go.Scatter(x=list(range(len(historial_balance))), y=historial_balance, name="Equity Curve", fill='tozeroy'))
fig_balance.update_layout(title="Evolución del Capital ($)", height=400)
st.plotly_chart(fig_balance, use_container_width=True)

st.subheader("📝 Historial de Operaciones")
st.dataframe(pd.DataFrame(log_eventos), use_container_width=True)
