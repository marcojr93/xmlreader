# 📄 XML Reader - Leitor de Arquivos SPED e NF-e

Uma aplicação web segura construída com Streamlit para ler e extrair informações de arquivos Notas Fiscais Eletrônicas (.xml), com sistema de autenticação e configuração de LLM.

## 🚀 Funcionalidades

- **Leitura de arquivos SPED Fiscal (.txt)**: Extrai registros e campos dos blocos SPED
- **Leitura de arquivos NF-e (.xml)**: Extrai informações principais como:
  - Dados do emitente e destinatário
  - Informações da nota fiscal (número, série, data)
  - Lista de produtos/itens
  - Totais e valores

### 🔒 **Criptografia de Dados Sensíveis**
- **Proteção automática** de CPFs, CNPJs, valores financeiros
- **Guardrails contra injection** (XSS, SQL, Command injection)
- **Sistema de hash** para busca sem descriptografar
- **Auditoria completa** de operações de segurança

### 💾 **Exportação e Visualização**
- **Exportação para CSV/Excel**: Download dos dados extraídos
- **Visualização protegida**: Dados mascarados para segurança
- **Interface web intuitiva**: Upload de arquivos via drag-and-drop

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes do Python)
- **API Key** de um dos provedores suportados:
  - OpenAI (GPT-4o, GPT-4-turbo, GPT-3.5-turbo)
  - Google Gemini (Gemini-1.5-pro, Gemini-1.5-flash)

## 🔧 Instalação

1. Clone ou baixe este projeto
2. Navegue até o diretório do projeto
3. Instale as dependências:

```bash
pip install -r requirements.txt
```

## ▶️ Como usar

### **1. Sistema de Login (BYOK - Bring Your Own Key)**

```bash
streamlit run login.py
```

1. **Configure sua identidade**: Digite seu nome
2. **Escolha o provider de LLM**: OpenAI ou Google Gemini
3. **Insira sua API Key**: Sua chave pessoal
4. **Validação automática**: Sistema detecta o melhor modelo
5. **Acesse a aplicação**: Redirecionamento automático

### **2. Aplicação Principal**

Após o login, você será redirecionado automaticamente para:

```bash
streamlit run main.py
```

1. **Faça upload** de um arquivo `.txt` (SPED) ou `.xml` (NF-e)
2. **Visualize os dados** extraídos com proteção de dados sensíveis
3. **Configure visualização**: Escolha entre dados mascarados, criptografados ou relatório de segurança
4. **Baixe os resultados** em formato Excel com dados protegidos

## 🔑 Configuração de API Keys

### **OpenAI**
- Acesse: [OpenAI Platform](https://platform.openai.com/api-keys)
- Crie uma nova API Key
- Modelos suportados: GPT-4o, GPT-4-turbo, GPT-3.5-turbo

### **Google Gemini**
- Acesse: [Google AI Studio](https://makersuite.google.com/app/apikey)
- Gere uma nova API Key
- Modelos suportados: Gemini-1.5-pro, Gemini-1.5-flash

## 📁 Estrutura do Projeto

```
XML reader/
├── login.py             # Sistema de login e configuração LLM
├── main.py              # Aplicação principal (protegida)
├── criptografia.py      # Sistema de criptografia e segurança
├── auth_utils.py        # Utilitários de autenticação
├── requirements.txt     # Dependências do projeto
├── README.md           # Este arquivo
├── LOGIN_GUIDE.md      # Guia detalhado do sistema de login
└── DB_NFe/             # Pasta com arquivos XML de exemplo
```

## 🛠️ Tecnologias Utilizadas

- **Streamlit**: Framework para aplicações web em Python
- **Pandas**: Manipulação e análise de dados
- **xml.etree.ElementTree**: Processamento de arquivos XML
- **Cryptography**: Criptografia de dados sensíveis
- **LangChain**: Integração unificada com LLMs
- **OpenAI API**: Integração com modelos GPT (via LangChain)
- **Google Generative AI**: Integração com Gemini (via LangChain)

