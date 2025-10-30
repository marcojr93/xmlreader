import streamlit as st
import pandas as pd
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import io
import base64
from typing import Dict, Any, List, Tuple
import os
import sys
import re

# Adicionar o diretório pai ao path para importações
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from criptografia import SecureDataProcessor
from agents.validador import ValidadorFiscal
from view.main import gerar_relatorio_pdf

def exibir_pagina_revisao():
    """Função principal de revisão chamada pela main.py"""
    st.title("Revisão e Correção de NFe")
    st.markdown("---")
    
    # Carregar dados do arquivo temporário
    dados_temp = carregar_dados_temporarios()
    if not dados_temp:
        st.error("Dados temporários não encontrados. Execute o processamento dos agentes primeiro.")
        return
    
    # Restaurar dados na sessão se não existirem
    restaurar_dados_sessao(dados_temp)
    
    # Inicializar componentes
    processor = SecureDataProcessor()
    
    # Layout em colunas
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Dados da NFe")
        exibir_resumo_nfe()
    
    with col2:
        st.subheader("Ações")
        exibir_painel_acoes()
    
    st.markdown("---")
    
    # Seção principal de insights e edição
    tab1, tab2, tab3 = st.tabs(["Edição Completa XML", "Insights dos Agentes", "Export & Relatórios"])
    
    with tab1:
        exibir_edicao_completa_xml(processor)
    
    with tab2:
        exibir_insights_validador()
    
    with tab3:
        exibir_opcoes_export(processor)

# Funções de verificação removidas - não necessárias com sistema de abas

def exibir_resumo_nfe():
    """Exibe resumo básico da NFe carregada"""
    try:
        processor = SecureDataProcessor()
        
        # Descriptografar APENAS campos necessários para exibição (SEM CNPJs)
        campos_exibicao = ['UF', 'Valor Total', 'Razão Social']
        cabecalho = processor.decrypt_sensitive_data(st.session_state.cabecalho_df, campos_exibicao)
        
        # Para produtos, usar apenas campos não sensíveis
        campos_produtos_seguros = ['Produto', 'NCM', 'Quantidade', 'Valor Total']
        produtos = processor.decrypt_sensitive_data(st.session_state.produtos_df, campos_produtos_seguros)
        
        # Informações básicas
        st.info(f"**Arquivo:** {st.session_state.arquivo_xml_nome}")
        
        # Dados do cabeçalho
        if not cabecalho.empty:
            linha = cabecalho.iloc[0]
            col1, col2 = st.columns(2)
            
            with col1:
                razao_social = str(linha.get('Razão Social', 'N/A'))
                empresa_display = razao_social[:20] + "..." if len(razao_social) > 20 else razao_social
                st.metric("Empresa", empresa_display)
                st.metric("UF", linha.get('UF', 'N/A'))
            
            with col2:
                valor_total = linha.get('Valor Total', 0)
                # Garantir que valor_total é numérico
                try:
                    valor_num = float(valor_total) if valor_total is not None else 0.0
                    st.metric("Valor Total", f"R$ {valor_num:,.2f}")
                except (ValueError, TypeError):
                    st.metric("Valor Total", "R$ 0,00")
                st.metric("Produtos", len(produtos))
        
    except Exception as e:
        st.error(f"Erro ao carregar resumo: {str(e)}")

def exibir_painel_acoes():
    """Painel com ações rápidas"""
    st.markdown("### Ações Rápidas")
    
    if st.button("Revalidar NFe", use_container_width=True):
        revalidar_nfe()
    
    if st.button("Salvar Alterações", use_container_width=True):
        salvar_alteracoes()
    
    if st.button("Exportar XML", use_container_width=True):
        exportar_xml_corrigido()
    
    st.markdown("---")
    
    # Estatísticas rápidas dos 3 agentes
    resultado_validador = st.session_state.get('resultado_validador', {})
    resultado_analista = st.session_state.get('resultado_analista', {})
    resultado_tributarista = st.session_state.get('resultado_tributarista', {})
    
    st.metric("Oportunidades", len(resultado_validador.get('oportunidades', [])))
    st.metric("Discrepâncias", len(resultado_validador.get('discrepancias', [])))
    st.metric("Soluções", len(resultado_analista.get('solucoes_propostas', [])))
    
    # Exposição financeira do tributarista
    analise_riscos = resultado_tributarista.get('analise_riscos', {})
    exposicao = analise_riscos.get('valor_total_exposicao', 0)
    # Garantir que exposicao é numérico
    try:
        exposicao_num = float(exposicao) if exposicao is not None else 0.0
        if exposicao_num > 0:
            st.metric("Exposição", f"R$ {exposicao_num:,.0f}")
    except (ValueError, TypeError):
        # Se não conseguir converter para número, não exibir métrica
        pass

