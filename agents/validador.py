"""
Validador Fiscal com LangChain
Sistema de análise fiscal que usa LLM para comparar dados da NFe com banco de regras fiscal.
Utiliza LangChain para orquestração e análise inteligente de conformidade tributária.
"""

import os
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Import do processador de criptografia
try:
    from criptografia import SecureDataProcessor
except Exception:
    class SecureDataProcessor:
        def __init__(self):
            pass
        def decrypt_sensitive_data(self, df: pd.DataFrame, fields_to_decrypt=None) -> pd.DataFrame:
            return df


class ValidadorFiscal:
    """
    Validador fiscal que usa LangChain e LLM para análise inteligente de conformidade.
    Compara dados da NFe com banco de regras fiscais usando AI.
    """

    def __init__(self):
        """Inicializa o validador fiscal com LangChain"""
        self.processor = SecureDataProcessor()
        self.banco_regras = {}
        self.llm = None
        self.chain = None
        
        # Modelos disponíveis para fallback
        self.modelos_disponiveis = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro", 
            "gemini-pro",
            "gemini-1.0-pro"
        ]
        
        # Carregar banco de regras e inicializar LLM
        self._carregar_banco_regras()
        self._inicializar_llm_chain()

    def _carregar_banco_regras(self):
        """Carrega o banco de regras fiscais do arquivo JSON na pasta assets"""
        try:
            arquivo_regras = os.path.join(os.path.dirname(__file__), '..', 'assets', 'banco_de_regras.json')
            
            if not os.path.exists(arquivo_regras):
                # Fallback para outros locais possíveis
                caminhos_alternativos = [
                    os.path.join(os.path.dirname(__file__), '..', 'banco_de_regras.json'),
                    os.path.join(os.path.dirname(__file__), 'banco_de_regras.json'),
                    'assets/banco_de_regras.json',
                    'banco_de_regras.json'
                ]
                
                for caminho in caminhos_alternativos:
                    if os.path.exists(caminho):
                        arquivo_regras = caminho
                        break
                        
            with open(arquivo_regras, 'r', encoding='utf-8') as f:
                self.banco_regras = json.load(f)
                print(f"✅ Banco de regras carregado: {arquivo_regras}")
                
        except Exception as e:
            print(f"⚠️ Erro ao carregar banco de regras: {e}")
            self.banco_regras = {"regras_fiscais": {}, "oportunidades": {}, "alertas": {}}

    def _inicializar_llm_chain(self):
        """Inicializa a LLM e cria a chain do LangChain"""
        try:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise Exception("GOOGLE_API_KEY não configurada")

            # Garantir versão da API
            os.environ.setdefault("GOOGLE_API_VERSION", "v1")

            # Testar modelos disponíveis
            for modelo in self.modelos_disponiveis:
                try:
                    test_llm = ChatGoogleGenerativeAI(
                        model=modelo,
                        google_api_key=api_key,
                        temperature=0.1,
                        max_output_tokens=8192
                    )
                    
                    # Teste simples
                    response = test_llm.invoke("OK")
                    if response and hasattr(response, 'content') and response.content:
                        self.llm = test_llm
                        print(f"✅ LLM inicializada: {modelo}")
                        break
                        
                except Exception as e:
                    print(f"⚠️ Modelo {modelo} indisponível: {str(e)[:100]}")
                    continue

            if not self.llm:
                raise Exception("Nenhum modelo Gemini disponível")

            # Criar parser e chain
            self._criar_chain()
            
        except Exception as e:
            print(f"❌ Erro ao inicializar LLM: {e}")
            self.llm = None
            self.chain = None

    def _criar_chain(self):
        """Cria a chain do LangChain com prompt estruturado"""
        
        # Template do prompt para análise fiscal
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em análise fiscal brasileira com profundo conhecimento em tributação de NFe.

Sua tarefa é analisar os dados da Nota Fiscal Eletrônica comparando com as regras fiscais fornecidas e identificar:
1. OPORTUNIDADES de otimização fiscal
2. DISCREPÂNCIAS ou não conformidades

BANCO DE REGRAS FISCAIS:
{banco_regras}

INSTRUÇÕES IMPORTANTES:
- Analise TODOS os produtos do DataFrame
- Compare alíquotas aplicadas vs. regras fiscais
- Identifique produtos sujeitos à substituição tributária
- Verifique adequação de CFOPs
- Analise regimes de PIS/COFINS
- Identifique benefícios fiscais aplicáveis
- Foque em oportunidades de redução da carga tributária
- Destaque não conformidades críticas

