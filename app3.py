import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Portfolio Pro Analysis", layout="wide")

st.title("📊 Análisis de Portafolio Avanzado")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración")
tickers_input = st.sidebar.text_input("Empresas", "NVDA, GS, MRK, NFLX, CAT")
start_date = st.sidebar.date_input("Inicio", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("Fin", pd.to_datetime("2023-12-31"))

tickers = [t.strip().upper() for t in tickers_input.split(",")]

if st.sidebar.button("Calcular"):
    try:
        with st.spinner('Obteniendo datos...'):
            # Descarga de activos + Tasa Libre de Riesgo (^IRX es el T-Bill de 13 semanas)
            data = yf.download(tickers, start=start_date, end=end_date)['Close']
            rf_data = yf.download("^IRX", start=start_date, end=end_date)['Close']
            
            # Tasa libre de riesgo promedio anualizada (dividida por 100 porque viene en %)
            rf_rate = (rf_data.mean().values[0] / 100) if not rf_data.empty else 0.04

        if data.empty:
            st.error("No hay datos disponibles.")
        else:
            # 1. Cálculos de Retornos
            retornos = data.pct_change().dropna()
            media_ret = retornos.mean() * 252
            matriz_cov = retornos.cov() * 252
            correlacion = retornos.corr()

            # 2. Simulación de Monte Carlo
            num_portfolios = 2500
            np.random.seed(42) # Para que no cambie al refrescar
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
                # Sharpe Ratio Realista: (Retorno - RiskFree) / Volatilidad
                resultados[2,i] = (ret_p - rf_rate) / vol_p

            # Índices clave
            idx_max_sharpe = resultados[2].argmax()
            idx_min_var = resultados[1].argmin()

            # --- DISEÑO DE LA APP ---
            
            # Fila 1: Métricas y Matriz de Correlación
            col_m1, col_m2 = st.columns([1, 1])
            
            with col_m1:
                st.subheader("📋 Matriz de Correlación")
                fig_corr, ax_corr = plt.subplots(figsize=(8, 6))
                sns.heatmap(correlacion, annot=True, cmap='RdYlGn', ax=ax_corr, center=0)
                st.pyplot(fig_corr)
                st.caption(f"Tasa Libre de Riesgo utilizada ($R_f$): {rf_rate*100:.2f}% (Basada en ^IRX)")

            with col_m2:
                st.subheader("📍 Comparación de Portafolios")
                res_df = pd.DataFrame({
                    "Métrica": ["Retorno Anual", "Volatilidad", "Sharpe Ratio"],
                    "Mín. Varianza (⭐)": [f"{resultados[0,idx_min_var]*100:.2f}%", f"{resultados[1,idx_min_var]*100:.2f}%", f"{resultados[2,idx_min_var]:.2f}"],
                    "Máx. Sharpe (X)": [f"{resultados[0,idx_max_sharpe]*100:.2f}%", f"{resultados[1,idx_max_sharpe]*100:.2f}%", f"{resultados[2,idx_max_sharpe]:.2f}"]
                })
                st.table(res_df.set_index("Métrica"))

            # Fila 2: Gráfica de Frontera Eficiente
            st.divider()
            st.subheader("📈 Frontera Eficiente de Markowitz")
            fig_fe, ax_fe = plt.subplots(figsize=(12, 6))
            plt.style.use('dark_background')
            
            scatter = ax_fe.scatter(resultados[1,:], resultados[0,:], c=resultados[2,:], cmap='viridis', alpha=0.4)
            plt.colorbar(scatter, label='Sharpe Ratio')
            
            # Estrella Roja: Mínima Varianza
            ax_fe.scatter(resultados[1,idx_min_var], resultados[0,idx_min_var], color='red', marker='*', s=250, label='Mínima Varianza')
            # X Blanca: Máximo Sharpe
            ax_fe.scatter(resultados[1,idx_max_sharpe], resultados[0,idx_max_sharpe], color='white', marker='X', s=200, label='Máximo Sharpe')
            
            ax_fe.set_xlabel('Riesgo (Volatilidad)')
            ax_fe.set_ylabel('Retorno Esperado')
            ax_fe.legend()
            st.pyplot(fig_fe)

            # Fila 3: Composición de Pesos
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Pesos Mínima Varianza**")
                st.dataframe(pd.DataFrame({'Activo': tickers, 'Peso': pesos_record[idx_min_var]}).set_index('Activo').style.format('{:.2%}'))
            with c2:
                st.write("**Pesos Máximo Sharpe**")
                st.dataframe(pd.DataFrame({'Activo': tickers, 'Peso': pesos_record[idx_max_sharpe]}).set_index('Activo').style.format('{:.2%}'))

    except Exception as e:
        st.error(f"Error: {e}")