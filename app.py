import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Analizador de Portafolio Pro", layout="wide")

st.title("🚀 Optimización de Portafolio Eficiente")
st.markdown("Basado en tu examen de optimización de activos.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración")
tickers_input = st.sidebar.text_input("Empresas (tickers)", "NVDA, GS, MRK, NFLX, CAT")
start_date = st.sidebar.date_input("Fecha de inicio", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("Fecha de fin", pd.to_datetime("2023-12-31"))

tickers = [t.strip().upper() for t in tickers_input.split(",")]

if st.sidebar.button("Ejecutar Análisis"):
    try:
        # 1. Descarga de datos
        with st.spinner('Descargando datos de Yahoo Finance...'):
            data = yf.download(tickers, start=start_date, end=end_date)['Close']
        
        if data.empty:
            st.error("No se encontraron datos. Revisa los tickers.")
        else:
            col1, col2 = st.columns(2)

            # 2. Rentabilidad y Riesgo
            retornos = data.pct_change().dropna()
            riesgo = retornos.std() * (252**0.5)
            rentabilidad_anual = (1 + retornos.mean())**252 - 1

            with col1:
                st.subheader("Rendimiento vs Riesgo")
                metrics_df = pd.DataFrame({
                    'Rendimiento Anual (%)': rentabilidad_anual * 100,
                    'Riesgo (Volatilidad) (%)': riesgo * 100
                })
                st.table(metrics_df)

            with col2:
                st.subheader("Correlación entre Activos")
                fig_corr, ax_corr = plt.subplots()
                sns.heatmap(retornos.corr(), annot=True, cmap='coolwarm', ax=ax_corr)
                st.pyplot(fig_corr)

            # 3. Frontera Eficiente (Simulación)
            st.divider()
            st.subheader("Simulación de la Frontera Eficiente")
            
            num_portfolios = 1000
            all_weights = np.zeros((num_portfolios, len(tickers)))
            ret_arr = np.zeros(num_portfolios)
            vol_arr = np.zeros(num_portfolios)
            sharpe_arr = np.zeros(num_portfolios)

            for ind in range(num_portfolios):
                weights = np.array(np.random.random(len(tickers)))
                weights = weights / np.sum(weights)
                all_weights[ind,:] = weights
                ret_arr[ind] = np.sum((retornos.mean() * weights) * 252)
                vol_arr[ind] = np.sqrt(np.dot(weights.T, np.dot(retornos.cov() * 252, weights)))
                sharpe_arr[ind] = ret_arr[ind]/vol_arr[ind]

            fig_fe, ax_fe = plt.subplots(figsize=(10, 6))
            scatter = ax_fe.scatter(vol_arr, ret_arr, c=sharpe_arr, cmap='viridis')
            plt.colorbar(scatter, label='Sharpe Ratio')
            ax_fe.set_xlabel('Volatilidad (Riesgo)')
            ax_fe.set_ylabel('Retorno Esperado')
            
            # Marcar el punto óptimo
            max_sr_idx = sharpe_arr.argmax()
            ax_fe.scatter(vol_arr[max_sr_idx], ret_arr[max_sr_idx], c='red', s=50, edgecolors='black', label="Máximo Sharpe")
            st.pyplot(fig_fe)

            st.success(f"Portafolio óptimo encontrado. El activo con mayor Sharpe ratio es {tickers[np.argmax(weights)]}")

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
else:
    st.info("Configura los parámetros a la izquierda y dale a 'Ejecutar'.")