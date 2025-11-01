import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'

# --- Importações Essenciais ---
import streamlit as st

# Importa as funções de cada página
from view.login import login_page

from view.main import main_screen

# --- Bloco de Execução Principal (Roteador) ---

# Inicializa o estado da sessão se não existir
if "welcome_seen" not in st.session_state:
    st.session_state.welcome_seen = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Controla qual página é exibida
if not st.session_state.logged_in:
    login_page()
else:
    main_screen()
