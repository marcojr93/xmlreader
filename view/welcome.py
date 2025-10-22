from view.main import extrair_dados_xml
import streamlit as st
from io import BytesIO
import pandas as pd
from view.login import login_page

# ==============================
# STREAMLIT INTERFACE
# ==============================
def welcome_screen():

    # Centraliza o botão
    _ , btn_col, _ = st.columns([2.5, 1, 2.5])
    with btn_col:
        if st.button("Entrar", use_container_width=True, type="primary"):
            st.session_state.welcome_seen = True
            st.rerun()
    
    st.markdown(" ") # Espaçamento
    
    with st.expander("📖 Como Usar (Clique para expandir)"):
        st.markdown("""
         Utilize uma chave API-KEY do Gemini para autenticar seu acesso. 
        """)