FORMATO DE RESPOSTA (JSON estrito):
{{
  "status": "sucesso|erro|parcial",
  "produtos_analisados": <número>,
  "oportunidades": [
    {{
      "tipo": "Categoria da oportunidade",
      "produto": "Nome/NCM do produto",
      "descricao": "Descrição da oportunidade",
      "impacto": "Estimativa do impacto",
      "acao_recomendada": "O que fazer"
    }}
  ],
  "discrepancias": [
    {{
      "tipo": "Categoria da discrepância", 
      "produto": "Nome/NCM do produto",
      "problema": "Descrição do problema",
      "gravidade": "Alta|Média|Baixa",
      "correcao": "Como corrigir"
    }}
  ],
  "resumo_executivo": "Resumo executivo em texto markdown",
  "detalhes_tecnicos": "Detalhes técnicos em texto markdown"
}}"""),
            ("human", """DADOS DA NOTA FISCAL PARA ANÁLISE:

CABEÇALHO DA NFe:
{dados_cabecalho}

PRODUTOS DA NFe:
{dados_produtos}

Analise estes dados contra as regras fiscais e forneça o resultado no formato JSON especificado.""")
        ])

        # Parser JSON simples
        parser = JsonOutputParser()
        
        # Criar chain
        self.chain = prompt_template | self.llm | parser

    def analisar_nfe(self, cabecalho_df: pd.DataFrame, produtos_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Método principal que analisa a NFe usando LangChain e LLM
        
        Args:
            cabecalho_df: DataFrame criptografado com dados do cabeçalho
            produtos_df: DataFrame criptografado com dados dos produtos
            
        Returns:
            dict: Resultado da análise com oportunidades e discrepâncias
        """
        try:
            if not self.chain:
                return self._erro_chain_nao_inicializada()

            # Descriptografar dados para análise
            cabecalho = self.processor.decrypt_sensitive_data(cabecalho_df)
            produtos = self.processor.decrypt_sensitive_data(produtos_df)
            
            # Preparar dados para o prompt
            dados_cabecalho = self._formatar_cabecalho(cabecalho)
            dados_produtos = self._formatar_produtos(produtos)
            banco_regras_str = json.dumps(self.banco_regras, ensure_ascii=False, indent=2)
            
            # Executar análise via LangChain
            resultado = self.chain.invoke({
                "banco_regras": banco_regras_str,
                "dados_cabecalho": dados_cabecalho,
                "dados_produtos": dados_produtos
            })
            
            # Processar resultado
            if isinstance(resultado, dict):
                resultado['banco_regras_carregado'] = bool(self.banco_regras.get('regras_fiscais'))
                resultado['modelo_utilizado'] = getattr(self.llm, 'model_name', 'gemini')
                
                # Gerar dropdown formatado
                resultado['resumo_dropdown'] = self._gerar_dropdown(resultado)
                
                return resultado
            else:
                return self._erro_formato_resposta(str(resultado))
                
        except Exception as e:
            return self._erro_analise(str(e))

    def _formatar_cabecalho(self, cabecalho_df: pd.DataFrame) -> str:
        """Formata dados do cabeçalho para o prompt"""
        if cabecalho_df.empty:
            return "Cabeçalho não disponível"
            
        cabecalho = cabecalho_df.iloc[0] if len(cabecalho_df) > 0 else {}
        
        info_relevante = []
        campos_importantes = ['CNPJ', 'UF', 'Natureza da Operação', 'CFOP', 'Data', 'Valor Total']
        
        for campo in campos_importantes:
            if campo in cabecalho and pd.notna(cabecalho[campo]):
                info_relevante.append(f"{campo}: {cabecalho[campo]}")
                
        return "\n".join(info_relevante) if info_relevante else "Dados básicos do cabeçalho"

    def _formatar_produtos(self, produtos_df: pd.DataFrame) -> str:
        """Formata dados dos produtos para o prompt (limitando tamanho)"""
        if produtos_df.empty:
            return "Nenhum produto encontrado"
            
        # Selecionar colunas mais relevantes para análise fiscal
        colunas_fiscais = [
            'Produto', 'NCM', 'CFOP', 'Quantidade', 'Valor Unitário', 'Valor Total',
            'Alíquota ICMS', 'Valor ICMS', 'Alíquota PIS', 'Valor PIS', 
            'Alíquota COFINS', 'Valor COFINS', 'Alíquota IPI', 'Valor IPI'
        ]
        
        # Filtrar colunas que existem no DataFrame
        colunas_existentes = [col for col in colunas_fiscais if col in produtos_df.columns]
        
        if not colunas_existentes:
            # Fallback para todas as colunas se nenhuma fiscal específica for encontrada
            colunas_existentes = list(produtos_df.columns)[:10]  # Limitar a 10 colunas
            
        # Limitar a 20 produtos para evitar prompt muito grande
        produtos_limitados = produtos_df[colunas_existentes].head(20)
        
        # Converter para string formatada
        resultado = f"Total de produtos: {len(produtos_df)}\n\n"
        resultado += "Primeiros produtos para análise:\n"
        resultado += produtos_limitados.to_string(index=False, max_cols=len(colunas_existentes))
        
        return resultado

    def _gerar_dropdown(self, resultado: Dict[str, Any]) -> str:
        """Gera relatório formatado para dropdown"""
        dropdown = "## 📊 RELATÓRIO DE ANÁLISE FISCAL\n\n"
        
        # Resumo geral
        status_emoji = {"sucesso": "✅", "erro": "❌", "parcial": "⚠️"}
        emoji = status_emoji.get(resultado.get('status', 'erro'), "❓")
        
        dropdown += f"**{emoji} Status:** {resultado.get('status', 'Desconhecido')}\n"
        dropdown += f"**📦 Produtos analisados:** {resultado.get('produtos_analisados', 0)}\n"
        dropdown += f"**🎯 Oportunidades:** {len(resultado.get('oportunidades', []))}\n"
        dropdown += f"**⚠️ Discrepâncias:** {len(resultado.get('discrepancias', []))}\n\n"
        
        # Resumo executivo
        if resultado.get('resumo_executivo'):
            dropdown += "### 📋 RESUMO EXECUTIVO\n\n"
            dropdown += resultado['resumo_executivo'] + "\n\n"
        
        # Oportunidades
        oportunidades = resultado.get('oportunidades', [])
        if oportunidades:
            dropdown += "### 🎯 OPORTUNIDADES IDENTIFICADAS\n\n"
            for i, oport in enumerate(oportunidades, 1):
                dropdown += f"**{i}. {oport.get('tipo', 'N/A')}**\n"
                dropdown += f"   • **Produto:** {oport.get('produto', 'N/A')}\n"
                dropdown += f"   • **Descrição:** {oport.get('descricao', 'N/A')}\n"
                dropdown += f"   • **Impacto:** {oport.get('impacto', 'N/A')}\n"
                dropdown += f"   • **Ação:** {oport.get('acao_recomendada', 'N/A')}\n\n"
        
        # Discrepâncias
        discrepancias = resultado.get('discrepancias', [])
        if discrepancias:
            dropdown += "### ⚠️ DISCREPÂNCIAS ENCONTRADAS\n\n"
            for i, disc in enumerate(discrepancias, 1):
                gravidade_emoji = {"Alta": "🔴", "Média": "🟡", "Baixa": "🟢"}
                emoji_grav = gravidade_emoji.get(disc.get('gravidade', 'Média'), "⚪")
                
                dropdown += f"**{i}. {disc.get('tipo', 'N/A')} {emoji_grav}**\n"
                dropdown += f"   • **Produto:** {disc.get('produto', 'N/A')}\n"
                dropdown += f"   • **Problema:** {disc.get('problema', 'N/A')}\n"
                dropdown += f"   • **Gravidade:** {disc.get('gravidade', 'N/A')}\n"
                dropdown += f"   • **Correção:** {disc.get('correcao', 'N/A')}\n\n"
        
        # Detalhes técnicos
        if resultado.get('detalhes_tecnicos'):
            dropdown += "### 🔧 DETALHES TÉCNICOS\n\n"
            dropdown += resultado['detalhes_tecnicos'] + "\n\n"
        
        if not oportunidades and not discrepancias:
            dropdown += "### ✅ CONFORMIDADE FISCAL\n\n"
            dropdown += "Não foram identificadas oportunidades significativas ou discrepâncias críticas na análise realizada.\n"
        
        return dropdown

    def _erro_chain_nao_inicializada(self) -> Dict[str, Any]:
        """Retorna erro quando chain não foi inicializada"""
        return {
            'status': 'erro',
            'produtos_analisados': 0,
            'oportunidades': [],
            'discrepancias': [],
            'resumo_dropdown': "❌ **Erro:** LLM não inicializada. Verifique a configuração da GOOGLE_API_KEY.",
            'banco_regras_carregado': bool(self.banco_regras.get('regras_fiscais')),
            'modelo_utilizado': 'N/A'
        }

    def _erro_formato_resposta(self, resposta: str) -> Dict[str, Any]:
        """Retorna erro de formato de resposta"""
        return {
            'status': 'erro',
            'produtos_analisados': 0,
            'oportunidades': [],
            'discrepancias': [],
            'resumo_dropdown': f"❌ **Erro de formato:** A LLM retornou resposta em formato inválido.\n\nResposta: {resposta[:500]}...",
            'banco_regras_carregado': bool(self.banco_regras.get('regras_fiscais')),
            'modelo_utilizado': getattr(self.llm, 'model_name', 'gemini') if self.llm else 'N/A'
        }

    def _erro_analise(self, erro: str) -> Dict[str, Any]:
        """Retorna erro geral de análise"""
        return {
            'status': 'erro',
            'produtos_analisados': 0,
            'oportunidades': [],
            'discrepancias': [],
            'resumo_dropdown': f"❌ **Erro na análise:** {erro}",
            'banco_regras_carregado': bool(self.banco_regras.get('regras_fiscais')),
            'modelo_utilizado': getattr(self.llm, 'model_name', 'gemini') if self.llm else 'N/A'
        }

    # Métodos de compatibilidade com código existente
    def buscar_regras_fiscais(self, cabecalho_df: pd.DataFrame, produtos_df: pd.DataFrame) -> Dict[str, Any]:
        """Alias para manter compatibilidade com código existente"""
        return self.analisar_nfe(cabecalho_df, produtos_df)

    def obter_regras_armazenadas(self) -> dict:
        """Retorna o banco de regras carregado"""
        return self.banco_regras

    def limpar_memoria_regras(self):
        """Método para compatibilidade - não necessário com LangChain"""
        pass


