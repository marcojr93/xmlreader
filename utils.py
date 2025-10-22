# --- Importações Essenciais ---
import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
from google.api_core import exceptions


# --- Funções de Validação e Obtenção de Modelos ---
def validate_gemini_api_key(api_key):
    try:
        genai.configure(api_key=api_key)
        genai.list_models()
        return True
    except exceptions.PermissionDenied:
        st.error("Chave de API do Gemini inválida ou sem permissão.")
        return False
    except Exception as e:
        st.error(f"Ocorreu um erro ao validar a chave de API: {e}")
        return False

def get_gemini_models():
    try:
        return [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        st.warning(f"Não foi possível buscar modelos Gemini. Verifique a API Key. Erro: {e}")
        return []