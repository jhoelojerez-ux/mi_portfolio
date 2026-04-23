import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Analizador de Portafolio Pro", layout="wide")

st.title("🚀 Optimización de Portafolio: Frontera Eficiente")
st.markdown("Identificación del Portafolio de Mínima Varianza y Máximo Sharpe.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración")
tickers_input = st.sidebar.text_input("Empresas (tickers)", "NVDA, GS, MRK, NFLX, CAT")
start_date = st.sidebar.date_input("Fecha de inicio", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("Fecha de fin", pd.to_datetime("2023-12-31"))

tickers = [t.strip().upper() for t in tickers_input.split(",")]

if st.sidebar.button("Ejecutar Análisis"):
    try:
        with st.spinner('Calculando...'):
            data = yf.download(tickers, start=start_date, end=end_date)['Close']
        
        if data.empty:
            st.error("No hay datos. Revisa los tickers.")
        else:
            # 1. Cálculos Base
            retornos = data.pct_change().dropna()
            media_ret = retornos.mean() * 252
            matriz_cov = retornos.cov() * 252

            # 2. Simulación de Monte Carlo (1000 portafolios)
            num_portfolios = 2000
            resultados = np.zeros((3, num_portfolios))
            pesos_record = []

            for i in range(num_portfolios):
                pesos = np.random.random(len(tickers))
                pesos /= np.sum(pesos)
                pesos_record.append(pesos)
                
                ret_p = np.dot(pesos, media_ret)
                vol_p = np.sqrt(np.dot(pesos.T, np.dot(matriz_cov, pesos)))
                
                resultados[0,i] = ret_p
                resultados[1,i] = vol_p
                resultados[2,i] = ret_p / vol_p # Sharpe Ratio

            # --- IDENTIFICACIÓN DE PUNTOS CLAVE ---
            # 1. Máximo Sharpe (El más eficiente)
            idx_max_sharpe = resultados[2].argmax()
            ret_max_s, vol_max_s = resultados[0, idx_max_sharpe], resultados[1, idx_max_sharpe]

            # 2. Mínima Varianza (El de menor riesgo)
            idx_min_var = resultados[1].argmin()
            ret_min_v, vol_min_v = resultados[0, idx_min_var], resultados[1, idx_min_var]

            # --- VISUALIZACIÓN ---
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Frontera Eficiente")
                fig, ax = plt.subplots(figsize=(10, 6))
                plt.style.use('dark_background')
                
                # Nube de portafolios
                scatter = ax.scatter(resultados[1,:], resultados[0,:], c=resultados[2,:], cmap='viridis', alpha=0.5)
                plt.colorbar(scatter, label='Sharpe Ratio')
                
                # Marcar Mínima Varianza (ESTRELLA ROJA)
                ax.scatter(vol_min_v, ret_min_v, color='red', marker='*', s=200, label='Mínima Varianza')
                
                # Marcar Máximo Sharpe (X BLANCA)
                ax.scatter(vol_max_s, ret_max_s, color='white', marker='X', s=150, label='Máximo Sharpe')
                
                ax.set_xlabel('Volatilidad (Riesgo)')
                ax.set_ylabel('Retorno Esperado')
                ax.legend()
                st.pyplot(fig)

            with col2:
                st.subheader("📍 Portafolio Mínima Varianza")
                st.metric("Riesgo Mínimo", f"{vol_min_v*100:.2f}%")
                st.metric("Retorno Esperado", f"{ret_min_v*100:.2f}%")
                
                st.write("**Composición óptima (Pesos):**")
                pesos_min_var = pd.DataFrame({'Activo': tickers, 'Peso': pesos_record[idx_min_var]})
                st.dataframe(pesos_min_var.style.format({'Peso': '{:.2%}'}))

            st.divider()
            st.info("💡 La **Estrella Roja** representa la combinación de activos que tiene el menor riesgo posible (Mínima Varianza)".)
