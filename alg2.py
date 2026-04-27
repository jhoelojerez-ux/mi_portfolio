import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Forex Backtest 1Y", layout="wide")

st.title("📈 Backtesting EUR/USD - Temporalidad 3H")
st.sidebar.header("Configuración de Cuenta")

# 1. Parámetros de la simulación
saldo_inicial = 10000.0
tamano_trade = 200.0 # Cantidad fija por operación
st.sidebar.metric("Saldo Inicial", f"${saldo_inicial}")
st.sidebar.metric("Riesgo por Trade", f"${tamano_trade}")

# 2. Carga de Datos (1 año)
@st.cache_data
def load_year_data():
    # Bajamos datos de 1 hora para luego agruparlos en 3 horas
    df = yf.download("EURUSD=X", period="1y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Resample a 3 horas (esto limpia y agrupa automáticamente)
    # OHLC: Open=First, High=Max, Low=Min, Close=Last
    df_3h = df.resample('3h').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last'
    }).dropna()
    return df_3h

data = load_year_data()

# 3. Indicadores (sobre el dataset de 3 horas)
data['MA10'] = data['Close'].rolling(10).mean()
data['MA20'] = data['Close'].rolling(20).mean()
data['MA50'] = data['Close'].rolling(50).mean()
data['STD20'] = data['Close'].rolling(20).std()
data['Upper'] = data['MA20'] + (data['STD20'] * 2)
data['Lower'] = data['MA20'] - (data['STD20'] * 2)
data = data.dropna()

# 4. Simulación (Trade Fijo de $200)
log_eventos = []
balance = saldo_inicial
posicion = None

for i in range(len(data)):
    current_time = data.index[i]
    price = float(data['Close'].iloc[i])
    row = data.iloc[i]
    
    if posicion is None:
        if row['MA10'] > row['MA50'] and price >= row['Upper']:
            posicion = {'tipo': 'LONG', 'entrada': price}
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA LONG", "Precio": price, "Balance": f"${balance:.2f}"})
        elif row['MA10'] < row['MA50'] and price <= row['Lower']:
            posicion = {'tipo': 'SHORT', 'entrada': price}
            log_eventos.append({"Fecha": current_time, "Acción": "ENTRADA SHORT", "Precio": price, "Balance": f"${balance:.2f}"})
            
    elif posicion['tipo'] == 'LONG':
        # Salida o Stop Loss
        razon = ""
        if price <= row['Lower']: razon = "STOP LOSS (Banda Inf)"
        elif price < row['MA20']: razon = "SALIDA (Cruce MA20)"
        
        if razon:
            # Ganancia = $200 * variación porcentual
            pnl_operacion = tamano_trade * ((price - posicion['entrada']) / posicion['entrada'])
            balance += pnl_operacion
            log_eventos.append({"Fecha": current_time, "Acción": razon, "Precio": price, "PnL": f"${pnl_operacion:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None
            
    elif posicion['tipo'] == 'SHORT':
        razon = ""
        if price >= row['Upper']: razon = "STOP LOSS (Banda Sup)"
        elif price > row['MA20']: razon = "SALIDA (Cruce MA20)"
        
        if razon:
            pnl_operacion = tamano_trade * ((posicion['entrada'] - price) / posicion['entrada'])
            balance += pnl_operacion
            log_eventos.append({"Fecha": current_time, "Acción": razon, "Precio": price, "PnL": f"${pnl_operacion:.2f}", "Balance": f"${balance:.2f}"})
            posicion = None

# 5. Interfaz Visual
c1, c2, c3 = st.columns(3)
c1.metric("Balance Actual", f"${balance:.2f}")
c2.metric("Ganancia Total", f"${balance - saldo_inicial:.2f}")
c3.metric("N° Operaciones", len([x for x in log_eventos if "ENTRADA" in x['Acción']]))

# Gráfico
fig = go.Figure()
fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="EUR/USD 3H"))
fig.add_trace(go.Scatter(x=data.index, y=data['MA10'], line=dict(color='blue', width=1), name="MA10"))
fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], line=dict(color='orange', width=1), name="MA50"))
st.plotly_chart(fig, use_container_width=True)

st.subheader("📝 Bitácora de Trades")
st.dataframe(pd.DataFrame(log_eventos), use_container_width=True)
