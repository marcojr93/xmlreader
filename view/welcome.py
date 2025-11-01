
import streamlit as st
from io import BytesIO
import pandas as pd
from view.login import login_page

# ==============================
# STREAMLIT INTERFACE
# ==============================

def card(title, description):
    st.markdown(f"""
    <div style="border: 1px solid #e6e6e6; border-radius: 5px; padding: 20px; margin: 10px 0px; box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);">
        <h4>{title}</h4>
        <p>{description}</p>
    </div>
    """, unsafe_allow_html=True)

def welcome_screen():
    st.set_page_config(layout="wide")
    
    col1, col2, col3 = st.columns([2,1,2])
    with col2:
        st.image("assets/LOGO.png", width=300)

    st.markdown("<h2 style='text-align: center;'>Bem-vindo ao CaaS - Compliance as a Service</h2>", unsafe_allow_html=True)
    
    st.markdown("<p style='font-size: 0.9rem; text-align: center;'>Este sistema foi projetado para facilitar a análise e validação de documentos fiscais em formato XML. Utilizando inteligência artificial, a ferramenta extrai, analisa e valida os dados para garantir a conformidade fiscal.</p>", unsafe_allow_html=True)

    st.markdown("<h3 style='text-align: center;'>Funcionalidades</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        card("Extração de Dados", "Carregue um arquivo XML para extrair as informações fiscais.")
        card("Validação de Regras", "O sistema valida os documentos com base em um conjunto de regras fiscais.")
    with col2:
        card("Análise Tributária", "A IA analisa os dados extraídos para identificar possíveis inconsistências.")
        card("Geração de Relatórios", "Exporte os resultados da análise em formato Excel.")


    st.markdown("<br>", unsafe_allow_html=True)
    # Centraliza o botão
    _ , btn_col, _ = st.columns([2, 1, 2])
    with btn_col:
        if st.button("Entrar", use_container_width=True, type="primary"):
            st.session_state.welcome_seen = True
            st.rerun()

    