def exibir_insights_validador():
    """Exibe os insights e análises dos agentes fiscais"""
    st.subheader("Análise Fiscal Inteligente")
    
    # Usar resultado do validador já processado
    resultado = st.session_state.get('resultado_validador', {})
    
    # Status da análise
    status_emoji = {"sucesso": "", "erro": "", "parcial": ""}
    status = resultado.get('status', 'erro')
    emoji = status_emoji.get(status, "")
    
    st.markdown(f"**{emoji} Status da Análise:** {status.title()}")
    
    # Se houver erro, mostrar e parar
    if status == 'erro':
        st.error("Erro na análise fiscal. Verifique a configuração da API.")
        st.code(resultado.get('resumo_dropdown', 'Erro desconhecido'))
        return
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Produtos Analisados", resultado.get('produtos_analisados', 0))
    
    with col2:
        st.metric("Oportunidades", len(resultado.get('oportunidades', [])))
    
    with col3:
        st.metric("Discrepâncias", len(resultado.get('discrepancias', [])))
    
    with col4:
        st.metric("Modelo IA", resultado.get('modelo_utilizado', 'N/A'))
    
    # Resumo executivo
    if resultado.get('resumo_executivo'):
        st.markdown("### Resumo Executivo")
        st.markdown(resultado['resumo_executivo'])
    
    # Oportunidades
    oportunidades = resultado.get('oportunidades', [])
    if oportunidades:
        st.markdown("### Oportunidades Identificadas")
        
        for i, oport in enumerate(oportunidades):
            with st.expander(f"💡 {oport.get('tipo', 'Oportunidade')} - {oport.get('produto', 'N/A')}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Descrição:** {oport.get('descricao', 'N/A')}")
                    st.markdown(f"**Impacto:** {oport.get('impacto', 'N/A')}")
                    st.markdown(f"**Ação Recomendada:** {oport.get('acao_recomendada', 'N/A')}")
                
                with col2:
                    if st.button(f"✏️ Editar", key=f"edit_oport_{i}"):
                        st.session_state[f'editar_produto_{i}'] = oport.get('produto', '')
                        st.rerun()
    
    # Discrepâncias
    discrepancias = resultado.get('discrepancias', [])
    if discrepancias:
        st.markdown("### Discrepâncias Encontradas")
        
        for i, disc in enumerate(discrepancias):
            gravidade = disc.get('gravidade', 'Média')
            cor = {"Alta": "🔴", "Média": "🟡", "Baixa": "🟢"}.get(gravidade, "⚪")
            
            with st.expander(f"{cor} {disc.get('tipo', 'Discrepância')} - {disc.get('produto', 'N/A')}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Problema:** {disc.get('problema', 'N/A')}")
                    st.markdown(f"**Gravidade:** {gravidade}")
                    st.markdown(f"**Correção Sugerida:** {disc.get('correcao', 'N/A')}")
                
                with col2:
                    if st.button(f"Corrigir", key=f"fix_disc_{i}"):
                        st.session_state[f'corrigir_produto_{i}'] = disc.get('produto', '')
                        st.rerun()
    
    # Detalhes técnicos
    if resultado.get('detalhes_tecnicos'):
        with st.expander("Detalhes Técnicos"):
            st.markdown(resultado['detalhes_tecnicos'])
    
    # Insights do Analista
    st.markdown("---")
    st.subheader("🔬 Insights do Analista Fiscal")
    resultado_analista = st.session_state.get('resultado_analista', {})
    
    if resultado_analista.get('status') == 'sucesso':
        solucoes = resultado_analista.get('solucoes_propostas', [])
        if solucoes:
            for i, solucao in enumerate(solucoes):
                with st.expander(f"💡 Solução {i+1}: {solucao.get('tipo_solucao', 'N/A')}"):
                    st.write(f"**Discrepância:** {solucao.get('discrepancia_origem', 'N/A')}")
                    st.write(f"**Solução:** {solucao.get('solucao_detalhada', 'N/A')}")
                    st.write(f"**Impacto:** {solucao.get('impacto_esperado', 'N/A')}")
        else:
            st.info("Nenhuma solução adicional necessária - análise validador suficiente")
    else:
        st.warning("Analista encontrou limitações no processamento")
    
    # Insights do Tributarista
    st.markdown("---")
    st.subheader("Cálculos do Tributarista")
    resultado_tributarista = st.session_state.get('resultado_tributarista', {})
    
    if resultado_tributarista.get('status') == 'sucesso':
        # Delta de impostos
        delta_impostos = resultado_tributarista.get('delta_impostos', {})
        if delta_impostos:
            with st.expander("Delta de Impostos", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    icms = delta_impostos.get('icms', {})
                    delta_icms = icms.get('delta', 0)
                    try:
                        delta_icms_num = float(delta_icms) if delta_icms is not None else 0.0
                        st.metric("ICMS Delta", f"R$ {delta_icms_num:,.2f}")
                    except (ValueError, TypeError):
                        st.metric("ICMS Delta", "R$ 0,00")
                
                with col2:
                    pis_cofins = delta_impostos.get('pis_cofins', {})
                    delta_pis_cofins = pis_cofins.get('delta_total', 0)
                    try:
                        delta_pis_cofins_num = float(delta_pis_cofins) if delta_pis_cofins is not None else 0.0
                        st.metric("PIS/COFINS Delta", f"R$ {delta_pis_cofins_num:,.2f}")
                    except (ValueError, TypeError):
                        st.metric("PIS/COFINS Delta", "R$ 0,00")
                
                with col3:
                    ipi = delta_impostos.get('ipi', {})
                    delta_ipi = ipi.get('delta', 0)
                    try:
                        delta_ipi_num = float(delta_ipi) if delta_ipi is not None else 0.0
                        st.metric("🏭 IPI Delta", f"R$ {delta_ipi_num:,.2f}")
                    except (ValueError, TypeError):
                        st.metric("🏭 IPI Delta", "R$ 0,00")
        
        # Multas potenciais
        calculo_multas = resultado_tributarista.get('calculo_multas', {})
        if calculo_multas:
            total_multas = calculo_multas.get('total_multas', 0)
            try:
                total_multas_num = float(total_multas) if total_multas is not None else 0.0
                if total_multas_num > 0:
                    with st.expander("Multas Potenciais"):
                        st.metric("💸 Total de Multas", f"R$ {total_multas_num:,.2f}")
                        
                        multas = calculo_multas.get('multas_potenciais', [])
                        for multa in multas:
                            valor_multa = multa.get('valor_multa', 0)
                            try:
                                valor_multa_num = float(valor_multa) if valor_multa is not None else 0.0
                                st.write(f"• **{multa.get('tipo_infracao', 'N/A')}**: R$ {valor_multa_num:,.2f}")
                            except (ValueError, TypeError):
                                st.write(f"• **{multa.get('tipo_infracao', 'N/A')}**: R$ 0,00")
            except (ValueError, TypeError):
                pass
        
        # Análise de riscos
        analise_riscos = resultado_tributarista.get('analise_riscos', {})
        if analise_riscos:
            with st.expander("Análise de Riscos"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Risco de Autuação:** {analise_riscos.get('risco_autuacao', 'N/A')}")
                    valor_exposicao = analise_riscos.get('valor_total_exposicao', 0)
                    try:
                        valor_exposicao_num = float(valor_exposicao) if valor_exposicao is not None else 0.0
                        st.write(f"**Exposição Total:** R$ {valor_exposicao_num:,.2f}")
                    except (ValueError, TypeError):
                        st.write("**Exposição Total:** R$ 0,00")
                
                with col2:
                    recomendacoes = analise_riscos.get('recomendacoes_urgentes', [])
                    if recomendacoes:
                        st.write("**Recomendações Urgentes:**")
                        for rec in recomendacoes:
                            st.write(f"• {rec}")
    else:
        st.warning("Tributarista encontrou limitações nos cálculos")

def exibir_interface_edicao(processor: SecureDataProcessor):
    """Interface para editar produtos com base nos insights"""
    st.subheader("✏️ Edição de Produtos")
    
    try:
        # Descriptografar APENAS campos editáveis (SEM dados sensíveis como CNPJs)
        campos_editaveis = [
            'Produto', 'NCM', 'CFOP', 'Quantidade', 'Valor Unitário', 'Valor Total',
            'Alíquota ICMS', 'Valor ICMS', 'Alíquota PIS', 'Valor PIS',
            'Alíquota COFINS', 'Valor COFINS', 'Alíquota IPI', 'Valor IPI'
        ]
        produtos = processor.decrypt_sensitive_data(st.session_state.produtos_df, campos_editaveis)
        
        if produtos.empty:
            st.warning("Nenhum produto encontrado para edição.")
            return
        
        # Seletor de produto
        produtos_lista = produtos['Produto'].tolist() if 'Produto' in produtos.columns else [f"Produto {i+1}" for i in range(len(produtos))]
        
        produto_selecionado = st.selectbox(
            "Selecione o produto para editar:",
            produtos_lista,
            key="produto_edicao"
        )
        
        if produto_selecionado:
            idx_produto = produtos_lista.index(produto_selecionado)
            produto_dados = produtos.iloc[idx_produto]
            
            # Interface de edição
            st.markdown(f"### Editando: **{produto_selecionado}**")
            
            # Criar formulário de edição
            with st.form(f"form_produto_{idx_produto}"):
                col1, col2 = st.columns(2)
                
                # Campos editáveis principais
                campos_edicao = {}
                
                with col1:
                    st.markdown("#### Dados Fiscais")
                    
                    # NCM
                    if 'NCM' in produto_dados:
                        campos_edicao['NCM'] = st.text_input(
                            "NCM", 
                            value=str(produto_dados['NCM']),
                            help="Nomenclatura Comum do Mercosul"
                        )
                    
                    # CFOP
                    if 'CFOP' in produto_dados:
                        campos_edicao['CFOP'] = st.text_input(
                            "CFOP", 
                            value=str(produto_dados['CFOP']),
                            help="Código Fiscal de Operações e Prestações"
                        )
                    
                    # Alíquotas ICMS
                    if 'Alíquota ICMS' in produto_dados:
                        aliquota_icms = str(produto_dados['Alíquota ICMS']).replace('%', '')
                        campos_edicao['Alíquota ICMS'] = st.number_input(
                            "Alíquota ICMS (%)", 
                            value=float(aliquota_icms) if aliquota_icms.replace('.', '').isdigit() else 0.0,
                            min_value=0.0,
                            max_value=30.0,
                            step=0.01
                        )
                
                with col2:
                    st.markdown("#### Valores")
                    
                    # Quantidade
                    if 'Quantidade' in produto_dados:
                        campos_edicao['Quantidade'] = st.number_input(
                            "Quantidade", 
                            value=float(produto_dados['Quantidade']) if pd.notna(produto_dados['Quantidade']) else 1.0,
                            min_value=0.01,
                            step=0.01
                        )
                    
                    # Valor Unitário
                    if 'Valor Unitário' in produto_dados:
                        campos_edicao['Valor Unitário'] = st.number_input(
                            "Valor Unitário (R$)", 
                            value=float(produto_dados['Valor Unitário']) if pd.notna(produto_dados['Valor Unitário']) else 0.0,
                            min_value=0.0,
                            step=0.01
                        )
                    
                    # PIS/COFINS
                    if 'Alíquota PIS' in produto_dados:
                        aliquota_pis = str(produto_dados['Alíquota PIS']).replace('%', '')
                        campos_edicao['Alíquota PIS'] = st.number_input(
                            "Alíquota PIS (%)", 
                            value=float(aliquota_pis) if aliquota_pis.replace('.', '').isdigit() else 0.0,
                            min_value=0.0,
                            max_value=10.0,
                            step=0.01
                        )
                
                # Mostrar insights relacionados ao produto
                mostrar_insights_produto(produto_selecionado)
                
                # Botões de ação
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    aplicar_mudancas = st.form_submit_button("💾 Aplicar Mudanças", use_container_width=True)
                
                with col2:
                    resetar = st.form_submit_button("🔄 Resetar", use_container_width=True)
                
                with col3:
                    preview = st.form_submit_button("👁️ Preview", use_container_width=True)
                
                # Processar ações do formulário
                if aplicar_mudancas:
                    aplicar_edicoes_produto(processor, idx_produto, campos_edicao)
                
                if resetar:
                    st.rerun()
                
                if preview:
                    mostrar_preview_alteracoes(produto_dados, campos_edicao)
                    
    except Exception as e:
        st.error(f"Erro na interface de edição: {str(e)}")

def mostrar_insights_produto(produto_nome: str):
    """Mostra insights específicos do produto selecionado"""
    if 'resultado_validacao' not in st.session_state:
        return
    
    resultado = st.session_state.resultado_validacao
    insights_produto = []
    
    # Buscar oportunidades para este produto
    for oport in resultado.get('oportunidades', []):
        if produto_nome.lower() in oport.get('produto', '').lower():
            insights_produto.append(('Oportunidade', oport))
    
    # Buscar discrepâncias para este produto
    for disc in resultado.get('discrepancias', []):
        if produto_nome.lower() in disc.get('produto', '').lower():
            insights_produto.append(('Discrepância', disc))
    
    if insights_produto:
        st.markdown("#### 💡 Insights para este Produto")
        
        for tipo, insight in insights_produto:
            with st.expander(f"{tipo}: {insight.get('tipo', 'N/A')}"):
                if 'descricao' in insight:
                    st.write(f"**Descrição:** {insight['descricao']}")
                if 'problema' in insight:
                    st.write(f"**Problema:** {insight['problema']}")
                if 'acao_recomendada' in insight:
                    st.write(f"**Ação:** {insight['acao_recomendada']}")
                if 'correcao' in insight:
                    st.write(f"**Correção:** {insight['correcao']}")

def aplicar_edicoes_produto(processor: SecureDataProcessor, idx_produto: int, campos_edicao: Dict[str, Any]):
    """Aplica as edições ao produto selecionado"""
    try:
        # Descriptografar APENAS campos editáveis (preserva dados sensíveis criptografados)
        campos_editaveis = [
            'Produto', 'NCM', 'CFOP', 'Quantidade', 'Valor Unitário', 'Valor Total',
            'Alíquota ICMS', 'Valor ICMS', 'Alíquota PIS', 'Valor PIS',
            'Alíquota COFINS', 'Valor COFINS', 'Alíquota IPI', 'Valor IPI'
        ]
        produtos = processor.decrypt_sensitive_data(st.session_state.produtos_df, campos_editaveis)
        
        # Aplicar mudanças
        for campo, valor in campos_edicao.items():
            if campo in produtos.columns:
                if campo in ['Alíquota ICMS', 'Alíquota PIS', 'Alíquota COFINS']:
                    produtos.iloc[idx_produto, produtos.columns.get_loc(campo)] = f"{valor}%"
                else:
                    produtos.iloc[idx_produto, produtos.columns.get_loc(campo)] = valor
        
        # Recalcular valores dependentes
        if 'Quantidade' in campos_edicao and 'Valor Unitário' in campos_edicao:
            valor_total = campos_edicao['Quantidade'] * campos_edicao['Valor Unitário']
            if 'Valor Total' in produtos.columns:
                produtos.iloc[idx_produto, produtos.columns.get_loc('Valor Total')] = valor_total
        
        # Criptografar e salvar de volta
        produtos_criptografados = processor.encrypt_sensitive_data(produtos)
        st.session_state.produtos_df = produtos_criptografados
        
        # Marcar como editado
        if 'alteracoes_realizadas' not in st.session_state:
            st.session_state.alteracoes_realizadas = []
        
        st.session_state.alteracoes_realizadas.append({
            'produto': produtos.iloc[idx_produto]['Produto'] if 'Produto' in produtos.columns else f'Produto {idx_produto+1}',
            'campos': list(campos_edicao.keys()),
            'timestamp': datetime.now().isoformat()
        })
        
        st.success("Alterações aplicadas com sucesso!")
        
        # Invalidar validação anterior para forçar nova análise
        if 'resultado_validacao' in st.session_state:
            del st.session_state.resultado_validacao
        
    except Exception as e:
        st.error(f"Erro ao aplicar alterações: {str(e)}")

def mostrar_preview_alteracoes(produto_original: pd.Series, campos_edicao: Dict[str, Any]):
    """Mostra preview das alterações antes de aplicar"""
    st.markdown("#### 👁️ Preview das Alterações")
    
    mudancas = []
    for campo, novo_valor in campos_edicao.items():
        if campo in produto_original:
            valor_original = produto_original[campo]
            
            # Formatação especial para alíquotas
            if campo in ['Alíquota ICMS', 'Alíquota PIS', 'Alíquota COFINS']:
                valor_original_fmt = str(valor_original)
                novo_valor_fmt = f"{novo_valor}%"
            else:
                valor_original_fmt = str(valor_original)
                novo_valor_fmt = str(novo_valor)
            
            if valor_original_fmt != novo_valor_fmt:
                mudancas.append({
                    'campo': campo,
                    'original': valor_original_fmt,
                    'novo': novo_valor_fmt
                })
    
    if mudancas:
        for mudanca in mudancas:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**{mudanca['campo']}**")
            with col2:
                st.write(f"~~{mudanca['original']}~~")
            with col3:
                st.write(f"{mudanca['novo']}")
    else:
        st.info("Nenhuma alteração detectada.")

def exibir_opcoes_export(processor: SecureDataProcessor):
    """Opções de exportação e relatórios"""
    st.subheader("Exportação e Relatórios")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Exportar Dados")
        
        if st.button("Exportar Planilha Excel", use_container_width=True):
            exportar_excel(processor)
        
        if st.button("Exportar CSV", use_container_width=True):
            exportar_csv(processor)
        
        if st.button("Download XML Corrigido", use_container_width=True):
            exportar_xml_corrigido()
        
        if st.button("Visualizar XML Revisado", use_container_width=True):
            visualizar_xml_dropdown(processor)
    
    with col2:
        st.markdown("### Relatórios")
        
        # Botão de download PDF direto (sem rerun)
        if 'resultado_validador' in st.session_state and 'resultado_analista' in st.session_state and 'resultado_tributarista' in st.session_state:
            try:
                resultado_completo = {
                    'validador': st.session_state.resultado_validador,
                    'analista': st.session_state.resultado_analista,
                    'tributarista': st.session_state.resultado_tributarista,
                    'timestamp_processamento': st.session_state.get('timestamp_processamento', datetime.now().strftime('%Y-%m-%d_%H-%M-%S')),
                    'resumo_execucao': st.session_state.get('resumo_execucao', {})
                }
                
                pdf_data = gerar_relatorio_pdf(resultado_completo, st.session_state.get('arquivo_xml_nome', 'arquivo'))
                if pdf_data:
                    st.download_button(
                        label="Download Relatório PDF Completo",
                        data=pdf_data,
                        file_name=f"relatorio_fiscal_{resultado_completo.get('timestamp_processamento', 'unknown').replace(':', '-')[:19]}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {str(e)}")
        
        if st.button("Relatório de Alterações", use_container_width=True):
            gerar_relatorio_alteracoes()
        
        if st.button("Relatório de Oportunidades", use_container_width=True):
            gerar_relatorio_oportunidades()
        
        if st.button("Ver Relatório Tributário Completo", use_container_width=True):
            exibir_relatorio_tributarista_completo()
        
        if st.button("Relatório de Discrepâncias", use_container_width=True):
            gerar_relatorio_discrepancias()
    
    # Histórico de alterações
    if 'alteracoes_realizadas' in st.session_state and st.session_state.alteracoes_realizadas:
        st.markdown("### 📝 Histórico de Alterações")
        
        for i, alteracao in enumerate(st.session_state.alteracoes_realizadas):
            with st.expander(f"✏️ {alteracao['produto']} - {alteracao['timestamp'][:19]}"):
                st.write(f"**Campos alterados:** {', '.join(alteracao['campos'])}")

def revalidar_nfe():
    """Revalida a NFe após alterações usando orquestração completa"""
    try:
        with st.spinner("🔄 Reprocessando com todos os agentes..."):
            from agents.orquestrador import processar_nfe_completa
            
            def callback_simples(msg):
                st.write(msg)
            
            # Reprocessar com orquestração completa
            resultado_completo = processar_nfe_completa(
                st.session_state.cabecalho_df,
                st.session_state.produtos_df,
                callback_simples
            )
            
            # Atualizar resultados na sessão
            st.session_state.resultado_validador = resultado_completo.get('validador', {})
            st.session_state.resultado_analista = resultado_completo.get('analista', {})
            st.session_state.resultado_tributarista = resultado_completo.get('tributarista', {})
            
        st.success("Reprocessamento completo realizado!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Erro no reprocessamento: {str(e)}")

def salvar_alteracoes():
    """Salva as alterações realizadas"""
    if 'alteracoes_realizadas' not in st.session_state or not st.session_state.alteracoes_realizadas:
        st.warning("Nenhuma alteração para salvar.")
        return
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"nfe_editada_{timestamp}.json"
        
        dados_para_salvar = {
            'arquivo_original': st.session_state.arquivo_xml_nome,
            'alteracoes': st.session_state.alteracoes_realizadas,
            'timestamp': timestamp,
            'total_alteracoes': len(st.session_state.alteracoes_realizadas)
        }
        
        # Simular salvamento (em produção, salvaria em arquivo)
        st.success(f"Alterações salvas como: {nome_arquivo}")
        st.json(dados_para_salvar)
        
    except Exception as e:
        st.error(f"Erro ao salvar: {str(e)}")

def exportar_xml_corrigido():
    """Exporta XML com as correções aplicadas"""
    try:
        processor = SecureDataProcessor()
        # Descriptografar APENAS campos não sensíveis para export XML
        campos_export_cabecalho = ['Natureza da Operação', 'CFOP', 'UF', 'Valor Total', 'Data']
        campos_export_produtos = [
            'Produto', 'NCM', 'CFOP', 'Quantidade', 'Valor Unitário', 'Valor Total',
            'Alíquota ICMS', 'Valor ICMS', 'Alíquota PIS', 'Valor PIS',
            'Alíquota COFINS', 'Valor COFINS', 'Alíquota IPI', 'Valor IPI'
        ]
        cabecalho = processor.decrypt_sensitive_data(st.session_state.cabecalho_df, campos_export_cabecalho)
        produtos = processor.decrypt_sensitive_data(st.session_state.produtos_df, campos_export_produtos)
        
        # Gerar XML básico com os dados revisados
        xml_content = gerar_xml_revisado(cabecalho, produtos)
        
        st.download_button(
            label="� Download XML Revisado",
            data=xml_content,
            file_name=f"nfe_revisada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
            mime="application/xml"
        )
        
    except Exception as e:
        st.error(f"Erro ao exportar XML: {str(e)}")

def visualizar_xml_dropdown(processor: SecureDataProcessor):
    """Visualiza as informações do XML revisado em dropdown"""
    try:
        # Descriptografar APENAS campos seguros para visualização
        campos_viz_cabecalho = ['Razão Social', 'UF', 'Natureza da Operação', 'CFOP', 'Valor Total']
        campos_viz_produtos = [
            'Produto', 'NCM', 'CFOP', 'Quantidade', 'Valor Unitário', 'Valor Total',
            'Alíquota ICMS', 'Valor ICMS', 'Alíquota PIS', 'Valor PIS',
            'Alíquota COFINS', 'Valor COFINS'
        ]
        cabecalho = processor.decrypt_sensitive_data(st.session_state.cabecalho_df, campos_viz_cabecalho)
        produtos = processor.decrypt_sensitive_data(st.session_state.produtos_df, campos_viz_produtos)
        
        st.markdown("### 👁️ Visualização do XML Revisado")
        
        # Informações do cabeçalho
        with st.expander("Dados do Cabeçalho", expanded=True):
            if not cabecalho.empty:
                linha = cabecalho.iloc[0]
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Razão Social:** {linha.get('Razão Social', 'N/A')}")
                    st.write(f"**UF:** {linha.get('UF', 'N/A')}")
                    st.write(f"**CFOP:** {linha.get('CFOP', 'N/A')}")
                
                with col2:
                    st.write(f"**Natureza da Operação:** {linha.get('Natureza da Operação', 'N/A')}")
                    st.write(f"**CFOP:** {linha.get('CFOP', 'N/A')}")
                    valor_total = linha.get('Valor Total', 0)
                    try:
                        valor_total_num = float(valor_total) if valor_total is not None else 0.0
                        st.write(f"**Valor Total:** R$ {valor_total_num:,.2f}")
                    except (ValueError, TypeError):
                        st.write("**Valor Total:** R$ 0,00")
        
        # Produtos revisados
        with st.expander("Produtos Revisados", expanded=True):
            st.dataframe(
                produtos,
                use_container_width=True,
                hide_index=True
            )
        
        # Resumo das alterações
        if 'alteracoes_realizadas' in st.session_state and st.session_state.alteracoes_realizadas:
            with st.expander("✏️ Resumo das Alterações"):
                for i, alt in enumerate(st.session_state.alteracoes_realizadas, 1):
                    st.write(f"**{i}.** {alt['produto']}")
                    st.write(f"   📝 Campos alterados: {', '.join(alt['campos'])}")
                    st.write(f"   🕐 Data: {alt['timestamp'][:19]}")
                    st.write("---")
        
        # Análise fiscal atual
        if 'resultado_validacao' in st.session_state:
            resultado = st.session_state.resultado_validacao
            with st.expander("Status da Análise Fiscal"):
                st.write(f"**Status:** {resultado.get('status', 'N/A')}")
                st.write(f"**Produtos Analisados:** {resultado.get('produtos_analisados', 0)}")
                st.write(f"**Oportunidades:** {len(resultado.get('oportunidades', []))}")
                st.write(f"**Discrepâncias:** {len(resultado.get('discrepancias', []))}")
        
    except Exception as e:
        st.error(f"Erro na visualização: {str(e)}")

def gerar_xml_revisado(cabecalho: pd.DataFrame, produtos: pd.DataFrame) -> str:
    """Gera conteúdo XML com os dados revisados"""
    try:
        # Função para limpar nomes de tags XML
        def limpar_nome_tag(nome):
            # Remove caracteres especiais e espaços, substitui por underscore
            nome_limpo = re.sub(r'[^a-zA-Z0-9_]', '_', nome)
            # Remove underscores múltiplos
            nome_limpo = re.sub(r'_+', '_', nome_limpo)
            # Remove underscore no início e fim
            nome_limpo = nome_limpo.strip('_')
            # Garante que comece com letra
            if nome_limpo and nome_limpo[0].isdigit():
                nome_limpo = 'field_' + nome_limpo
            return nome_limpo.lower() if nome_limpo else 'field_unknown'
        
        # Função para escapar conteúdo XML
        def escapar_xml(texto):
            if texto is None:
                return ''
            texto_str = str(texto)
            # Escapar caracteres especiais XML
            texto_str = texto_str.replace('&', '&amp;')
            texto_str = texto_str.replace('<', '&lt;')  
            texto_str = texto_str.replace('>', '&gt;')
            texto_str = texto_str.replace('"', '&quot;')
            texto_str = texto_str.replace("'", '&apos;')
            return texto_str
        
        # Estrutura XML básica
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<nfe_revisada>',
            '  <metadata>',
            f'    <data_revisao>{datetime.now().isoformat()}</data_revisao>',
            f'    <arquivo_original>{escapar_xml(st.session_state.get("arquivo_xml_nome", "N/A"))}</arquivo_original>',
            '  </metadata>',
            '  <cabecalho>'
        ]
        
        # Adicionar dados do cabeçalho
        if not cabecalho.empty:
            linha = cabecalho.iloc[0]
            for coluna, valor in linha.items():
                if pd.notna(valor):
                    tag_name = limpar_nome_tag(coluna)
                    valor_escapado = escapar_xml(valor)
                    xml_lines.append(f'    <{tag_name}>{valor_escapado}</{tag_name}>')
        
        xml_lines.append('  </cabecalho>')
        xml_lines.append('  <produtos>')
        
        # Adicionar produtos
        for idx, produto in produtos.iterrows():
            xml_lines.append(f'    <produto id="{idx + 1}">')
            for coluna, valor in produto.items():
                if pd.notna(valor):
                    tag_name = limpar_nome_tag(coluna)
                    valor_escapado = escapar_xml(valor)
                    xml_lines.append(f'      <{tag_name}>{valor_escapado}</{tag_name}>')
            xml_lines.append('    </produto>')
        
        xml_lines.append('  </produtos>')
        
        # Adicionar alterações se existirem
        if 'alteracoes_realizadas' in st.session_state and st.session_state.alteracoes_realizadas:
            xml_lines.append('  <alteracoes>')
            for alt in st.session_state.alteracoes_realizadas:
                xml_lines.append('    <alteracao>')
                xml_lines.append(f'      <produto>{alt["produto"]}</produto>')
                xml_lines.append(f'      <campos>{", ".join(alt["campos"])}</campos>')
                xml_lines.append(f'      <timestamp>{alt["timestamp"]}</timestamp>')
                xml_lines.append('    </alteracao>')
            xml_lines.append('  </alteracoes>')
        
        xml_lines.append('</nfe_revisada>')
        
        return '\n'.join(xml_lines)
        
    except Exception as e:
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<erro>Erro ao gerar XML: {str(e)}</erro>'

def exportar_excel(processor: SecureDataProcessor):
    """Exporta dados para Excel"""
    try:
        # Export APENAS campos não sensíveis para Excel
        campos_export_cabecalho = ['Razão Social', 'UF', 'Natureza da Operação', 'CFOP', 'Valor Total', 'Data']
        campos_export_produtos = [
            'Produto', 'NCM', 'CFOP', 'Quantidade', 'Valor Unitário', 'Valor Total',
            'Alíquota ICMS', 'Valor ICMS', 'Alíquota PIS', 'Valor PIS',
            'Alíquota COFINS', 'Valor COFINS', 'Alíquota IPI', 'Valor IPI'
        ]
        cabecalho = processor.decrypt_sensitive_data(st.session_state.cabecalho_df, campos_export_cabecalho)
        produtos = processor.decrypt_sensitive_data(st.session_state.produtos_df, campos_export_produtos)
        
        # Criar buffer para Excel
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            cabecalho.to_excel(writer, sheet_name='Cabeçalho', index=False)
            produtos.to_excel(writer, sheet_name='Produtos', index=False)
            
            if 'alteracoes_realizadas' in st.session_state:
                alteracoes_df = pd.DataFrame(st.session_state.alteracoes_realizadas)
                alteracoes_df.to_excel(writer, sheet_name='Alterações', index=False)
        
        buffer.seek(0)
        
        st.download_button(
            label="Download Excel",
            data=buffer.getvalue(),
            file_name=f"nfe_revisada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"Erro no export Excel: {str(e)}")

def exportar_csv(processor: SecureDataProcessor):
    """Exporta dados para CSV"""
    try:
        # Export CSV APENAS com campos não sensíveis
        campos_export_produtos = [
            'Produto', 'NCM', 'CFOP', 'Quantidade', 'Valor Unitário', 'Valor Total',
            'Alíquota ICMS', 'Valor ICMS', 'Alíquota PIS', 'Valor PIS',
            'Alíquota COFINS', 'Valor COFINS', 'Alíquota IPI', 'Valor IPI'
        ]
        produtos = processor.decrypt_sensitive_data(st.session_state.produtos_df, campos_export_produtos)
        
        csv_buffer = io.StringIO()
        produtos.to_csv(csv_buffer, index=False, encoding='utf-8')
        
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name=f"produtos_revisados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Erro no export CSV: {str(e)}")

def gerar_relatorio_alteracoes():
    """Gera relatório das alterações realizadas"""
    if 'alteracoes_realizadas' not in st.session_state or not st.session_state.alteracoes_realizadas:
        st.warning("Nenhuma alteração registrada.")
        return
    
    st.markdown("### Relatório de Alterações")
    
    alteracoes = st.session_state.alteracoes_realizadas
    
    # Estatísticas
    total_alteracoes = len(alteracoes)
    produtos_editados = len(set([alt['produto'] for alt in alteracoes]))
    campos_mais_editados = pd.Series([campo for alt in alteracoes for campo in alt['campos']]).value_counts()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Alterações", total_alteracoes)
    with col2:
        st.metric("Produtos Editados", produtos_editados)
    with col3:
        st.metric("Sessões de Edição", len(alteracoes))
    
    # Campos mais editados
    if not campos_mais_editados.empty:
        st.markdown("#### Campos Mais Editados")
        st.bar_chart(campos_mais_editados)
    
    # Lista detalhada
    st.markdown("#### 📝 Detalhes das Alterações")
    for i, alt in enumerate(alteracoes, 1):
        st.write(f"**{i}.** {alt['produto']} - {alt['timestamp'][:19]}")
        st.write(f"   Campos: {', '.join(alt['campos'])}")

def gerar_relatorio_oportunidades():
    """Gera relatório de oportunidades fiscais"""
    if 'resultado_validacao' not in st.session_state:
        st.warning("Execute a validação primeiro.")
        return
    
    oportunidades = st.session_state.resultado_validacao.get('oportunidades', [])
    
    if not oportunidades:
        st.info("Nenhuma oportunidade identificada.")
        return
    
    st.markdown("### Relatório de Oportunidades")
    
    # Categorizar oportunidades
    categorias = {}
    for oport in oportunidades:
        categoria = oport.get('tipo', 'Outras')
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append(oport)
    
    # Mostrar por categoria
    for categoria, lista in categorias.items():
        st.markdown(f"#### {categoria} ({len(lista)} oportunidades)")
        
        for oport in lista:
            with st.expander(f"💡 {oport.get('produto', 'N/A')}"):
                st.write(f"**Descrição:** {oport.get('descricao', 'N/A')}")
                st.write(f"**Impacto:** {oport.get('impacto', 'N/A')}")
                st.write(f"**Ação:** {oport.get('acao_recomendada', 'N/A')}")

def gerar_relatorio_discrepancias():
    """Gera relatório de discrepâncias encontradas"""
    if 'resultado_validacao' not in st.session_state:
        st.warning("Execute a validação primeiro.")
        return
    
    discrepancias = st.session_state.resultado_validacao.get('discrepancias', [])
    
    if not discrepancias:
        st.info("Nenhuma discrepância encontrada.")
        return
    
    st.markdown("### Relatório de Discrepâncias")
    
    # Agrupar por gravidade
    por_gravidade = {"Alta": [], "Média": [], "Baixa": []}
    for disc in discrepancias:
        gravidade = disc.get('gravidade', 'Média')
        if gravidade in por_gravidade:
            por_gravidade[gravidade].append(disc)
    
    # Mostrar por gravidade
    cores = {"Alta": "🔴", "Média": "🟡", "Baixa": "🟢"}
    
    for gravidade, lista in por_gravidade.items():
        if lista:
            st.markdown(f"#### {cores[gravidade]} {gravidade} ({len(lista)} discrepâncias)")
            
            for disc in lista:
                with st.expander(f"{cores[gravidade]} {disc.get('produto', 'N/A')}"):
                    st.write(f"**Tipo:** {disc.get('tipo', 'N/A')}")
                    st.write(f"**Problema:** {disc.get('problema', 'N/A')}")
                    st.write(f"**Correção:** {disc.get('correcao', 'N/A')}")

def carregar_dados_temporarios():
    """Carrega dados do arquivo temporário JSON"""
    import json
    import os
    
    try:
        # Caminho absoluto para garantir que encontre o arquivo
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        arquivo_temp = os.path.join(base_dir, 'temp_nfe_data.json')
        
        if os.path.exists(arquivo_temp):
            with open(arquivo_temp, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                st.success(f"Dados carregados do arquivo temporário (salvo em: {dados.get('timestamp_salvamento', 'N/A')})")
                return dados
        else:
            st.warning(f"Arquivo temporário não encontrado em: {arquivo_temp}")
            return None
            
    except Exception as e:
        st.error(f"Erro ao carregar dados temporários: {str(e)}")
        return None


def restaurar_dados_sessao(dados_temp):
    """Restaura dados na sessão a partir do arquivo temporário"""
    try:
        # Restaurar DataFrames
        if 'cabecalho_df' not in st.session_state and dados_temp.get('cabecalho_df'):
            st.session_state.cabecalho_df = pd.DataFrame(dados_temp['cabecalho_df'])
            
        if 'produtos_df' not in st.session_state and dados_temp.get('produtos_df'):
            st.session_state.produtos_df = pd.DataFrame(dados_temp['produtos_df'])
        
        # Restaurar resultados dos agentes
        st.session_state.resultado_validador = dados_temp.get('resultado_validador', {})
        st.session_state.resultado_analista = dados_temp.get('resultado_analista', {})
        st.session_state.resultado_tributarista = dados_temp.get('resultado_tributarista', {})
        st.session_state.resumo_execucao = dados_temp.get('resumo_execucao', {})
        
        # Restaurar outras informações
        st.session_state.arquivo_xml_nome = dados_temp.get('arquivo_xml_nome', 'Arquivo não identificado')
        st.session_state.agentes_processados = True
        st.session_state.timestamp_processamento = dados_temp.get('timestamp_processamento')
        
        st.info("Dados restaurados na sessão a partir do arquivo temporário")
        
    except Exception as e:
        st.error(f"Erro ao restaurar dados na sessão: {str(e)}")


def exibir_edicao_completa_xml(processor):
    """Interface de edição completa de todos os campos XML com sugestões"""
    st.subheader("Edição Completa dos Dados XML")
    
    # Verificar se dados XML estão disponíveis
    if 'cabecalho_df' not in st.session_state or 'produtos_df' not in st.session_state:
        st.error("Dados XML não encontrados. Faça upload de um arquivo XML primeiro.")
        return
    
    st.markdown("Edite os campos abaixo. As sugestões dos agentes aparecem quando disponíveis.")
    
    # Descriptografar dados para edição
    try:
        cabecalho_original = processor.decrypt_sensitive_data(st.session_state.cabecalho_df)
        produtos_original = processor.decrypt_sensitive_data(st.session_state.produtos_df)
        
        # Obter sugestões dos agentes (se disponíveis)
        resultado_validador = st.session_state.get('resultado_validador', {})
        resultado_analista = st.session_state.get('resultado_analista', {})
        resultado_tributarista = st.session_state.get('resultado_tributarista', {})
        
        # Verificar se agentes foram processados
        agentes_processados = st.session_state.get('agentes_processados', False)
        
        if agentes_processados:
            st.info("Sugestões dos agentes IA disponíveis abaixo dos campos")
        else:
            st.warning("Execute 'Análise com IA' para obter sugestões dos agentes")
        
        # Criar mapeamento de sugestões por campo
        sugestoes = criar_mapeamento_sugestoes(resultado_validador, resultado_analista, resultado_tributarista)
        
        # Interface de edição do cabeçalho
        st.markdown("### Dados do Cabeçalho")
        cabecalho_editado = editar_campos_cabecalho(cabecalho_original, sugestoes)
        
        # Interface de edição dos produtos
        st.markdown("### Dados dos Produtos")
        produtos_editados = editar_campos_produtos(produtos_original, sugestoes)
        
        # Botões de salvamento
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Salvar Alterações", type="primary", use_container_width=True):
                salvar_alteracoes_xml(cabecalho_editado, produtos_editados, processor)
        
        with col2:
            if st.button("Gerar XML Corrigido", use_container_width=True):
                gerar_xml_corrigido(cabecalho_editado, produtos_editados)
                
    except Exception as e:
        st.error(f"Erro ao carregar dados para edição: {str(e)}")

def criar_mapeamento_sugestoes(validador, analista, tributarista):
    """Cria mapeamento de sugestões por campo"""
    sugestoes = {}
    
    # Verificar se dados dos agentes estão disponíveis
    if not validador and not analista and not tributarista:
        return sugestoes
    
    # Sugestões do validador (se disponível)
    if validador and isinstance(validador, dict):
        for disc in validador.get('discrepancias', []):
            campo = disc.get('campo_afetado', disc.get('tipo', ''))
            if campo:
                sugestoes[campo] = {
                    'tipo': 'discrepancia',
                    'mensagem': disc.get('correcao', disc.get('problema', '')),
                    'gravidade': disc.get('gravidade', 'Média')
                }
        
        for oport in validador.get('oportunidades', []):
            campo = oport.get('campo_afetado', oport.get('tipo', ''))
            if campo:
                sugestoes[campo] = {
                    'tipo': 'oportunidade', 
                    'mensagem': oport.get('acao_recomendada', oport.get('descricao', '')),
                    'impacto': oport.get('impacto', 'Positivo')
                }
    
    # Sugestões do analista (se disponível)
    if analista and isinstance(analista, dict):
        for analise in analista.get('analises_detalhadas', []):
            campo = analise.get('campo_relacionado', 'Geral')
            if campo and campo != 'Geral':
                sugestoes[campo] = {
                    'tipo': 'analise',
                    'mensagem': analise.get('solucao_proposta', ''),
                    'complexidade': analise.get('grau_complexidade', 'Média')
                }
    
    return sugestoes

def editar_campos_cabecalho(cabecalho_df, sugestoes):
    """Interface de edição dos campos do cabeçalho"""
    if cabecalho_df.empty:
        st.warning("Dados do cabeçalho não disponíveis")
        return cabecalho_df
    
    linha = cabecalho_df.iloc[0]
    campos_editados = {}
    
    # Campos principais para edição
    campos_principais = [
        'Emitente CNPJ', 'Emitente Nome', 'Emitente IE', 
        'Destinatário CNPJ', 'Destinatário Nome', 'Destinatário IE',
        'Número NF', 'Série', 'Natureza Operação', 'CFOP',
        'Valor Total', 'Base ICMS', 'Valor ICMS', 'Valor PIS', 'Valor COFINS', 'Valor IPI'
    ]
    
    for campo in campos_principais:
        if campo in linha:
            valor_original = linha[campo]
            
            # Campo de edição
            if 'Valor' in campo and pd.api.types.is_numeric_dtype(type(valor_original)):
                valor_editado = st.number_input(
                    f"**{campo}**",
                    value=float(valor_original) if valor_original else 0.0,
                    format="%.2f",
                    key=f"cab_{campo}"
                )
            else:
                valor_editado = st.text_input(
                    f"**{campo}**",
                    value=str(valor_original) if valor_original else "",
                    key=f"cab_{campo}"
                )
            
            campos_editados[campo] = valor_editado
            
            # Mostrar sugestão se existir
            mostrar_sugestao_campo(campo, sugestoes)
    
    # Atualizar DataFrame
    cabecalho_editado = cabecalho_df.copy()
    for campo, valor in campos_editados.items():
        cabecalho_editado.loc[0, campo] = valor
    
    return cabecalho_editado

def editar_campos_produtos(produtos_df, sugestoes):
    """Interface de edição dos campos dos produtos"""
    if produtos_df.empty:
        st.warning("Dados dos produtos não disponíveis")
        return produtos_df
    
    produtos_editados = produtos_df.copy()
    
    # Campos principais dos produtos
    campos_produto = [
        'Descrição', 'NCM', 'CFOP', 'Quantidade', 'Valor Unitário', 'Valor Total',
        'Alíquota ICMS', 'Valor ICMS', 'Alíquota PIS', 'Valor PIS', 
        'Alíquota COFINS', 'Valor COFINS', 'Alíquota IPI', 'Valor IPI'
    ]
    
    for idx, produto in produtos_df.iterrows():
        st.markdown(f"**Produto {idx + 1}**")
        
        for campo in campos_produto:
            if campo in produto:
                valor_original = produto[campo]
                
                # Campo de edição
                if 'Valor' in campo or 'Quantidade' in campo:
                    if pd.api.types.is_numeric_dtype(type(valor_original)):
                        valor_editado = st.number_input(
                            f"{campo}",
                            value=float(valor_original) if valor_original else 0.0,
                            format="%.2f",
                            key=f"prod_{idx}_{campo}"
                        )
                    else:
                        valor_editado = st.text_input(
                            f"{campo}",
                            value=str(valor_original) if valor_original else "",
                            key=f"prod_{idx}_{campo}"
                        )
                else:
                    valor_editado = st.text_input(
                        f"{campo}",
                        value=str(valor_original) if valor_original else "",
                        key=f"prod_{idx}_{campo}"
                    )
                
                produtos_editados.loc[idx, campo] = valor_editado
                
                # Mostrar sugestão se existir
                mostrar_sugestao_campo(f"{campo}_produto_{idx}", sugestoes)
        
        st.markdown("---")
    
    return produtos_editados

def mostrar_sugestao_campo(campo, sugestoes):
    """Mostra sugestão para um campo específico"""
    sugestao = sugestoes.get(campo)
    if sugestao:
        tipo = sugestao.get('tipo', 'info')
        mensagem = sugestao.get('mensagem', '')
        
        if tipo == 'discrepancia':
            st.error(f"Correção sugerida: {mensagem}")
        elif tipo == 'oportunidade':
            st.success(f"Oportunidade: {mensagem}")
        elif tipo == 'analise':
            st.info(f"Análise: {mensagem}")
    else:
        # Buscar sugestões genéricas
        for chave, sugestao in sugestoes.items():
            if chave.lower() in campo.lower():
                st.info(f"Sugestão relacionada: {sugestao.get('mensagem', '')}")
                break

def salvar_alteracoes_xml(cabecalho_editado, produtos_editados, processor):
    """Salva alterações nos dados XML"""
    try:
        # Criptografar dados editados
        cabecalho_criptografado = processor.encrypt_sensitive_data(cabecalho_editado)
        produtos_criptografados = processor.encrypt_sensitive_data(produtos_editados)
        
        # Atualizar sessão
        st.session_state.cabecalho_df = cabecalho_criptografado
        st.session_state.produtos_df = produtos_criptografados
        
        st.success("Alterações salvas com sucesso!")
        
    except Exception as e:
        st.error(f"Erro ao salvar alterações: {str(e)}")

def gerar_xml_corrigido(cabecalho_editado, produtos_editados):
    """Gera XML corrigido com os dados editados"""
    try:
        # Gerar XML básico (implementação simplificada)
        xml_corrigido = "<NFe>\n"
        xml_corrigido += "  <Cabecalho>\n"
        
        for campo, valor in cabecalho_editado.iloc[0].items():
            xml_corrigido += f"    <{campo}>{valor}</{campo}>\n"
        
        xml_corrigido += "  </Cabecalho>\n"
        xml_corrigido += "  <Produtos>\n"
        
        for idx, produto in produtos_editados.iterrows():
            xml_corrigido += f"    <Produto id='{idx + 1}'>\n"
            for campo, valor in produto.items():
                xml_corrigido += f"      <{campo}>{valor}</{campo}>\n"
            xml_corrigido += "    </Produto>\n"
        
        xml_corrigido += "  </Produtos>\n"
        xml_corrigido += "</NFe>"
        
        # Download
        st.download_button(
            label="Download XML Corrigido",
            data=xml_corrigido,
            file_name=f"nfe_corrigida_{st.session_state.get('timestamp_processamento', 'unknown').replace(':', '-')[:19]}.xml",
            mime="application/xml",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Erro ao gerar XML: {str(e)}")

def exibir_relatorio_tributarista_completo():
    """Exibe o relatório híbrido completo do tributarista"""
    resultado_tributarista = st.session_state.get('resultado_tributarista', {})
    
    if not resultado_tributarista:
        st.error("Resultado do tributarista não encontrado")
        return
    
    # Verificar se existe o relatório híbrido
    relatorio_hibrido = resultado_tributarista.get('relatorio_hibrido')
    
    if not relatorio_hibrido:
        st.warning("Relatório tributário híbrido não disponível")
        return
    
    # Exibir o relatório híbrido em formato markdown
    st.subheader("Relatório Tributário Completo")
    st.markdown("---")
    
    # Mostrar o relatório híbrido completo como markdown
    st.markdown(relatorio_hibrido)
    
    # Opção para download do relatório como texto
    st.download_button(
        label="Download Relatório Tributário (TXT)",
        data=relatorio_hibrido,
        file_name=f"relatorio_tributario_{st.session_state.get('timestamp_processamento', 'unknown').replace(':', '-')[:19]}.txt",
        mime="text/plain",
        use_container_width=True
    )

def main():
    """Função main para quando executado diretamente"""
    exibir_pagina_revisao()

if __name__ == "__main__":
    main()