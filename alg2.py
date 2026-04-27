import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Backtesting EUR/USD", layout="wide")

st.title("📊 Backtesting Estrategia EUR/USD")
st.sidebar.header("Parámetros Iniciales")

# 1. Configuración de Capital
capital_inicial = 1000.0
st.sidebar.metric("Capital Inicial", f"${capital_inicial}")

# 2. Carga de Datos
@st.cache_data
def load_data():
    df = yf.download("EURUSD=X", period="2mo", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data()

# 3. Indicadores Técnicos
data['MA10'] = data['Close'].rolling(10).mean()
data['MA20'] = data['Close'].rolling(20).mean()
data['MA50'] = data['Close'].rolling(50).mean()
data['STD20'] = data['Close'].rolling(20).std()
data['Upper'] = data['MA20'] + (data['STD20'] * 2)
data['Lower'] = data['MA20'] - (data['STD20'] * 2)

# 4. Motor de Backtesting con PnL
log_eventos = []
balance = capital_inicial
posicion = None # Guarda: {'tipo': 'LONG'/'SHORT', 'precio_entrada': 0.0}

for i in range(50, len(data)):
    current_time = data.index[i]
    price = float(data['Close'].iloc[i])
    row = data.iloc[i]
    
    # Lógica de Entrada
    if posicion is None:
        if row['MA10'] > row['MA50'] and price >= row['Upper']:
            posicion = {'tipo': 'LONG', 'precio_entrada': price}
            log_eventos.append({"Fecha": current_time, "Acción": "COMPRA (Long)", "Precio": price, "Balance": f"${balance:.2f}"})
        elif row['MA10'] < row['MA50'] and price <= row['Lower']:
            posicion = {'tipo': 'SHORT', 'precio_entrada': price}
            log_eventos.append({"Fecha": current_time, "Acción": "VENTA (Short)", "Precio": price, "Balance": f"${balance:.2f}"})
            
    # Lógica de Salida y Cálculo de PnL
    elif posicion['tipo'] == 'LONG':
        if price < row['MA20']:
            pnl_pct = (price - posicion['precio_entrada']) / posicion['precio_entrada']
            ganancia_neta = balance * pnl_pct
            balance += ganancia_neta
            log_eventos.append({"Fecha": current_time, "Acción": "CIERRE COMPRA", "Precio": price, "Ganancia/Pérdida": f"${ganancia_neta:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None
            
    elif posicion['tipo'] == 'SHORT':
        if price > row['MA20']:
            # En corto ganas si el precio baja
            pnl_pct = (posicion['precio_entrada'] - price) / posicion['precio_entrada']
            ganancia_neta = balance * pnl_pct
            balance += ganancia_neta
            log_eventos.append({"Fecha": current_time, "Acción": "CIERRE VENTA", "Precio": price, "Ganancia/Pérdida": f"${ganancia_neta:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None

# 5. Dashboard de Resultados
col1, col2, col3 = st.columns(3)
col1.metric("Balance Final", f"${balance:.2f}")
col2.metric("Retorno Total", f"{((balance - capital_inicial) / capital_inicial) * 100:.2f}%")
col3.metric("Status", "Ganancia" if balance > capital_inicial else "Pérdida")

# 6. Gráfico
fig = go.Figure()
fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="EUR/USD"))
fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], line=dict(color='orange', width=1), name="MA50"))
fig.add_trace(go.Scatter(x=data.index, y=data['Upper'], line=dict(color='rgba(173, 216, 230, 0.5)', dash='dash'), name="Bollinger Sup"))
fig.add_trace(go.Scatter(x=data.index, y=data['Lower'], line=dict(color='rgba(173, 216, 230, 0.5)', dash='dash'), name="Bollinger Inf"))

st.plotly_chart(fig, use_container_width=True)

# 7. Tabla de Resultados
st.subheader("📋 Historial Detallado de Operaciones")
if log_eventos:
    st.table(pd.DataFrame(log_eventos))
