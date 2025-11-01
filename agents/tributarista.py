"""
Tributarista Fiscal - Cálculo de Delta de Impostos e Multas
Sistema especializado em calcular diferenças entre impostos pagos vs devidos,
possibilidade de multas e apresentar resultados em formato híbrido (tabelas + texto).
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


class TributaristaFiscal:
    """
    Tributarista fiscal especializado em cálculos de delta de impostos e multas.
    Usa conhecimento da nuvem para calcular diferenças tributárias e possíveis penalidades.
    """

    def __init__(self):
        """Inicializa o tributarista fiscal com LangChain"""
        self.processor = SecureDataProcessor()
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
        
        # Inicializar LLM
        self._inicializar_llm_chain()

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
                        print(f"LLM Tributarista inicializada: {modelo}")
                        break
                        
                except Exception as e:
                    print(f"Modelo {modelo} indisponível: {str(e)[:100]}")
                    continue

            if not self.llm:
                raise Exception("Nenhum modelo Gemini disponível")

            # Criar parser e chain
            self._criar_chain()
            
        except Exception as e:
            print(f"Erro ao inicializar LLM Tributarista: {e}")
            self.llm = None
            self.chain = None

    def _criar_chain(self):
        """Cria a chain do LangChain com prompt especializado em cálculos tributários"""
        
        # Template do prompt para cálculos tributários
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Você é um TRIBUTARISTA ESPECIALISTA em cálculos fiscais com profundo conhecimento em:
- Cálculo de impostos federais, estaduais e municipais
- Multas e penalidades por infrações fiscais
- Regime de tributação LUCRO REAL
- Legislação tributária brasileira atualizada

Sua missão é realizar CÁLCULOS PRECISOS de:
1. DELTA de impostos: Diferença entre o que foi pago vs. o que deveria ser pago
2. MULTAS POTENCIAIS: Cálculo de multas por má aplicação ou não recolhimento
3. ANÁLISE QUANTITATIVA: Apresentar resultados em formato híbrido (tabelas + texto)

CONTEXTO IMPORTANTE:
- REGIME: LUCRO REAL (sempre considerar este regime)
- FOCO: Cálculos matemáticos precisos de impostos e multas
- FONTE: Legislação tributária atual e tabelas de multas vigentes
- DADOS: Trabalhe com dados criptografados mantendo precisão nos cálculos

INSTRUÇÕES PARA CÁLCULOS:
1. Calcule EXATAMENTE o que deveria ser pago conforme legislação atual
2. Compare com o que foi efetivamente recolhido/declarado
3. Identifique diferenças (para mais ou para menos)
4. Calcule multas conforme tabelas vigentes
5. Apresente resultados em formato tabular sempre que possível
6. Use fórmulas e percentuais corretos da legislação

TIPOS DE IMPOSTOS A CALCULAR:
- ICMS (incluindo ST e DIFAL)
- PIS/COFINS (Lucro Real - não cumulativo)
- IPI (quando aplicável)
- Contribuições federais
- Multas por atraso, inexatidão ou sonegação

FORMATO DE RESPOSTA (JSON estrito):
{{
  "status": "sucesso|erro|parcial",
  "regime_tributario": "LUCRO REAL",
  "impostos_analisados": <número>,
  "delta_impostos": {{
    "icms": {{
      "valor_pago": <número>,
      "valor_devido": <número>,
      "delta": <número>,
      "percentual_diferenca": <número>,
      "observacoes": "texto explicativo"
    }},
    "pis_cofins": {{
      "pis_pago": <número>,
      "pis_devido": <número>,
      "cofins_pago": <número>,
      "cofins_devido": <número>,
      "delta_total": <número>,
      "observacoes": "texto explicativo"
    }},
    "ipi": {{
      "valor_pago": <número>,
      "valor_devido": <número>,
      "delta": <número>,
      "observacoes": "texto explicativo"
    }}
  }},
  "calculo_multas": {{
    "multas_potenciais": [
      {{
        "tipo_infracao": "Descrição da infração",
        "base_calculo": <número>,
        "percentual_multa": <número>,
        "valor_multa": <número>,
        "base_legal": "Artigo e lei aplicável",
        "prazo_regularizacao": "prazo em dias"
      }}
    ],
    "total_multas": <número>,
    "multa_minima": <número>,
    "multa_maxima": <número>
  }},
  "tabela_resumo": {{
    "cabecalho": ["Imposto", "Pago", "Devido", "Delta", "% Diferença"],
    "linhas": [
      ["ICMS", "valor", "valor", "valor", "percentual"],
      ["PIS", "valor", "valor", "valor", "percentual"],
      ["COFINS", "valor", "valor", "valor", "percentual"]
    ]
  }},
  "analise_riscos": {{
    "risco_autuacao": "Alto|Médio|Baixo",
    "valor_total_exposicao": <número>,
    "recomendacoes_urgentes": ["lista de ações"],
    "prazos_criticos": ["lista de prazos"]
  }},
  "resumo_executivo": "Resumo dos cálculos em texto markdown",
  "detalhes_tecnicos": "Metodologia de cálculo e fórmulas aplicadas",
  "limitacoes_calculo": "Limitações encontradas para cálculos precisos"
}}"""),
            ("human", """DADOS PARA CÁLCULO DE DELTA TRIBUTÁRIO:

IMPORTANTE: Dados criptografados - mantenha precisão nos cálculos focando em valores e alíquotas.

CABEÇALHO DA NFe (CRIPTOGRAFADO):
{dados_cabecalho}

PRODUTOS DA NFe (CRIPTOGRAFADOS):
{dados_produtos}

INSIGHTS DO ANALISTA FISCAL:
{resultado_analista}

DISCREPÂNCIAS IDENTIFICADAS:
{discrepancias_validador}

OPORTUNIDADES IDENTIFICADAS:
{oportunidades_validador}

INSTRUÇÕES ESPECÍFICAS PARA CÁLCULOS:

1. DELTA DE IMPOSTOS:
   - Extraia valores pagos de impostos dos dados da NFe
   - Calcule valores corretos conforme legislação atual
   - Determine diferenças absolutas e percentuais
   - Identifique se há sub ou super recolhimento

2. CÁLCULO DE MULTAS:
   - Use tabelas de multas vigentes
   - Considere diferentes tipos de infrações
   - Calcule multas mínimas e máximas
   - Inclua juros de mora quando aplicável

3. APRESENTAÇÃO DE RESULTADOS:
   - Priorize formato tabular para valores
   - Use texto explicativo para contexto
   - Mantenha precisão de 2 casas decimais
   - Indique base legal dos cálculos

Realize os cálculos considerando regime de LUCRO REAL e apresente resultados em formato híbrido conforme especificado.""")
        ])

        # Parser JSON
        parser = JsonOutputParser()
        
        # Criar chain
        self.chain = prompt_template | self.llm | parser

    def calcular_delta_impostos(self, 
                               cabecalho_df: pd.DataFrame, 
                               produtos_df: pd.DataFrame, 
                               resultado_analista: Dict[str, Any],
                               resultado_validador: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método principal que calcula delta de impostos e multas usando LLM
        
        Args:
            cabecalho_df: DataFrame criptografado com dados do cabeçalho
            produtos_df: DataFrame criptografado com dados dos produtos
            resultado_analista: Resultado completo do analista com insights
            resultado_validador: Resultado do validador com discrepâncias
            
        Returns:
            dict: Resultado dos cálculos tributários com tabelas e análises
        """
        try:
            if not self.chain:
                return self._erro_chain_nao_inicializada()

            # Usar dados CRIPTOGRAFADOS para cálculos (mantém segurança)
            cabecalho = cabecalho_df
            produtos = produtos_df
            
            print(f"🧮 Tributarista - Calculando delta com dados CRIPTOGRAFADOS")
            print(f"   Cabecalho shape: {cabecalho.shape if not cabecalho.empty else 'Vazio'}")
            print(f"   Produtos shape: {produtos.shape if not produtos.empty else 'Vazio'}")
            
            # Preparar dados criptografados para o prompt
            dados_cabecalho = self._formatar_cabecalho_para_calculo(cabecalho)
            dados_produtos = self._formatar_produtos_para_calculo(produtos)
            insights_analista = self._formatar_insights_analista(resultado_analista)
            discrepancias_formatadas = self._formatar_discrepancias(resultado_validador.get('discrepancias', []))
            oportunidades_formatadas = self._formatar_oportunidades(resultado_validador.get('oportunidades', []))
            
            # Executar cálculos via LangChain
            resultado = self.chain.invoke({
                "dados_cabecalho": dados_cabecalho,
                "dados_produtos": dados_produtos,
                "resultado_analista": insights_analista,
                "discrepancias_validador": discrepancias_formatadas,
                "oportunidades_validador": oportunidades_formatadas
            })
            
            # Processar resultado
            if isinstance(resultado, dict):
                resultado['modelo_utilizado'] = getattr(self.llm, 'model_name', 'gemini')
                resultado['timestamp_calculo'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Gerar relatório híbrido formatado
                resultado['relatorio_hibrido'] = self._gerar_relatorio_hibrido(resultado)
                
                return resultado
            else:
                return self._erro_formato_resposta(str(resultado))
                
        except Exception as e:
            return self._erro_calculo(str(e))

    def _formatar_cabecalho_para_calculo(self, cabecalho_df: pd.DataFrame) -> str:
        """Formata dados do cabeçalho focando em informações tributárias"""
        if cabecalho_df.empty:
            return "Cabeçalho não disponível"
            
        cabecalho = cabecalho_df.iloc[0] if len(cabecalho_df) > 0 else {}
        
        info_relevante = []
        
        # SEÇÃO ESPECÍFICA PARA CÁLCULOS TRIBUTÁRIOS
        info_relevante.append("=== DADOS PARA CÁLCULO TRIBUTÁRIO ===")
        
        # Campos críticos para cálculos
        campos_tributarios = [
            'Valor Total', 'Base ICMS', 'Valor ICMS', 'Valor PIS', 'Valor COFINS', 'Valor IPI',
            'UF', 'Emitente UF', 'Destinatário UF', 'CFOP', 'Natureza Operação'
        ]
        
        for campo in campos_tributarios:
            if campo in cabecalho and pd.notna(cabecalho[campo]):
                valor = cabecalho[campo]
                info_relevante.append(f"{campo}: {valor}")
        
        # Outros campos do cabeçalho
        info_relevante.append("=== OUTROS DADOS DO CABEÇALHO ===")
        for campo, valor in cabecalho.items():
            if campo not in campos_tributarios and pd.notna(valor) and str(valor).strip():
                info_relevante.append(f"{campo}: {valor}")
                
        return "\n".join(info_relevante) if info_relevante else "Dados básicos do cabeçalho"

    def _formatar_produtos_para_calculo(self, produtos_df: pd.DataFrame) -> str:
        """Formata dados dos produtos focando em valores e alíquotas"""
        if produtos_df.empty:
            return "Nenhum produto encontrado"
            
        # Limitar produtos para análise de cálculo
        produtos_limitados = produtos_df.head(20)
        
        resultado = f"Total de produtos: {len(produtos_df)}\n\n"
        resultado += "PRODUTOS PARA CÁLCULO TRIBUTÁRIO (DADOS CRIPTOGRAFADOS):\n"
        resultado += "FOCO: Valores, alíquotas e bases de cálculo para delta tributário\n\n"
        
        # Destacar colunas de valores e alíquotas
        colunas_tributarias = [
            'Valor Unitário', 'Valor Total', 'Quantidade',
            'Alíquota ICMS', 'Valor ICMS', 'Base ICMS',
            'Alíquota PIS', 'Valor PIS', 'Alíquota COFINS', 'Valor COFINS',
            'Alíquota IPI', 'Valor IPI', 'NCM', 'CFOP'
        ]
        
        # Filtrar colunas existentes
        colunas_existentes = [col for col in colunas_tributarias if col in produtos_df.columns]
        
        if colunas_existentes:
            try:
                produtos_calc = produtos_limitados[colunas_existentes]
                resultado += produtos_calc.to_string(index=True, max_cols=None, float_format='%.2f')
            except Exception as e:
                resultado += f"Erro ao formatar produtos para cálculo: {str(e)}\n"
                resultado += produtos_limitados.to_string(index=True, max_cols=10, max_colwidth=30)
        else:
            resultado += produtos_limitados.to_string(index=True, max_cols=10, max_colwidth=30)
        
        return resultado

    def _formatar_insights_analista(self, resultado_analista: Dict[str, Any]) -> str:
        """Formata insights do analista para uso em cálculos"""
        if not resultado_analista:
            return "Nenhum insight do analista disponível"
        
        insights = f"INSIGHTS DO ANALISTA FISCAL:\n\n"
        insights += f"Status: {resultado_analista.get('status', 'N/A')}\n"
        insights += f"Regime: {resultado_analista.get('regime_tributario', 'N/A')}\n"
        
        # Análises detalhadas
        analises = resultado_analista.get('analises_detalhadas', [])
        if analises:
            insights += f"\nANÁLISES DETALHADAS ({len(analises)} encontradas):\n"
            for i, analise in enumerate(analises, 1):
                insights += f"\n{i}. {analise.get('discrepancia_original', 'N/A')}\n"
                insights += f"   Solução: {analise.get('solucao_proposta', 'N/A')}\n"
                insights += f"   Complexidade: {analise.get('grau_complexidade', 'N/A')}\n"
        
        # Oportunidades adicionais
        oportunidades = resultado_analista.get('oportunidades_adicionais', [])
        if oportunidades:
            insights += f"\nOPORTUNIDADES ADICIONAIS ({len(oportunidades)} encontradas):\n"
            for i, oport in enumerate(oportunidades, 1):
                insights += f"\n{i}. {oport.get('tipo', 'N/A')}\n"
                insights += f"   Benefício: {oport.get('beneficio_estimado', 'N/A')}\n"
        
        # Plano de ação
        plano = resultado_analista.get('plano_acao_consolidado', {})
        if plano:
            insights += f"\nPLANO DE AÇÃO:\n"
            if plano.get('acoes_imediatas'):
                insights += f"Ações imediatas: {len(plano['acoes_imediatas'])} identificadas\n"
            if plano.get('riscos_identificados'):
                insights += f"Riscos: {len(plano['riscos_identificados'])} identificados\n"
        
        return insights

    def _formatar_discrepancias(self, discrepancias: List[Dict]) -> str:
        """Formata discrepâncias para cálculos"""
        if not discrepancias:
            return "Nenhuma discrepância identificada"
        
        resultado = f"DISCREPÂNCIAS PARA CÁLCULO ({len(discrepancias)}):\n\n"
        
        for i, disc in enumerate(discrepancias, 1):
            resultado += f"DISCREPÂNCIA {i}:\n"
            resultado += f"  Tipo: {disc.get('tipo', 'N/A')}\n"
            resultado += f"  Produto: {disc.get('produto', 'N/A')}\n"
            resultado += f"  Problema: {disc.get('problema', 'N/A')}\n"
            resultado += f"  Gravidade: {disc.get('gravidade', 'N/A')}\n"
            resultado += f"  Correção sugerida: {disc.get('correcao', 'N/A')}\n\n"
        
        return resultado

    def _formatar_oportunidades(self, oportunidades: List[Dict]) -> str:
        """Formata oportunidades para cálculos"""
        if not oportunidades:
            return "Nenhuma oportunidade identificada"
        
        resultado = f"OPORTUNIDADES PARA CÁLCULO ({len(oportunidades)}):\n\n"
        
        for i, oport in enumerate(oportunidades, 1):
            resultado += f"OPORTUNIDADE {i}:\n"
            resultado += f"  Tipo: {oport.get('tipo', 'N/A')}\n"
            resultado += f"  Produto: {oport.get('produto', 'N/A')}\n"
            resultado += f"  Descrição: {oport.get('descricao', 'N/A')}\n"
            resultado += f"  Impacto estimado: {oport.get('impacto', 'N/A')}\n"
            resultado += f"  Ação recomendada: {oport.get('acao_recomendada', 'N/A')}\n\n"
        
        return resultado

    def _converter_para_numero(self, valor) -> float:
        """Converte valor para número de forma segura"""
        if valor is None:
            return 0.0
        
        # Se já é número
        if isinstance(valor, (int, float)):
            return float(valor)
        
        # Se é string, tentar converter
        if isinstance(valor, str):
            try:
                # Remover caracteres comuns em valores monetários
                valor_limpo = valor.replace('R$', '').replace('$', '').replace(' ', '')
                valor_limpo = valor_limpo.replace(',', '').replace('%', '')
                return float(valor_limpo)
            except (ValueError, AttributeError):
                return 0.0
        
        # Para qualquer outro tipo, retornar 0
        return 0.0

    def _gerar_relatorio_hibrido(self, resultado: Dict[str, Any]) -> str:
        """Gera relatório híbrido com tabelas e texto"""
        relatorio = "# 🧮 RELATÓRIO TRIBUTÁRIO - CÁLCULO DE DELTA E MULTAS\n"
        
        # Cabeçalho
        status_emoji = {"sucesso": "", "erro": "", "parcial": ""}
        emoji = status_emoji.get(resultado.get('status', 'erro'), "")
        
        relatorio += f"**{emoji} Status do Cálculo:** {resultado.get('status', 'Desconhecido')}\n"
        relatorio += f"**Regime Tributário:** {resultado.get('regime_tributario', 'LUCRO REAL')}\n"
        relatorio += f"**🔢 Impostos Analisados:** {resultado.get('impostos_analisados', 0)}\n"
        relatorio += f"**Timestamp:** {resultado.get('timestamp_calculo', 'N/A')}\n"
        
        # Tabela resumo
        tabela_resumo = resultado.get('tabela_resumo', {})
        if tabela_resumo and tabela_resumo.get('linhas'):
            relatorio += "## TABELA RESUMO - DELTA DE IMPOSTOS\n"
            
            # Cabeçalho da tabela
            cabecalho = tabela_resumo.get('cabecalho', [])
            if cabecalho:
                relatorio += "| " + " | ".join(cabecalho) + " |\n"
                relatorio += "|" + "---|" * len(cabecalho) + "\n"
                
                # Linhas da tabela
                for linha in tabela_resumo['linhas']:
                    relatorio += "| " + " | ".join(str(item) for item in linha) + " |\n"
                
        
        # Delta de impostos detalhado
        delta_impostos = resultado.get('delta_impostos', {})
        if delta_impostos:
            relatorio += "## ANÁLISE DETALHADA DO DELTA\n"
            
            # ICMS
            icms = delta_impostos.get('icms', {})
            if icms and icms.get('valor_devido') is not None:
                relatorio += "### 🏛️ ICMS\n"
                valor_pago = self._converter_para_numero(icms.get('valor_pago', 0))
                valor_devido = self._converter_para_numero(icms.get('valor_devido', 0))
                delta = self._converter_para_numero(icms.get('delta', 0))
                percentual = self._converter_para_numero(icms.get('percentual_diferenca', 0))
                
                relatorio += f"- **Valor Pago:** R$ {valor_pago:,.2f}\n"
                relatorio += f"- **Valor Devido:** R$ {valor_devido:,.2f}\n"
                relatorio += f"- **Delta:** R$ {delta:,.2f}\n"
                relatorio += f"- **% Diferença:** {percentual:.2f}%\n"
                if icms.get('observacoes'):
                    relatorio += f"- **Observações:** {icms['observacoes']}\n"
              
            
            # PIS/COFINS
            pis_cofins = delta_impostos.get('pis_cofins', {})
            if pis_cofins and pis_cofins.get('delta_total') is not None:
                relatorio += "### 🏦 PIS/COFINS\n"
                pis_pago = self._converter_para_numero(pis_cofins.get('pis_pago', 0))
                pis_devido = self._converter_para_numero(pis_cofins.get('pis_devido', 0))
                cofins_pago = self._converter_para_numero(pis_cofins.get('cofins_pago', 0))
                cofins_devido = self._converter_para_numero(pis_cofins.get('cofins_devido', 0))
                delta_total = self._converter_para_numero(pis_cofins.get('delta_total', 0))
                
                relatorio += f"- **PIS Pago:** R$ {pis_pago:,.2f}\n"
                relatorio += f"- **PIS Devido:** R$ {pis_devido:,.2f}\n"
                relatorio += f"- **COFINS Pago:** R$ {cofins_pago:,.2f}\n"
                relatorio += f"- **COFINS Devido:** R$ {cofins_devido:,.2f}\n"
                relatorio += f"- **Delta Total:** R$ {delta_total:,.2f}\n"
                if pis_cofins.get('observacoes'):
                    relatorio += f"- **Observações:** {pis_cofins['observacoes']}\n"
                
            
            # IPI
            ipi = delta_impostos.get('ipi', {})
            if ipi and ipi.get('valor_devido') is not None:
                relatorio += "### 🏭 IPI\n"
                valor_pago = self._converter_para_numero(ipi.get('valor_pago', 0))
                valor_devido = self._converter_para_numero(ipi.get('valor_devido', 0))
                delta = self._converter_para_numero(ipi.get('delta', 0))
                
                relatorio += f"- **Valor Pago:** R$ {valor_pago:,.2f}\n"
                relatorio += f"- **Valor Devido:** R$ {valor_devido:,.2f}\n"
                relatorio += f"- **Delta:** R$ {delta:,.2f}\n"
                if ipi.get('observacoes'):
                    relatorio += f"- **Observações:** {ipi['observacoes']}\n"
                
        
        # Cálculo de multas
        calculo_multas = resultado.get('calculo_multas', {})
        if calculo_multas:
            relatorio += "## CÁLCULO DE MULTAS POTENCIAIS\n"
            
            # Resumo de multas
            if calculo_multas.get('total_multas'):
                total_multas = self._converter_para_numero(calculo_multas.get('total_multas', 0))
                multa_minima = self._converter_para_numero(calculo_multas.get('multa_minima', 0))
                multa_maxima = self._converter_para_numero(calculo_multas.get('multa_maxima', 0))
                
                relatorio += f"**💸 Total de Multas:** R$ {total_multas:,.2f}\n"
                relatorio += f"**Multa Mínima:** R$ {multa_minima:,.2f}\n"
                relatorio += f"**Multa Máxima:** R$ {multa_maxima:,.2f}\n"
            
            # Detalhes das multas
            multas_potenciais = calculo_multas.get('multas_potenciais', [])
            if multas_potenciais:
                relatorio += "### DETALHAMENTO DAS MULTAS\n"
                
                for i, multa in enumerate(multas_potenciais, 1):
                    relatorio += f"**{i}. {multa.get('tipo_infracao', 'N/A')}**\n"
                    base_calculo = self._converter_para_numero(multa.get('base_calculo', 0))
                    percentual_multa = self._converter_para_numero(multa.get('percentual_multa', 0))
                    valor_multa = self._converter_para_numero(multa.get('valor_multa', 0))
                    
                    relatorio += f"   - Base de Cálculo: R$ {base_calculo:,.2f}\n"
                    relatorio += f"   - Percentual: {percentual_multa:.2f}%\n"
                    relatorio += f"   - Valor da Multa: R$ {valor_multa:,.2f}\n"
                    if multa.get('base_legal'):
                        relatorio += f"   - Base Legal: {multa['base_legal']}\n"
                    if multa.get('prazo_regularizacao'):
                        relatorio += f"   - Prazo: {multa['prazo_regularizacao']}\n"
                    relatorio += "\n"
        
        # Análise de riscos
        analise_riscos = resultado.get('analise_riscos', {})
        if analise_riscos:
            relatorio += "## ANÁLISE DE RISCOS\n\n"
            relatorio += f"**🚨 Risco de Autuação:** {analise_riscos.get('risco_autuacao', 'N/A')}\n"
            
            valor_exposicao = analise_riscos.get('valor_total_exposicao')
            if valor_exposicao is not None and valor_exposicao != 0:
                valor_exposicao = self._converter_para_numero(valor_exposicao)
                relatorio += f"**Valor Total de Exposição:** R$ {valor_exposicao:,.2f}\n"
            
            recomendacoes = analise_riscos.get('recomendacoes_urgentes', [])
            if recomendacoes:
                relatorio += f"\n**Recomendações Urgentes:**\n"
                for rec in recomendacoes:
                    relatorio += f"- {rec}\n"
            
            prazos = analise_riscos.get('prazos_criticos', [])
            if prazos:
                relatorio += f"\n**Prazos Críticos:**\n"
                for prazo in prazos:
                    relatorio += f"- {prazo}\n"
            relatorio += "\n"
        
        # Resumo executivo
        if resultado.get('resumo_executivo'):
            relatorio += "## RESUMO EXECUTIVO\n\n"
            relatorio += resultado['resumo_executivo'] + "\n\n"
        
        # Detalhes técnicos
        if resultado.get('detalhes_tecnicos'):
            relatorio += "## DETALHES TÉCNICOS\n\n"
            relatorio += resultado['detalhes_tecnicos'] + "\n\n"
        
        # Limitações
        if resultado.get('limitacoes_calculo'):
            relatorio += "## LIMITAÇÕES DO CÁLCULO\n\n"
            relatorio += resultado['limitacoes_calculo'] + "\n\n"
        
        # Rodapé
        relatorio += "---\n"
        relatorio += f"*Cálculo gerado pelo Tributarista Fiscal IA - Modelo: {resultado.get('modelo_utilizado', 'N/A')}*\n"
        relatorio += "*Regime: LUCRO REAL - Sempre valide os cálculos com um profissional contábil*"
        
        return relatorio

    def _erro_chain_nao_inicializada(self) -> Dict[str, Any]:
        """Retorna erro quando chain não foi inicializada"""
        return {
            'status': 'erro',
            'regime_tributario': 'LUCRO REAL',
            'impostos_analisados': 0,
            'delta_impostos': {},
            'calculo_multas': {},
            'tabela_resumo': {},
            'analise_riscos': {},
            'limitacoes_calculo': 'LLM não inicializada',
            'relatorio_hibrido': "**Erro:** LLM não inicializada. Verifique a configuração da GOOGLE_API_KEY.",
            'modelo_utilizado': 'N/A',
            'timestamp_calculo': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _erro_formato_resposta(self, resposta: str) -> Dict[str, Any]:
        """Retorna erro de formato de resposta"""
        return {
            'status': 'erro',
            'regime_tributario': 'LUCRO REAL',
            'impostos_analisados': 0,
            'delta_impostos': {},
            'calculo_multas': {},
            'tabela_resumo': {},
            'analise_riscos': {},
            'limitacoes_calculo': 'Erro de formato na resposta da LLM',
            'relatorio_hibrido': f"**Erro de formato:** A LLM retornou resposta em formato inválido.\n\nResposta: {resposta[:500]}...",
            'modelo_utilizado': getattr(self.llm, 'model_name', 'gemini') if self.llm else 'N/A',
            'timestamp_calculo': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _erro_calculo(self, erro: str) -> Dict[str, Any]:
        """Retorna erro geral de cálculo"""
        return {
            'status': 'erro',
            'regime_tributario': 'LUCRO REAL',
            'impostos_analisados': 0,
            'delta_impostos': {},
            'calculo_multas': {},
            'tabela_resumo': {},
            'analise_riscos': {},
            'limitacoes_calculo': f'Erro durante cálculo: {erro}',
            'relatorio_hibrido': f"**Erro no cálculo:** {erro}",
            'modelo_utilizado': getattr(self.llm, 'model_name', 'gemini') if self.llm else 'N/A',
            'timestamp_calculo': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# Função de conveniência para uso na interface
def calcular_delta_tributario(cabecalho_criptografado: pd.DataFrame, 
                             produtos_criptografados: pd.DataFrame, 
                             resultado_analista: Dict[str, Any],
                             resultado_validador: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função principal para cálculo de delta tributário usando LangChain
    
    Args:
        cabecalho_criptografado: DataFrame criptografado com cabeçalho
        produtos_criptografados: DataFrame criptografado com produtos
        resultado_analista: Resultado completo da análise do analista
        resultado_validador: Resultado do validador com discrepâncias
        
    Returns:
        dict: Resultado dos cálculos com tabelas e análises
    """
    try:
        tributarista = TributaristaFiscal()
        return tributarista.calcular_delta_impostos(
            cabecalho_criptografado, 
            produtos_criptografados, 
            resultado_analista,
            resultado_validador
        )
    except Exception as e:
        return {
            'status': 'erro',
            'regime_tributario': 'LUCRO REAL',
            'impostos_analisados': 0,
            'delta_impostos': {},
            'calculo_multas': {},
            'tabela_resumo': {},
            'analise_riscos': {},
            'limitacoes_calculo': f'Erro crítico: {str(e)}',
            'relatorio_hibrido': f"**Erro crítico:** {str(e)}",
            'modelo_utilizado': 'N/A',
            'timestamp_calculo': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }


if __name__ == "__main__":
    print("🧮 Tributarista Fiscal - Cálculo de Delta e Multas - Teste Local\n")
    
    # Teste básico com dados simulados
    cabecalho_teste = pd.DataFrame({
        'Valor Total': [10000.00],
        'Base ICMS': [10000.00],
        'Valor ICMS': [1200.00],  # 12% aplicado
        'Valor PIS': [165.00],    # 1.65% 
        'Valor COFINS': [760.00], # 7.6%
        'UF': ['SP'],
        'Emitente UF': ['SP'],
        'Destinatário UF': ['RJ'],
        'CFOP': ['6102']
    })
    
    produtos_teste = pd.DataFrame({
        'Produto': ['gAAAAABhXmY8_encrypted_produto'],
        'NCM': ['84713012'],
        'Valor Total': [10000.00],
        'Alíquota ICMS': ['12%'],
        'Valor ICMS': [1200.00],
        'Alíquota PIS': ['1.65%'],
        'Valor PIS': [165.00],
        'Alíquota COFINS': ['7.6%'],
        'Valor COFINS': [760.00]
    })
    
    # Resultado simulado do analista
    resultado_analista_teste = {
        'status': 'sucesso',
        'regime_tributario': 'LUCRO REAL',
        'analises_detalhadas': [
            {
                'discrepancia_original': 'Alíquota ICMS incorreta',
                'solucao_proposta': 'Ajustar para 18% conforme legislação',
                'grau_complexidade': 'Médio'
            }
        ],
        'oportunidades_adicionais': [],
        'plano_acao_consolidado': {
            'acoes_imediatas': ['Recalcular ICMS'],
            'riscos_identificados': ['Multa por diferença de recolhimento']
        }
    }
    
    # Resultado simulado do validador
    resultado_validador_teste = {
        'status': 'parcial',
        'discrepancias': [
            {
                'tipo': 'Alíquota ICMS',
                'problema': 'Alíquota de 12% deveria ser 18%',
                'gravidade': 'Alta'
            }
        ],
        'oportunidades': []
    }
    
    # Executar cálculo
    resultado = calcular_delta_tributario(
        cabecalho_teste, 
        produtos_teste, 
        resultado_analista_teste,
        resultado_validador_teste
    )
    
    print(f"🧮 Status: {resultado['status']}")
    print(f"Regime: {resultado['regime_tributario']}")
    print(f"🔢 Impostos analisados: {resultado['impostos_analisados']}")
    print(f"Modelo: {resultado.get('modelo_utilizado', 'N/A')}")
    
    print("\n" + "="*70)
    print("RELATÓRIO HÍBRIDO:")
    print("="*70)
    print(resultado['relatorio_hibrido'])