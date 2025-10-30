"""
Analista Fiscal - Tratamento de Discrepâncias com LLM
Sistema especializado em analisar e propor soluções para discrepâncias fiscais identificadas
pelo validador, utilizando conhecimento da nuvem via LLM e regime de Lucro Real.
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


class AnalistaFiscal:
    """
    Analista fiscal especializado em tratamento de discrepâncias com LLM.
    Usa conhecimento da nuvem para propor soluções específicas para LUCRO REAL.
    """

    def __init__(self):
        """Inicializa o analista fiscal com LangChain"""
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
                        print(f"LLM Analista inicializada: {modelo}")
                        break
                        
                except Exception as e:
                    print(f"Modelo {modelo} indisponível: {str(e)[:100]}")
                    continue

            if not self.llm:
                raise Exception("Nenhum modelo Gemini disponível")

            # Criar parser e chain
            self._criar_chain()
            
        except Exception as e:
            print(f"Erro ao inicializar LLM Analista: {e}")
            self.llm = None
            self.chain = None

    def _criar_chain(self):
        """Cria a chain do LangChain com prompt especializado em análise de discrepâncias"""
        
        # Template do prompt para análise de discrepâncias
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Você é um ANALISTA FISCAL ESPECIALISTA em regime de LUCRO REAL com profundo conhecimento da legislação tributária brasileira.

Sua missão é analisar ESPECIFICAMENTE as discrepâncias fiscais identificadas e propor SOLUÇÕES PRÁTICAS baseadas em:
- Legislação tributária atualizada (obtida via conhecimento da nuvem)
- Regime de tributação LUCRO REAL
- Melhores práticas fiscais
- Jurisprudência relevante

CONTEXTO IMPORTANTE:
- REGIME: LUCRO REAL (sempre considerar este regime)
- FOCO: Análise de discrepâncias e correções
- FONTE: Conhecimento da nuvem/legislação atualizada
- DADOS: Dados sensíveis como CNPJ e nomes não devem ser divulgados ou utilizados pela LLM
- FORMATAÇÃO: Evite emojis e mantenha uma resposta com teor corporativo

IMPORTANTE SOBRE DADOS CRIPTOGRAFADOS:
- Os dados sensíveis (CNPJs, nomes, etc.) estão criptografados
- Use padrões e estruturas dos dados criptografados para análise
- Foque nos aspectos fiscais e tributários que podem ser identificados
- Considere valores, alíquotas, e classificações fiscais para análise
- Se não houver percentagens das alíquotas, utilize os valores de tributos e impostos para o cálculo das mesmas e avaliação se estão corretas  
- Não tente descriptografar os dados - trabalhe com eles como estão

ATENÇÃO ESPECIAL PARA UFs (UNIDADES FEDERATIVAS):
- As UFs são apresentadas de forma destacada no cabeçalho
- Podem aparecer como códigos numéricos (ex: 35 = SP, 33 = RJ, 31 = MG)
- UF do Emitente: Estado de origem da operação
- UF do Destinatário: Estado de destino da operação (CRÍTICO para análise ICMS)
- A diferença entre UF origem e destino é fundamental para:
  * Alíquotas de ICMS interestadual
  * Aplicação de Substituição Tributária
  * Regras de DIFAL (Diferencial de Alíquota)
  * Benefícios fiscais estaduais

INSTRUÇÕES CRÍTICAS:
1. Para cada discrepância, busque na legislação atual a forma CORRETA de proceder
2. Considere SEMPRE o regime de Lucro Real
3. Identifique se há falta de dados críticos que impedem a correção
4. Proponha ações específicas e práticas
5. Indique quando é necessário consultar contador/advogado
6. Cite base legal quando relevante
7. Trabalhe com dados criptografados sem tentar revelá-los

FORMATO DE RESPOSTA (JSON estrito):
{{
  "status": "sucesso|erro|parcial",
  "regime_tributario": "LUCRO REAL",
  "discrepancias_analisadas": <número>,
  "analises_detalhadas": [
    {{
      "discrepancia_original": "Descrição da discrepância identificada",
      "analise_tecnica": "Análise técnica baseada na legislação",
      "solucao_proposta": "Solução específica e prática",
      "base_legal": "Fundamentação legal (quando aplicável)",
      "acao_imediata": "O que fazer imediatamente",
      "acao_preventiva": "Como evitar no futuro",
      "grau_complexidade": "Simples|Médio|Complexo",
      "requer_consultoria": true/false,
      "dados_necessarios": ["lista de dados adicionais necessários"]
    }}
  ],
  "oportunidades_adicionais": [
    {{
      "tipo": "Oportunidade identificada durante análise",
      "descricao": "Descrição da oportunidade",
      "beneficio_estimado": "Benefício potencial",
      "aplicabilidade_lucro_real": "Como se aplica no Lucro Real"
    }}
  ],
  "plano_acao_consolidado": {{
    "acoes_imediatas": ["Lista de ações urgentes"],
    "acoes_medio_prazo": ["Lista de ações para implementar"],
    "consultoria_necessaria": ["Pontos que necessitam consultoria"],
    "documentos_necessarios": ["Documentos a providenciar"],
    "riscos_identificados": ["Riscos se não corrigir"]
  }},
  "limitacoes_analise": "Limitações encontradas por falta de dados",
  "resumo_executivo": "Resumo executivo em texto markdown com foco em ações",
  "detalhes_tecnicos": "Detalhes técnicos específicos em texto markdown"
}}"""),
            ("human", """DADOS PARA ANÁLISE DE DISCREPÂNCIAS (CRIPTOGRAFADOS):

IMPORTANTE: Os dados abaixo estão criptografados por segurança. Analise os padrões, estruturas e valores não sensíveis.

CABEÇALHO DA NFe (CRIPTOGRAFADO):
{dados_cabecalho}

PRODUTOS DA NFe (CRIPTOGRAFADOS):
{dados_produtos}

DISCREPÂNCIAS IDENTIFICADAS PELO VALIDADOR:
{discrepancias_validador}

OPORTUNIDADES IDENTIFICADAS PELO VALIDADOR:
{oportunidades_validador}

CONTEXTO DO RESULTADO DO VALIDADOR:
{contexto_validador}

INSTRUÇÕES ESPECÍFICAS PARA ANÁLISE DE UFs:
1. Identifique claramente a UF de ORIGEM (Emitente) e UF de DESTINO (Destinatário)
2. Se as UFs forem diferentes, considere operação INTERESTADUAL
3. Se as UFs forem iguais, considere operação INTERNA
4. Para operações interestaduais, verifique:
   - Alíquotas de ICMS interestaduais (4%, 7% ou 12%)
   - Aplicação de DIFAL quando destinatário for consumidor final
   - Substituição Tributária entre estados
   - Benefícios fiscais específicos

Analise essas discrepâncias considerando o regime de LUCRO REAL e forneça soluções práticas baseadas na legislação atual. Trabalhe com os dados criptografados como estão, focando nos aspectos fiscais identificáveis.""")
        ])

        # Parser JSON
        parser = JsonOutputParser()
        
        # Criar chain
        self.chain = prompt_template | self.llm | parser

    def analisar_discrepancias(self, 
                             cabecalho_df: pd.DataFrame, 
                             produtos_df: pd.DataFrame, 
                             resultado_validador: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método principal que analisa discrepâncias usando LLM e conhecimento da nuvem
        
        Args:
            cabecalho_df: DataFrame criptografado com dados do cabeçalho (mantido criptografado)
            produtos_df: DataFrame criptografado com dados dos produtos (mantido criptografado)
            resultado_validador: Resultado completo do validador com discrepâncias
            
        Returns:
            dict: Resultado da análise com soluções propostas
            
        IMPORTANTE: Este método trabalha com dados CRIPTOGRAFADOS por segurança.
        A LLM analisa padrões e estruturas dos dados sem descriptografá-los.
        """
        try:
            if not self.chain:
                return self._erro_chain_nao_inicializada()

            # Verificar se há discrepâncias para analisar
            discrepancias = resultado_validador.get('discrepancias', [])
            if not discrepancias:
                return self._sem_discrepancias()

            # Usar dados CRIPTOGRAFADOS para análise (não descriptografar)
            # A LLM trabalhará com dados anonimizados/criptografados
            cabecalho = cabecalho_df
            produtos = produtos_df
            
            print(f"🔒 Analista - Usando dados CRIPTOGRAFADOS para análise na nuvem")
            print(f"   Cabecalho shape: {cabecalho.shape if not cabecalho.empty else 'Vazio'}")
            print(f"   Produtos shape: {produtos.shape if not produtos.empty else 'Vazio'}")
            
            # Preparar dados criptografados para o prompt
            dados_cabecalho = self._formatar_cabecalho_criptografado(cabecalho)
            dados_produtos = self._formatar_produtos_criptografados(produtos)
            discrepancias_formatadas = self._formatar_discrepancias(discrepancias)
            oportunidades_formatadas = self._formatar_oportunidades(resultado_validador.get('oportunidades', []))
            contexto_formatado = self._formatar_contexto_validador(resultado_validador)
            
            # Executar análise via LangChain
            resultado = self.chain.invoke({
                "dados_cabecalho": dados_cabecalho,
                "dados_produtos": dados_produtos,
                "discrepancias_validador": discrepancias_formatadas,
                "oportunidades_validador": oportunidades_formatadas,
                "contexto_validador": contexto_formatado
            })
            
            # Processar resultado
            if isinstance(resultado, dict):
                resultado['modelo_utilizado'] = getattr(self.llm, 'model_name', 'gemini')
                resultado['timestamp_analise'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Gerar relatório formatado
                resultado['relatorio_final'] = self._gerar_relatorio_final(resultado)
                
                return resultado
            else:
                return self._erro_formato_resposta(str(resultado))
                
        except Exception as e:
            return self._erro_analise(str(e))

    def _formatar_cabecalho(self, cabecalho_df: pd.DataFrame) -> str:
        """Formata dados do cabeçalho para o prompt (MÉTODO LEGADO - NÃO USADO)"""
        # Mantido para compatibilidade, mas não é usado
        pass

    def _formatar_cabecalho_criptografado(self, cabecalho_df: pd.DataFrame) -> str:
        """Formata dados CRIPTOGRAFADOS do cabeçalho para análise na nuvem"""
        if cabecalho_df.empty:
            return "Cabeçalho não disponível"
            
        cabecalho = cabecalho_df.iloc[0] if len(cabecalho_df) > 0 else {}
        
        info_relevante = []
        
        # SEÇÃO ESPECÍFICA PARA UFs - DESTACAR PARA MELHOR IDENTIFICAÇÃO
        info_relevante.append("=== INFORMAÇÕES DE LOCALIZAÇÃO (UFs) ===")
        
        # Mapear códigos de UF para siglas se necessário
        codigo_uf_map = {
            '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
            '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
            '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
            '41': 'PR', '42': 'SC', '43': 'RS',
            '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
        }
        
        # Campos relacionados a UF com prioridade
        campos_uf = ['UF', 'Emitente UF', 'Destinatário UF', 'Transportadora UF']
        
        for campo in campos_uf:
            if campo in cabecalho and pd.notna(cabecalho[campo]):
                valor = str(cabecalho[campo]).strip()
                # Converter código para sigla se necessário
                if valor in codigo_uf_map:
                    valor_formatado = f"{valor} ({codigo_uf_map[valor]})"
                else:
                    valor_formatado = valor
                info_relevante.append(f"🗺️ {campo}: {valor_formatado}")
        
        info_relevante.append("=== OUTROS DADOS DO CABEÇALHO ===")
        
        # Campos fiscais importantes
        campos_fiscais = ['CFOP', 'Natureza Operação', 'Valor Total', 'Data Emissão', 'Número NF']
        
        for campo in campos_fiscais:
            if campo in cabecalho and pd.notna(cabecalho[campo]):
                info_relevante.append(f"{campo}: {cabecalho[campo]}")
        
        # Outros campos (criptografados)
        for campo, valor in cabecalho.items():
            if campo not in campos_uf + campos_fiscais and pd.notna(valor) and str(valor).strip():
                info_relevante.append(f"🔒 {campo}: {valor}")
                
        return "\n".join(info_relevante) if info_relevante else "Dados básicos do cabeçalho (criptografados)"

    def _formatar_produtos(self, produtos_df: pd.DataFrame) -> str:
        """Formata dados dos produtos para o prompt (MÉTODO LEGADO - NÃO USADO)"""
        # Mantido para compatibilidade, mas não é usado
        pass

    def _formatar_produtos_criptografados(self, produtos_df: pd.DataFrame) -> str:
        """Formata dados CRIPTOGRAFADOS dos produtos para análise na nuvem"""
        if produtos_df.empty:
            return "Nenhum produto encontrado"
            
        # Limitar a 15 produtos para evitar prompt muito grande (dados criptografados podem ser maiores)
        produtos_limitados = produtos_df.head(15)
        
        resultado = f"Total de produtos: {len(produtos_df)}\n\n"
        resultado += "Produtos para análise de discrepâncias (DADOS CRIPTOGRAFADOS):\n"
        resultado += "IMPORTANTE: Os dados sensíveis abaixo estão criptografados para proteção.\n\n"
        
        # Usar todas as colunas disponíveis (dados criptografados)
        try:
            resultado += produtos_limitados.to_string(index=True, max_cols=None, max_colwidth=50)
        except Exception as e:
            # Fallback em caso de erro
            resultado += f"Erro ao formatar produtos criptografados: {str(e)}\n"
            resultado += f"Colunas disponíveis: {list(produtos_df.columns)}"
        
        return resultado

    def _formatar_discrepancias(self, discrepancias: List[Dict]) -> str:
        """Formata discrepâncias do validador para análise"""
        if not discrepancias:
            return "Nenhuma discrepância identificada"
        
        resultado = f"Total de discrepâncias: {len(discrepancias)}\n\n"
        
        for i, disc in enumerate(discrepancias, 1):
            resultado += f"DISCREPÂNCIA {i}:\n"
            resultado += f"  Tipo: {disc.get('tipo', 'N/A')}\n"
            resultado += f"  Produto: {disc.get('produto', 'N/A')}\n"
            resultado += f"  Problema: {disc.get('problema', 'N/A')}\n"
            resultado += f"  Gravidade: {disc.get('gravidade', 'N/A')}\n"
            resultado += f"  Correção sugerida: {disc.get('correcao', 'N/A')}\n\n"
        
        return resultado

    def _formatar_oportunidades(self, oportunidades: List[Dict]) -> str:
        """Formata oportunidades do validador"""
        if not oportunidades:
            return "Nenhuma oportunidade identificada"
        
        resultado = f"Total de oportunidades: {len(oportunidades)}\n\n"
        
        for i, oport in enumerate(oportunidades, 1):
            resultado += f"OPORTUNIDADE {i}:\n"
            resultado += f"  Tipo: {oport.get('tipo', 'N/A')}\n"
            resultado += f"  Produto: {oport.get('produto', 'N/A')}\n"
            resultado += f"  Descrição: {oport.get('descricao', 'N/A')}\n"
            resultado += f"  Impacto: {oport.get('impacto', 'N/A')}\n"
            resultado += f"  Ação recomendada: {oport.get('acao_recomendada', 'N/A')}\n\n"
        
        return resultado

    def _formatar_contexto_validador(self, resultado_validador: Dict[str, Any]) -> str:
        """Formata contexto geral do validador"""
        contexto = f"Status da validação: {resultado_validador.get('status', 'N/A')}\n"
        contexto += f"Produtos analisados: {resultado_validador.get('produtos_analisados', 0)}\n"
        contexto += f"Total de oportunidades: {len(resultado_validador.get('oportunidades', []))}\n"
        contexto += f"Total de discrepâncias: {len(resultado_validador.get('discrepancias', []))}\n"
        
        if resultado_validador.get('resumo_executivo'):
            contexto += f"\nResumo do validador:\n{resultado_validador['resumo_executivo']}"
        
        return contexto

    def _gerar_relatorio_final(self, resultado: Dict[str, Any]) -> str:
        """Gera relatório final formatado com plano de ação"""
        relatorio = "# RELATÓRIO ANALÍTICO - TRATAMENTO DE DISCREPÂNCIAS\n\n"
        
        # Cabeçalho
        status_emoji = {"sucesso": "", "erro": "", "parcial": ""}
        emoji = status_emoji.get(resultado.get('status', 'erro'), "")
        
        relatorio += f"**{emoji} Status da Análise:** {resultado.get('status', 'Desconhecido')}\n"
        relatorio += f"**Regime Tributário:** {resultado.get('regime_tributario', 'LUCRO REAL')}\n"
        relatorio += f"**Discrepâncias Analisadas:** {resultado.get('discrepancias_analisadas', 0)}\n"
        relatorio += f"**Timestamp:** {resultado.get('timestamp_analise', 'N/A')}\n\n"
        
        # Resumo executivo
        if resultado.get('resumo_executivo'):
            relatorio += "## RESUMO EXECUTIVO\n\n"
            relatorio += resultado['resumo_executivo'] + "\n\n"
        
        # Análises detalhadas
        analises = resultado.get('analises_detalhadas', [])
        if analises:
            relatorio += "## 🔬 ANÁLISES DETALHADAS\n\n"
            for i, analise in enumerate(analises, 1):
                complexidade_emoji = {"Simples": "🟢", "Médio": "🟡", "Complexo": "🔴"}
                emoji_comp = complexidade_emoji.get(analise.get('grau_complexidade', 'Médio'), "⚪")
                consultoria_emoji = "👨‍" if analise.get('requer_consultoria', False) else ""
                
                relatorio += f"### {i}. {analise.get('discrepancia_original', 'N/A')} {emoji_comp} {consultoria_emoji}\n\n"
                relatorio += f"**Análise Técnica:**\n{analise.get('analise_tecnica', 'N/A')}\n\n"
                relatorio += f"**💡 Solução Proposta:**\n{analise.get('solucao_proposta', 'N/A')}\n\n"
                
                if analise.get('base_legal'):
                    relatorio += f"**⚖️ Base Legal:**\n{analise['base_legal']}\n\n"
                
                relatorio += f"**Ação Imediata:**\n{analise.get('acao_imediata', 'N/A')}\n\n"
                relatorio += f"**🛡️ Ação Preventiva:**\n{analise.get('acao_preventiva', 'N/A')}\n\n"
                
                if analise.get('dados_necessarios'):
                    relatorio += f"**Dados Necessários:**\n"
                    for dado in analise['dados_necessarios']:
                        relatorio += f"   • {dado}\n"
                    relatorio += "\n"
        
        # Oportunidades adicionais
        oportunidades = resultado.get('oportunidades_adicionais', [])
        if oportunidades:
            relatorio += "## OPORTUNIDADES ADICIONAIS IDENTIFICADAS\n\n"
            for i, oport in enumerate(oportunidades, 1):
                relatorio += f"**{i}. {oport.get('tipo', 'N/A')}**\n"
                relatorio += f"   • **Descrição:** {oport.get('descricao', 'N/A')}\n"
                relatorio += f"   • **Benefício:** {oport.get('beneficio_estimado', 'N/A')}\n"
                relatorio += f"   • **Lucro Real:** {oport.get('aplicabilidade_lucro_real', 'N/A')}\n\n"
        
        # Plano de ação consolidado
        plano = resultado.get('plano_acao_consolidado', {})
        if plano:
            relatorio += "## PLANO DE AÇÃO CONSOLIDADO\n\n"
            
            if plano.get('acoes_imediatas'):
                relatorio += "### AÇÕES IMEDIATAS\n"
                for acao in plano['acoes_imediatas']:
                    relatorio += f"• {acao}\n"
                relatorio += "\n"
            
            if plano.get('acoes_medio_prazo'):
                relatorio += "### 📅 AÇÕES MÉDIO PRAZO\n"
                for acao in plano['acoes_medio_prazo']:
                    relatorio += f"• {acao}\n"
                relatorio += "\n"
            
            if plano.get('consultoria_necessaria'):
                relatorio += "### 👨‍CONSULTORIA NECESSÁRIA\n"
                for item in plano['consultoria_necessaria']:
                    relatorio += f"• {item}\n"
                relatorio += "\n"
            
            if plano.get('documentos_necessarios'):
                relatorio += "### DOCUMENTOS A PROVIDENCIAR\n"
                for doc in plano['documentos_necessarios']:
                    relatorio += f"• {doc}\n"
                relatorio += "\n"
            
            if plano.get('riscos_identificados'):
                relatorio += "### RISCOS SE NÃO CORRIGIR\n"
                for risco in plano['riscos_identificados']:
                    relatorio += f"• {risco}\n"
                relatorio += "\n"
        
        # Limitações
        if resultado.get('limitacoes_analise'):
            relatorio += "## LIMITAÇÕES DA ANÁLISE\n\n"
            relatorio += resultado['limitacoes_analise'] + "\n\n"
        
        # Detalhes técnicos
        if resultado.get('detalhes_tecnicos'):
            relatorio += "## DETALHES TÉCNICOS\n\n"
            relatorio += resultado['detalhes_tecnicos'] + "\n\n"
        
        # Rodapé
        relatorio += "---\n"
        relatorio += f"*Análise gerada pelo Analista Fiscal IA - Modelo: {resultado.get('modelo_utilizado', 'N/A')}*\n"
        relatorio += "*Regime: LUCRO REAL - Sempre consulte um profissional contábil para casos complexos*"
        
        return relatorio

    def _sem_discrepancias(self) -> Dict[str, Any]:
        """Retorna resultado quando não há discrepâncias para analisar"""
        return {
            'status': 'sucesso',
            'regime_tributario': 'LUCRO REAL',
            'discrepancias_analisadas': 0,
            'analises_detalhadas': [],
            'oportunidades_adicionais': [],
            'plano_acao_consolidado': {},
            'limitacoes_analise': '',
            'relatorio_final': "# ANÁLISE CONCLUÍDA\n\n**Nenhuma discrepância identificada para tratamento.**\n\nTodas as verificações do validador foram aprovadas. A nota fiscal está em conformidade com as regras analisadas.",
            'modelo_utilizado': getattr(self.llm, 'model_name', 'gemini') if self.llm else 'N/A',
            'timestamp_analise': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _erro_chain_nao_inicializada(self) -> Dict[str, Any]:
        """Retorna erro quando chain não foi inicializada"""
        return {
            'status': 'erro',
            'regime_tributario': 'LUCRO REAL',
            'discrepancias_analisadas': 0,
            'analises_detalhadas': [],
            'oportunidades_adicionais': [],
            'plano_acao_consolidado': {},
            'limitacoes_analise': 'LLM não inicializada',
            'relatorio_final': "**Erro:** LLM não inicializada. Verifique a configuração da GOOGLE_API_KEY.",
            'modelo_utilizado': 'N/A',
            'timestamp_analise': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _erro_formato_resposta(self, resposta: str) -> Dict[str, Any]:
        """Retorna erro de formato de resposta"""
        return {
            'status': 'erro',
            'regime_tributario': 'LUCRO REAL',
            'discrepancias_analisadas': 0,
            'analises_detalhadas': [],
            'oportunidades_adicionais': [],
            'plano_acao_consolidado': {},
            'limitacoes_analise': 'Erro de formato na resposta da LLM',
            'relatorio_final': f"**Erro de formato:** A LLM retornou resposta em formato inválido.\n\nResposta: {resposta[:500]}...",
            'modelo_utilizado': getattr(self.llm, 'model_name', 'gemini') if self.llm else 'N/A',
            'timestamp_analise': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _erro_analise(self, erro: str) -> Dict[str, Any]:
        """Retorna erro geral de análise"""
        return {
            'status': 'erro',
            'regime_tributario': 'LUCRO REAL',
            'discrepancias_analisadas': 0,
            'analises_detalhadas': [],
            'oportunidades_adicionais': [],
            'plano_acao_consolidado': {},
            'limitacoes_analise': f'Erro durante análise: {erro}',
            'relatorio_final': f"**Erro na análise:** {erro}",
            'modelo_utilizado': getattr(self.llm, 'model_name', 'gemini') if self.llm else 'N/A',
            'timestamp_analise': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# Função de conveniência para uso na interface
def analisar_discrepancias_nfe(cabecalho_criptografado: pd.DataFrame, 
                              produtos_criptografados: pd.DataFrame, 
                              resultado_validador: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função principal para análise de discrepâncias usando LangChain
    
    Args:
        cabecalho_criptografado: DataFrame criptografado com cabeçalho (MANTIDO CRIPTOGRAFADO)
        produtos_criptografados: DataFrame criptografado com produtos (MANTIDO CRIPTOGRAFADO)
        resultado_validador: Resultado completo da análise do validador
        
    Returns:
        dict: Resultado da análise com soluções propostas
        
    IMPORTANTE: Esta função trabalha com dados CRIPTOGRAFADOS por segurança.
    Os dados não são descriptografados antes de serem enviados para a LLM.
    """
    try:
        analista = AnalistaFiscal()
        return analista.analisar_discrepancias(cabecalho_criptografado, produtos_criptografados, resultado_validador)
    except Exception as e:
        return {
            'status': 'erro',
            'regime_tributario': 'LUCRO REAL',
            'discrepancias_analisadas': 0,
            'analises_detalhadas': [],
            'oportunidades_adicionais': [],
            'plano_acao_consolidado': {},
            'limitacoes_analise': f'Erro crítico: {str(e)}',
            'relatorio_final': f"**Erro crítico:** {str(e)}",
            'modelo_utilizado': 'N/A',
            'timestamp_analise': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }


if __name__ == "__main__":
    print("Analista Fiscal - Tratamento de Discrepâncias - Teste Local\n")
    
    # Teste básico com discrepâncias simuladas
    cabecalho_teste = pd.DataFrame({
        'CNPJ': ['12345678000199'],
        'UF': ['SP'],
        'Natureza da Operação': ['Venda'],
        'CFOP': ['6102']
    })
    
    produtos_teste = pd.DataFrame({
        'Produto': ['Notebook Dell Inspiron'],
        'NCM': ['84713012'],
        'CFOP': ['6102'],
        'Quantidade': [1],
        'Valor Unitário': [3500.00],
        'Alíquota ICMS': ['12%'],
        'Alíquota PIS': ['1.65%'],
        'Alíquota COFINS': ['7.6%']
    })
    
    # Resultado simulado do validador
    resultado_validador_teste = {
        'status': 'parcial',
        'produtos_analisados': 1,
        'oportunidades': [
            {
                'tipo': 'Substituição Tributária',
                'produto': 'Notebook Dell Inspiron',
                'descricao': 'Produto pode estar sujeito à ST',
                'impacto': 'Redução de 5% na carga tributária',
                'acao_recomendada': 'Verificar enquadramento na ST'
            }
        ],
        'discrepancias': [
            {
                'tipo': 'Alíquota ICMS',
                'produto': 'Notebook Dell Inspiron',
                'problema': 'Alíquota aplicada pode estar incorreta',
                'gravidade': 'Média',
                'correcao': 'Verificar alíquota correta para NCM'
            }
        ],
        'resumo_executivo': 'Análise identificou discrepâncias na alíquota ICMS'
    }
    
    # Executar análise
    resultado = analisar_discrepancias_nfe(cabecalho_teste, produtos_teste, resultado_validador_teste)
    
    print(f"Status: {resultado['status']}")
    print(f"Regime: {resultado['regime_tributario']}")
    print(f"Discrepâncias analisadas: {resultado['discrepancias_analisadas']}")
    print(f"💡 Análises detalhadas: {len(resultado['analises_detalhadas'])}")
    print(f"Modelo: {resultado.get('modelo_utilizado', 'N/A')}")
    
    print("\n" + "="*70)
    print("RELATÓRIO FINAL:")
    print("="*70)
    print(resultado['relatorio_final'])