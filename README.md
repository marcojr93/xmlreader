# CaaS - Compliance as a Service

Aplicação para análise e validação de documentos fiscais XML com inteligência artificial.

## 🚀 Funcionalidades

- **Extração de dados XML** de notas fiscais
- **Análise tributária automatizada** com IA (Google Gemini)
- **Validação de conformidade** fiscal
- **Criptografia de dados sensíveis** (CPF, CNPJ, valores)
- **Exportação em Excel/PDF**
- **Landing page** profissional
- **Sistema de login** seguro

## ⚡ Uso Rápido

1. **Execute o script:** `start.bat`
2. **Ou manualmente:**
   - Abra: `templates/landing_page.html`
   - Execute: `streamlit run app.py --server.port 8501`
3. **Clique "Entrar"** na landing page
4. **Faça login** com sua API Key do Google Gemini
5. **Upload do XML** e análise automática

## 📋 Requisitos

- Python 3.8+
- API Key do Google Gemini
- Navegador web

## 🔑 API Key

Obtenha gratuitamente em: [Google AI Studio](https://makersuite.google.com/app/apikey)

## �️ Tecnologias

- **Streamlit** - Interface web
- **Google Gemini** - IA para análise tributária
- **Cryptography** - Segurança de dados
- **Pandas/XML** - Processamento de dados

## 📁 Principais Arquivos

- `app.py` - Aplicação principal
- `templates/landing_page.html` - Página inicial
- `agents/` - Agentes de IA especializados
- `start.bat` - Script de inicialização