"""
Orquestrador de Agentes - Coordenação Sequencial
Sistema que coordena a execução sequencial dos agentes:
1. Validador → 2. Analista → 3. Tributarista
"""

import pandas as pd
from typing import Dict, Any, Callable
from datetime import datetime

# Imports dos agentes existentes
from .validador import ValidadorFiscal
from .analista import AnalistaFiscal
from .tributarista import TributaristaFiscal


class OrquestradorAgentes:
    """
    Orquestrador que coordena a execução sequencial dos agentes fiscais
    """
    
    def __init__(self):
        """Inicializa os agentes fiscais"""
        self.validador = ValidadorFiscal()
        self.analista = AnalistaFiscal()
        self.tributarista = TributaristaFiscal()
        
    def processar_sequencial(self, 
                           cabecalho_df: pd.DataFrame, 
                           produtos_df: pd.DataFrame,
                           callback_status: Callable[[str], None] = None) -> Dict[str, Any]:
        """
        Executa processamento sequencial dos 3 agentes
        
        Args:
            cabecalho_df: DataFrame criptografado com dados do cabeçalho
            produtos_df: DataFrame criptografado com dados dos produtos
            callback_status: Função callback para atualizar status na interface
            
        Returns:
            dict: Resultados consolidados dos 3 agentes
        """
        
        def log_status(mensagem: str):
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_completo = f"{timestamp} - {mensagem}"
            print(log_completo)  # Log para terminal/debug
            if callback_status:
                callback_status(log_completo)
        
        # Timeout global para evitar travamento por limite de API
        inicio_processamento = datetime.now()
        timeout_segundos = 300  # 5 minutos máximo
        
        try:
            # AGENTE 1: VALIDADOR
            log_status("Agente Validador avaliando regras no banco de dados...")
            log_status("Nota: Analista e Tributarista limitados a ~10 requisições/min pela API do Gemini")
            resultado_validador = self.validador.analisar_nfe(cabecalho_df, produtos_df)
            
            # Verificar se validador teve sucesso
            if resultado_validador.get('status') == 'erro':
                log_status("Erro no Agente Validador - Abortando processamento")
                return self._resultado_erro("Falha no Agente Validador", resultado_validador)
            
            oportunidades = len(resultado_validador.get('oportunidades', []))
            discrepancias = len(resultado_validador.get('discrepancias', []))
            log_status(f"Validador concluído: {oportunidades} oportunidades, {discrepancias} discrepâncias encontradas")
            
            # AGENTE 2: ANALISTA (com delay para evitar limite de API)
            import time
            time.sleep(2)  # Delay de 2 segundos entre agentes
            
            log_status("Agente Analista buscando informações adicionais com auxílio de IA...")
            try:
                resultado_analista = self.analista.analisar_discrepancias(
                    cabecalho_df, 
                    produtos_df, 
                    resultado_validador
                )
                
                # Verificar se analista teve sucesso
                if resultado_analista.get('status') == 'erro':
                    log_status("Erro no Agente Analista - Continuando com Tributarista")
                else:
                    solucoes = len(resultado_analista.get('solucoes_propostas', []))
                    log_status(f"Analista concluído: {solucoes} soluções propostas")
                    
            except Exception as e:
                log_status(f"Erro no Agente Analista ({str(e)[:50]}...) - Continuando com Tributarista")
                resultado_analista = {'status': 'erro', 'erro': str(e), 'solucoes_propostas': []}
            
            # AGENTE 3: TRIBUTARISTA (com delay para evitar limite de API)
            time.sleep(2)  # Delay de 2 segundos entre agentes
            
            log_status("Agente Tributarista calculando oportunidades financeiras...")
            try:
                resultado_tributarista = self.tributarista.calcular_delta_impostos(
                    cabecalho_df,
                    produtos_df,
                    resultado_analista,
                    resultado_validador
                )
                
                # Verificar se tributarista teve sucesso
                if resultado_tributarista.get('status') == 'erro':
                    log_status("Erro no Agente Tributarista - Processamento com limitações")
                else:
                    # Extrair valor do delta se disponível
                    delta_info = self._extrair_delta_total(resultado_tributarista)
                    log_status(f"Tributarista concluído: {delta_info}")
                    
            except Exception as e:
                log_status(f"Erro no Agente Tributarista ({str(e)[:50]}...) - Processamento com limitações")
                resultado_tributarista = {'status': 'erro', 'erro': str(e), 'analise_riscos': {}}
            
            # CONCLUSÃO
            log_status("Processamento concluído! Redirecionando para revisão...")
            
            return {
                'status': 'sucesso',
                'timestamp_processamento': datetime.now().isoformat(),
                'validador': resultado_validador,
                'analista': resultado_analista,
                'tributarista': resultado_tributarista,
                'resumo_execucao': self._gerar_resumo_execucao(
                    resultado_validador, 
                    resultado_analista, 
                    resultado_tributarista
                )
            }
            
        except Exception as e:
            erro_msg = f"Erro crítico na orquestração: {str(e)}"
            log_status(erro_msg)
            return self._resultado_erro("Erro crítico", {'erro': str(e)})
    
    def _extrair_delta_total(self, resultado_tributarista: Dict[str, Any]) -> str:
        """Extrai informação resumida do delta calculado"""
        try:
            if 'analise_riscos' in resultado_tributarista:
                exposicao = resultado_tributarista['analise_riscos'].get('valor_total_exposicao', 0)
                if exposicao > 0:
                    return f"Delta de R$ {exposicao:,.2f} identificado"
            
            if 'calculo_multas' in resultado_tributarista:
                total_multas = resultado_tributarista['calculo_multas'].get('total_multas', 0)
                if total_multas > 0:
                    return f"Multas potenciais de R$ {total_multas:,.2f}"
            
            return "Análise financeira concluída"
            
        except Exception:
            return "Cálculos realizados"
    
    def _gerar_resumo_execucao(self, 
                             resultado_validador: Dict[str, Any],
                             resultado_analista: Dict[str, Any], 
                             resultado_tributarista: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resumo executivo da execução dos agentes"""
        
        return {
            'agentes_executados': 3,
            'validador_status': resultado_validador.get('status', 'erro'),
            'analista_status': resultado_analista.get('status', 'erro'),
            'tributarista_status': resultado_tributarista.get('status', 'erro'),
            'total_oportunidades': len(resultado_validador.get('oportunidades', [])),
            'total_discrepancias': len(resultado_validador.get('discrepancias', [])),
            'total_solucoes': len(resultado_analista.get('solucoes_propostas', [])),
            'produtos_analisados': resultado_validador.get('produtos_analisados', 0),
            'execucao_completa': all([
                resultado_validador.get('status') == 'sucesso',
                resultado_analista.get('status') in ['sucesso', 'parcial'],
                resultado_tributarista.get('status') in ['sucesso', 'parcial']
            ])
        }
    
    def _resultado_erro(self, tipo_erro: str, detalhes: Dict[str, Any]) -> Dict[str, Any]:
        """Padroniza resultado de erro"""
        return {
            'status': 'erro',
            'tipo_erro': tipo_erro,
            'timestamp_erro': datetime.now().isoformat(),
            'detalhes': detalhes,
            'validador': {'status': 'erro', 'oportunidades': [], 'discrepancias': []},
            'analista': {'status': 'erro', 'solucoes_propostas': []},
            'tributarista': {'status': 'erro', 'delta_impostos': {}},
            'resumo_execucao': {
                'agentes_executados': 0,
                'execucao_completa': False,
                'erro_critico': True
            }
        }

    def verificar_dependencias(self) -> Dict[str, bool]:
        """Verifica se todos os agentes estão prontos para execução"""
        return {
            'validador_pronto': self.validador.chain is not None,
            'analista_pronto': self.analista.chain is not None,
            'tributarista_pronto': self.tributarista.chain is not None,
            'todos_prontos': all([
                self.validador.chain is not None,
                self.analista.chain is not None,
                self.tributarista.chain is not None
            ])
        }


# Função de conveniência para uso direto
def processar_nfe_completa(cabecalho_df: pd.DataFrame, 
                          produtos_df: pd.DataFrame,
                          callback_status: Callable[[str], None] = None) -> Dict[str, Any]:
    """
    Função principal para processamento completo da NFe
    
    Args:
        cabecalho_df: DataFrame criptografado com dados do cabeçalho
        produtos_df: DataFrame criptografado com dados dos produtos
        callback_status: Função callback para atualizar status na interface
        
    Returns:
        dict: Resultado consolidado dos 3 agentes
    """
    orquestrador = OrquestradorAgentes()
    return orquestrador.processar_sequencial(cabecalho_df, produtos_df, callback_status)


if __name__ == "__main__":
    print("Orquestrador de Agentes - Sistema de Coordenação Fiscal")
    
    # Teste de dependências
    orq = OrquestradorAgentes()
    deps = orq.verificar_dependencias()
    
    print(f"Validador: {'Pronto' if deps['validador_pronto'] else 'Erro'}")
    print(f"Analista: {'Pronto' if deps['analista_pronto'] else 'Erro'}")
    print(f"Tributarista: {'Pronto' if deps['tributarista_pronto'] else 'Erro'}")
    print(f"Sistema: {'Operacional' if deps['todos_prontos'] else 'Requer configuração'}")