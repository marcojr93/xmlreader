import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'

# --- Importações Essenciais ---
import streamlit as st

# Importa as funções de cada página
from view.login import login_page
from view.main import welcome_screen

# --- Bloco de Execução Principal (Roteador) ---

# Inicializa o estado da sessão se não existir
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Controla qual página é exibida
if not st.session_state.logged_in:
    login_page()  # Se não logado, vai para login
else:
    welcome_screen()  # Se logado, vai para tela principal
