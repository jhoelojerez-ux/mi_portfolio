import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Forex Algo V2", layout="wide")

st.title("📊 Backtesting Pro: EUR/USD")
st.sidebar.header("Configuración de Riesgo")

capital_inicial = 1000.0
st.sidebar.metric("Capital Inicial", f"${capital_inicial}")

# 1. Carga y Limpieza de datos
@st.cache_data
def load_clean_data():
    df = yf.download("EURUSD=X", period="2mo", interval="1h")
    # Aplanar MultiIndex si existe
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # ELIMINAR GAPS: Quita filas donde no hubo mercado o hay NaNs
    df = df.dropna()
    return df

data = load_clean_data()

# 2. Indicadores (calculados sobre datos limpios)
data['MA10'] = data['Close'].rolling(10).mean()
data['MA20'] = data['Close'].rolling(20).mean()
data['MA50'] = data['Close'].rolling(50).mean()
data['STD20'] = data['Close'].rolling(20).std()
data['Upper'] = data['MA20'] + (data['STD20'] * 2)
data['Lower'] = data['MA20'] - (data['STD20'] * 2)

# Volvemos a limpiar por los NaNs que generan las medias al principio (los primeros 50 periodos)
data = data.dropna()

# 3. Motor de Trading con Stop Loss en Bandas
log_eventos = []
balance = capital_inicial
posicion = None 

for i in range(len(data)):
    current_time = data.index[i]
    price = float(data['Close'].iloc[i])
    row = data.iloc[i]
    
    if posicion is None:
        # ENTRADA
        if row['MA10'] > row['MA50'] and price >= row['Upper']:
            posicion = {'tipo': 'LONG', 'precio_entrada': price}
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA COMPRA", "Precio": price, "Detalle": "Cruce Alcista + Banda Sup", "Balance": f"${balance:.2f}"})
        elif row['MA10'] < row['MA50'] and price <= row['Lower']:
            posicion = {'tipo': 'SHORT', 'precio_entrada': price}
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA VENTA", "Precio": price, "Detalle": "Cruce Bajista + Banda Inf", "Balance": f"${balance:.2f}"})
            
    elif posicion['tipo'] == 'LONG':
        # SALIDA O STOP LOSS
        razon = ""
        if price <= row['Lower']: # STOP LOSS: Tocó la banda inferior
            razon = "STOP LOSS (Banda Inferior)"
        elif price < row['MA20']: # SALIDA NORMAL
            razon = "SALIDA (Cruce MA20)"
            
        if razon:
            pnl = (price - posicion['precio_entrada']) / posicion['precio_entrada']
            ganancia = balance * pnl
            balance += ganancia
            log_eventos.append({"Fecha": current_time, "Acción": razon, "Precio": price, "Ganancia/Pérdida": f"${ganancia:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None
            
    elif posicion['tipo'] == 'SHORT':
        # SALIDA O STOP LOSS
        razon = ""
        if price >= row['Upper']: # STOP LOSS: Tocó la banda superior
            razon = "STOP LOSS (Banda Superior)"
        elif price > row['MA20']: # SALIDA NORMAL
            razon = "SALIDA (Cruce MA20)"
            
        if razon:
            pnl = (posicion['precio_entrada'] - price) / posicion['precio_entrada']
            ganancia = balance * pnl
            balance += ganancia
            log_eventos.append({"Fecha": current_time, "Acción": razon, "Precio": price, "Ganancia/Pérdida": f"${ganancia:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None

# 4. Interfaz de Streamlit
col1, col2, col3 = st.columns(3)
col1.metric("Balance Final", f"${balance:.2f}")
col2.metric("Retorno", f"{((balance - capital_inicial) / capital_inicial) * 100:.2f}%")
col3.metric("Operaciones", len([x for x in log_eventos if "ENTRADA" in x['Acción']]))

# Gráfico con marcadores de Stop Loss
fig = go.Figure()
fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="EUR/USD"))
fig.add_trace(go.Scatter(x=data.index, y=data['Upper'], line=dict(color='red', width=1, dash='dot'), name="Banda SL (Upper)"))
fig.add_trace(go.Scatter(x=data.index, y=data['Lower'], line=dict(color='red', width=1, dash='dot'), name="Banda SL (Lower)"))
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Registro de Operaciones con Stop Loss")
st.dataframe(pd.DataFrame(log_eventos), use_container_width=True)