# Funções de conveniência para compatibilidade
def buscar_regras_fiscais_nfe(cabecalho_criptografado: pd.DataFrame, produtos_criptografados: pd.DataFrame) -> dict:
    """
    Função principal para análise fiscal usando LangChain
    
    Args:
        cabecalho_criptografado: DataFrame criptografado com cabeçalho
        produtos_criptografados: DataFrame criptografado com produtos
        
    Returns:
        dict: Resultado da análise fiscal
    """
    try:
        validador = ValidadorFiscal()
        return validador.analisar_nfe(cabecalho_criptografado, produtos_criptografados)
    except Exception as e:
        return {
            'status': 'erro',
            'produtos_analisados': 0,
            'oportunidades': [],
            'discrepancias': [],
            'resumo_dropdown': f"❌ **Erro crítico:** {str(e)}",
            'banco_regras_carregado': False,
            'modelo_utilizado': 'N/A'
        }


# Alias para compatibilidade
verificar_regras_fiscais_nfe = buscar_regras_fiscais_nfe


if __name__ == "__main__":
    print("🚀 Validador Fiscal com LangChain - Teste Local\n")
    
    # Teste básico
    cabecalho_teste = pd.DataFrame({
        'CNPJ': ['12345678000199'],
        'UF': ['SP'],
        'Natureza da Operação': ['Venda'],
        'CFOP': ['6102']
    })
    
    produtos_teste = pd.DataFrame({
        'Produto': ['Notebook Dell Inspiron', 'Medicamento Genérico'],
        'NCM': ['84713012', '30049099'],
        'CFOP': ['6102', '5102'],
        'Quantidade': [1, 10],
        'Valor Unitário': [3500.00, 25.50],
        'Alíquota ICMS': ['12%', '0%'],
        'Alíquota PIS': ['1.65%', '0%'],
        'Alíquota COFINS': ['7.6%', '0%']
    })
    
    # Executar análise
    resultado = buscar_regras_fiscais_nfe(cabecalho_teste, produtos_teste)
    
    print(f"📊 Status: {resultado['status']}")
    print(f"📦 Produtos analisados: {resultado['produtos_analisados']}")
    print(f"🎯 Oportunidades: {len(resultado['oportunidades'])}")
    print(f"⚠️ Discrepâncias: {len(resultado['discrepancias'])}")
    print(f"🤖 Modelo: {resultado.get('modelo_utilizado', 'N/A')}")
    print(f"📋 Banco de regras: {'✅' if resultado['banco_regras_carregado'] else '❌'}")
    
    print("\n" + "="*50)
    print("RELATÓRIO COMPLETO:")
    print("="*50)
    print(resultado['resumo_dropdown'])
