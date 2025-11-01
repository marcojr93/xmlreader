# --- Importações Essenciais ---
import streamlit as st
import os
import base64
from io import BytesIO
import pandas as pd
from utils import validate_gemini_api_key

def login_page():
    st.set_page_config(page_title="Login - CaaS", layout="centered")
    
    # Centraliza a logo
    col1, col2, col3 = st.columns([2.5, 2, 2.5])
    with col2:
        st.image("assets/LOGO.png", width=200)

    """Exibe a página de login em um layout centralizado."""
    _, col, _ = st.columns([2, 1, 2])

    name = st.text_input("Seu Nome", key="login_name")
    password = st.text_input("Insira sua API Key do Gemini", type="password", key="login_password")
    
    if st.button("Login", use_container_width=True, type="primary"):
        if name and password:
            if validate_gemini_api_key(password):
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = name
                os.environ["GOOGLE_API_KEY"] = password
                st.success("Login bem-sucedido!")
                st.rerun()
        else:
            st.error("Por favor, insira seu nome e a API Key.")
