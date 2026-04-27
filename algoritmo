import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Forex Algo-Backtester", layout="wide")

st.title("📊 EUR/USD Algo-Visualizer")
st.sidebar.header("Configuración")

# 1. Parámetros
symbol = "EURUSD=X"
periodo = st.sidebar.selectbox("Periodo", ["1mo", "2mo", "3mo"], index=1)
intervalo = "1h"

# 2. Descarga de Datos
@st.cache_data
def load_data(ticker, p, i):
    df = yf.download(ticker, period=p, interval=i)
    # Limpiar nombres de columnas si vienen como MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(symbol, periodo, intervalo)

# 3. Cálculo de Indicadores
data['MA10'] = data['Close'].rolling(10).mean()
data['MA20'] = data['Close'].rolling(20).mean()
data['MA50'] = data['Close'].rolling(50).mean()
data['STD20'] = data['Close'].rolling(20).std()
data['Upper'] = data['MA20'] + (data['STD20'] * 2)
data['Lower'] = data['MA20'] - (data['STD20'] * 2)

# 4. Lógica de Backtesting (Entradas y Salidas)
log_eventos = []
posicion = None  # None, 'LONG', 'SHORT'

for i in range(50, len(data)):
    current_time = data.index[i]
    price = data['Close'].iloc[i]
    row = data.iloc[i]
    
    if posicion is None:
        # Lógica de ENTRADA (MA10 vs MA50 + Bollinger)
        if row['MA10'] > row['MA50'] and price >= row['Upper']:
            posicion = 'LONG'
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA COMPRA", "Precio": price})
        elif row['MA10'] < row['MA50'] and price <= row['Lower']:
            posicion = 'SHORT'
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA VENTA", "Precio": price})
            
    elif posicion == 'LONG':
        # Lógica de SALIDA (Cuando cruza la MA20 hacia abajo)
        if price < row['MA20']:
            log_eventos.append({"Fecha": current_time, "Acción": "SALIDA COMPRA", "Precio": price})
            posicion = None
            
    elif posicion == 'SHORT':
        # Lógica de SALIDA (Cuando cruza la MA20 hacia arriba)
        if price > row['MA20']:
            log_eventos.append({"Fecha": current_time, "Acción": "SALIDA VENTA", "Precio": price})
            posicion = None

# 5. Visualización con Plotly
fig = go.Figure()

# Velas
fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], 
                low=data['Low'], close=data['Close'], name="EUR/USD"))

# Indicadores
fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], line=dict(color='orange', width=1.5), name="MA50"))
fig.add_trace(go.Scatter(x=data.index, y=data['Upper'], line=dict(color='gray', dash='dash'), name="Bollinger Superior"))
fig.add_trace(go.Scatter(x=data.index, y=data['Lower'], line=dict(color='gray', dash='dash'), name="Bollinger Inferior"))

# Marcar Entradas/Salidas en el gráfico
if log_eventos:
    ev_df = pd.DataFrame(log_eventos)
    fig.add_trace(go.Scatter(x=ev_df['Fecha'], y=ev_df['Precio'], mode='markers', 
                             marker=dict(size=12, symbol='star', color='yellow'), name="Hitos"))

st.plotly_chart(fig, use_container_width=True)

# 6. Tabla de Log de Operaciones
st.subheader("📋 Registro de Operaciones")
if log_eventos:
    st.dataframe(pd.DataFrame(log_eventos), use_container_width=True)
else:
    st.write("No se detectaron entradas en este periodo.")