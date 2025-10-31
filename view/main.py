import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO
from criptografia import SecureDataProcessor
from agents.orquestrador import processar_nfe_completa



def extrair_dados_xml(xml_content):
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    root = ET.fromstring(xml_content)
    infNFe = root.find(".//nfe:infNFe", ns)

    def get_text(tag, parent=infNFe, default="0"):
        return parent.findtext(tag, default=default, namespaces=ns)

    dados = {}

    # --- IDE (Identificação da Nota) ---
    ide = infNFe.find("nfe:ide", ns)
    if ide is not None:
        dados["Número NF"] = get_text("nfe:nNF", ide)
        dados["Série"] = get_text("nfe:serie", ide)
        dados["Data Emissão"] = get_text("nfe:dhEmi", ide)
        dados["Data Saída/Entrada"] = get_text("nfe:dhSaiEnt", ide)
        dados["Natureza Operação"] = get_text("nfe:natOp", ide)
        dados["Tipo NF"] = get_text("nfe:tpNF", ide)
        dados["Modelo"] = get_text("nfe:mod", ide)
        dados["UF"] = get_text("nfe:cUF", ide)
        dados["Finalidade"] = get_text("nfe:finNFe", ide)

    # --- EMITENTE ---
    emit = infNFe.find("nfe:emit", ns)
    if emit is not None:
        dados["Emitente CNPJ"] = get_text("nfe:CNPJ", emit)
        dados["Emitente Nome"] = get_text("nfe:xNome", emit)
        dados["Emitente Fantasia"] = get_text("nfe:xFant", emit)
        dados["Emitente IE"] = get_text("nfe:IE", emit)
        dados["Emitente UF"] = get_text("nfe:enderEmit/nfe:UF", emit)
        dados["Emitente Município"] = get_text("nfe:enderEmit/nfe:xMun", emit)
        dados["Emitente CEP"] = get_text("nfe:enderEmit/nfe:CEP", emit)

    # --- DESTINATÁRIO ---
    dest = infNFe.find("nfe:dest", ns)
    if dest is not None:
        dados["Destinatário CNPJ"] = get_text("nfe:CNPJ", dest)
        dados["Destinatário Nome"] = get_text("nfe:xNome", dest)
        dados["Destinatário IE"] = get_text("nfe:IE", dest)
        dados["Destinatário UF"] = get_text("nfe:enderDest/nfe:UF", dest)
        dados["Destinatário Município"] = get_text("nfe:enderDest/nfe:xMun", dest)
        dados["Destinatário CEP"] = get_text("nfe:enderDest/nfe:CEP", dest)

    # --- TRANSPORTE ---
    transp = infNFe.find("nfe:transp", ns)
    if transp is not None:
        transporta = transp.find("nfe:transporta", ns)
        vol = transp.find("nfe:vol", ns)
        dados["Modalidade Frete"] = get_text("nfe:modFrete", transp)
        if transporta is not None:
            dados["Transportadora Nome"] = get_text("nfe:xNome", transporta)
            dados["Transportadora CNPJ"] = get_text("nfe:CNPJ", transporta)
            dados["Transportadora UF"] = get_text("nfe:UF", transporta)
        if vol is not None:
            dados["Qtde Volumes"] = get_text("nfe:qVol", vol)
            dados["Peso Líquido"] = get_text("nfe:pesoL", vol)
            dados["Peso Bruto"] = get_text("nfe:pesoB", vol)

    # --- COBRANÇA / FATURA ---
    cobr = infNFe.find("nfe:cobr", ns)
    if cobr is not None:
        fat = cobr.find("nfe:fat", ns)
        dup = cobr.find("nfe:dup", ns)
        if fat is not None:
            dados["Número Fatura"] = get_text("nfe:nFat", fat)
            dados["Valor Original"] = get_text("nfe:vOrig", fat)
            dados["Valor Líquido"] = get_text("nfe:vLiq", fat)
        if dup is not None:
            dados["Número Duplicata"] = get_text("nfe:nDup", dup)
            dados["Data Vencimento"] = get_text("nfe:dVenc", dup)
            dados["Valor Duplicata"] = get_text("nfe:vDup", dup)

    # --- TOTALIZAÇÃO ---
    total = infNFe.find(".//nfe:ICMSTot", ns)
    if total is not None:
        dados["Base ICMS"] = get_text("nfe:vBC", total)
        dados["Valor ICMS"] = get_text("nfe:vICMS", total)
        dados["Valor Produtos"] = get_text("nfe:vProd", total)
        dados["Valor NF"] = get_text("nfe:vNF", total)
        dados["Valor Frete"] = get_text("nfe:vFrete", total)
        dados["Valor IPI"] = get_text("nfe:vIPI", total)
        dados["Valor COFINS"] = get_text("nfe:vCOFINS", total)
        dados["Valor PIS"] = get_text("nfe:vPIS", total)

    # --- PRODUTOS ---
    produtos = []
    for det in infNFe.findall("nfe:det", ns):
        prod = det.find("nfe:prod", ns)
        imp = det.find("nfe:imposto", ns)
        if prod is not None:
            p = {
                "Item": det.attrib.get("nItem", "0"),
                "Código": get_text("nfe:cProd", prod),
                "Descrição": get_text("nfe:xProd", prod),
                "NCM": get_text("nfe:NCM", prod),
                "CFOP": get_text("nfe:CFOP", prod),
                "Unidade": get_text("nfe:uCom", prod),
                "Quantidade": get_text("nfe:qCom", prod),
                "Valor Unitário": get_text("nfe:vUnCom", prod),
                "Valor Total": get_text("nfe:vProd", prod),
            }
            if imp is not None:
                p["ICMS"] = get_text(".//nfe:vICMS", imp)
                p["IPI"] = get_text(".//nfe:vIPI", imp)
                p["PIS"] = get_text(".//nfe:vPIS", imp)
                p["COFINS"] = get_text(".//nfe:vCOFINS", imp)
            produtos.append(p)

    produtos_df = pd.DataFrame(produtos).fillna("0")
    cabecalho_df = pd.DataFrame([dados]).fillna("0")

    return cabecalho_df, produtos_df


# ==============================
# STREAMLIT INTERFACE
# ==============================
def welcome_screen():
    """Tela principal da aplicação XML Reader"""
    # Sistema de abas para evitar perda de dados na navegação
    if st.session_state.get('agentes_processados', False):
        # Se agentes foram processados, mostrar seletor de modo
        # Definir índice baseado no estado da navegação
        indice_inicial = 1 if st.session_state.get('navegacao_revisao', False) else 0
        
        modo = st.selectbox(
            "Selecione o modo:",
            ["Processamento de XML", "Revisão e Edição"],
            index=indice_inicial,
            key="modo_selecao"
        )
        
        # Atualizar estado baseado na seleção
        if modo == "Revisão e Edição":
            st.session_state.navegacao_revisao = True
            # Importar e executar função de revisão diretamente
            from view.revisao import exibir_pagina_revisao
            exibir_pagina_revisao()
            return  # Sair da função para não mostrar o resto
        else:
            st.session_state.navegacao_revisao = False
    
    # Código atual do Streamlit (extrair_dados_xml interface)
    st.title("Extrator de Nota Fiscal Eletrônica (NF-e XML)")

    uploaded_file = st.file_uploader("Selecione o arquivo XML da NF-e", type=["xml"])

    if uploaded_file is not None:
        xml_content = uploaded_file.read().decode("utf-8")

        cabecalho_df, produtos_df = extrair_dados_xml(xml_content)

        # Criptografar dados automaticamente
        processor = SecureDataProcessor()
        
        # Criptografar cabecalho
        cabecalho_criptografado = processor.encrypt_sensitive_data(cabecalho_df)
        
        # Criptografar produtos  
        produtos_criptografado = processor.encrypt_sensitive_data(produtos_df)
        
        # Salvar dados na sessão para edição imediata
        st.session_state.cabecalho_df = cabecalho_criptografado
        st.session_state.produtos_df = produtos_criptografado
        st.session_state.arquivo_xml_nome = uploaded_file.name
        st.session_state.xml_carregado = True
        
        # Mostrar seletor de modo logo após upload
        modo = st.selectbox(
            "Selecione o modo:",
            ["Visualização dos Dados", "Edição do XML", "Análise com IA"],
            index=0,
            key="modo_pos_upload"
        )
        
        if modo == "Visualização dos Dados":
            # Manter expandables normais + adicionar dropdown criptografado
            with st.expander("Dados Gerais da NF-e", expanded=True):
                st.dataframe(cabecalho_df.T, use_container_width=True)

            with st.expander("Produtos e Impostos Detalhados", expanded=False):
                st.dataframe(produtos_df, use_container_width=True)

            # NOVO - Dropdown para dados criptografados
            with st.expander("Dados Criptografados", expanded=False):
                tab1, tab2 = st.tabs(["Cabeçalho", "Produtos"])
                
                with tab1:
                    st.dataframe(cabecalho_criptografado, use_container_width=True)
                
                with tab2:
                    st.dataframe(produtos_criptografado, use_container_width=True)
        
        elif modo == "Edição do XML":
            # Importar e executar edição do XML
            from view.revisao import exibir_edicao_completa_xml
            exibir_edicao_completa_xml(processor)
        
        elif modo == "Análise com IA":
            # Análise Fiscal com IA
            st.subheader("Busca de Regras Fiscais")
            
            # Verificar se já existe um resultado processado na sessão
            if (st.session_state.get('agentes_processados') and 
                st.session_state.get('arquivo_xml_nome') == uploaded_file.name):
                st.info("Resultados anteriores carregados da sessão")
                exibir_resultados_processamento()
            else:
                # Botão para processar agentes
                processar_agentes = st.button("Buscar Regras Fiscais Aplicáveis", type="primary")
                
                if processar_agentes:
                    # Container para log em tempo real
                    st.subheader("Processamento com Agentes IA")
                    
                    # Criar containers organizados
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.subheader("Log de Processamento")
                        log_placeholder = st.empty()
                        
                    with col2:
                        st.subheader("Progresso")
                        progress_bar = st.progress(0)
                        status_placeholder = st.empty()
                    
                    # Lista para capturar logs estruturados
                    if 'log_processamento' not in st.session_state:
                        st.session_state.log_processamento = []
                    
                    def callback_status(mensagem):
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                        
                        # Determinar o agente e status da mensagem
                        agente = "Sistema"
                        status = "Info"
                        
                        if "Validador" in mensagem:
                            agente = "Validador"
                            status = "Processando"
                        elif "Analista" in mensagem:
                            agente = "Analista"
                            status = "Processando"
                        elif "Tributarista" in mensagem:
                            agente = "Tributarista"
                            status = "Processando"
                        elif "finalizado" in mensagem.lower() or "concluído" in mensagem.lower():
                            status = "✅ Concluído"
                        elif "erro" in mensagem.lower():
                            status = "❌ Erro"
                        
                        # Adicionar log estruturado
                        log_entry = {
                            "Timestamp": timestamp,
                            "Agente": agente,
                            "Status": status,
                            "Mensagem": mensagem
                        }
                        st.session_state.log_processamento.append(log_entry)
                        
                        # Criar DataFrame dos logs
                        df_logs = pd.DataFrame(st.session_state.log_processamento)
                        
                        # Exibir grid com rolagem
                        with log_placeholder.container():
                            st.dataframe(
                                df_logs,
                                use_container_width=True,
                                height=300,  # Altura fixa com rolagem
                                column_config={
                                    "Timestamp": st.column_config.TextColumn("Tempo", width="small"),
                                    "Agente": st.column_config.TextColumn("Agente", width="medium"),
                                    "Status": st.column_config.TextColumn("Status", width="medium"),
                                    "Mensagem": st.column_config.TextColumn("Detalhes", width="large")
                                },
                                hide_index=True
                            )
                        
                        # Atualizar barra de progresso e status
                        progresso = 0
                        status_atual = "Iniciando..."
                        
                        if "Validador" in mensagem:
                            progresso = 33
                            status_atual = "Executando Validador..."
                        elif "Analista" in mensagem:
                            progresso = 66
                            status_atual = "Executando Analista..."
                        elif "Tributarista" in mensagem:
                            progresso = 100
                            status_atual = "Executando Tributarista..."
                        elif "finalizado" in mensagem.lower():
                            progresso = 100
                            status_atual = "✅ Processamento Concluído!"
                        
                        progress_bar.progress(progresso)
                        status_placeholder.info(f"**Status:** {status_atual}")
                        
                        # Scroll automático para o último log (simular)
                        if len(st.session_state.log_processamento) > 10:
                            # Manter apenas os últimos 50 logs para performance
                            st.session_state.log_processamento = st.session_state.log_processamento[-50:]
                    
                    try:
                        # Executar orquestração dos 3 agentes
                        resultado_completo = processar_nfe_completa(
                            cabecalho_criptografado,
                            produtos_criptografado,
                            callback_status
                        )
                        
                        # Armazenar resultados na sessão e em arquivo temporário
                        st.session_state.resultado_validador = resultado_completo.get('validador', {})
                        st.session_state.resultado_analista = resultado_completo.get('analista', {})
                        st.session_state.resultado_tributarista = resultado_completo.get('tributarista', {})
                        st.session_state.resumo_execucao = resultado_completo.get('resumo_execucao', {})
                        st.session_state.agentes_processados = True
                        st.session_state.timestamp_processamento = resultado_completo.get('timestamp_processamento')
                        
                        # Salvar em arquivo temporário para persistência
                        salvar_dados_temporarios(
                            cabecalho_criptografado, 
                            produtos_criptografado, 
                            resultado_completo,
                            uploaded_file.name
                        )
                        
                        if resultado_completo['status'] == 'sucesso':
                            # Chamar função centralizada para exibir resultados
                            exibir_resultados_processamento()
                            
                        else:
                            st.error("Erro no processamento dos agentes")
                            st.write("Detalhes:", resultado_completo.get('detalhes', {}))
                                
                    except Exception as e:
                        st.error(f"Erro crítico na orquestração: {str(e)}")
                        st.session_state.agentes_processados = False

        # Criação do Excel para download
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            cabecalho_df.to_excel(writer, sheet_name="Cabecalho", index=False)
            produtos_df.to_excel(writer, sheet_name="Produtos", index=False)
        output.seek(0)

        st.download_button(
            label="📥 Baixar Excel da NF-e",
            data=output,
            file_name="nfe_dados_extraidos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.success("Extração concluída com sucesso!")


def exibir_resultados_processamento():
    """Exibe os resultados do processamento dos agentes a partir do session_state"""
    try:
        # Recuperar dados do session_state
        resultado_validador = st.session_state.get('resultado_validador', {})
        resultado_analista = st.session_state.get('resultado_analista', {})
        resultado_tributarista = st.session_state.get('resultado_tributarista', {})
        resumo_execucao = st.session_state.get('resumo_execucao', {})
        arquivo_nome = st.session_state.get('arquivo_xml_nome', 'arquivo')
        timestamp_proc = st.session_state.get('timestamp_processamento', 'unknown')
        
        # Recriar resultado_completo
        resultado_completo = {
            'status': 'sucesso',
            'validador': resultado_validador,
            'analista': resultado_analista, 
            'tributarista': resultado_tributarista,
            'resumo_execucao': resumo_execucao,
            'timestamp_processamento': timestamp_proc
        }
        
        # Exibir resumo executivo
        st.success("Processamento concluído com sucesso!")
        
        # Seção do histórico de logs
        with st.expander("📋 **Histórico de Processamento**", expanded=False):
            if 'log_processamento' in st.session_state and st.session_state.log_processamento:
                df_logs_historico = pd.DataFrame(st.session_state.log_processamento)
                
                # Filtros para o histórico
                col_filtro1, col_filtro2 = st.columns(2)
                
                with col_filtro1:
                    agentes_disponiveis = ["Todos"] + df_logs_historico["Agente"].unique().tolist()
                    filtro_agente = st.selectbox("Filtrar por Agente:", agentes_disponiveis)
                
                with col_filtro2:
                    status_disponiveis = ["Todos"] + df_logs_historico["Status"].unique().tolist()
                    filtro_status = st.selectbox("Filtrar por Status:", status_disponiveis)
                
                # Aplicar filtros
                df_filtrado = df_logs_historico.copy()
                if filtro_agente != "Todos":
                    df_filtrado = df_filtrado[df_filtrado["Agente"] == filtro_agente]
                if filtro_status != "Todos":
                    df_filtrado = df_filtrado[df_filtrado["Status"] == filtro_status]
                
                # Exibir grid filtrado
                st.dataframe(
                    df_filtrado,
                    use_container_width=True,
                    height=400,
                    column_config={
                        "Timestamp": st.column_config.TextColumn("Tempo", width="small"),
                        "Agente": st.column_config.TextColumn("Agente", width="medium"),
                        "Status": st.column_config.TextColumn("Status", width="medium"),
                        "Mensagem": st.column_config.TextColumn("Detalhes", width="large")
                    },
                    hide_index=True
                )
                
                # Estatísticas do processamento
                st.subheader("📊 Estatísticas do Processamento")
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                
                with col_stat1:
                    total_logs = len(df_logs_historico)
                    st.metric("Total de Logs", total_logs)
                
                with col_stat2:
                    agentes_executados = df_logs_historico["Agente"].nunique()
                    st.metric("Agentes Executados", agentes_executados)
                
                with col_stat3:
                    status_sucesso = len(df_logs_historico[df_logs_historico["Status"].str.contains("Concluído", na=False)])
                    st.metric("Etapas Concluídas", status_sucesso)
                
                # Botões de ação para os logs
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if st.button("🗑️ Limpar Logs", help="Remove todos os logs do histórico"):
                        st.session_state.log_processamento = []
                        st.rerun()
                
                with col_btn2:
                    # Exportar logs para CSV
                    csv_logs = df_filtrado.to_csv(index=False)
                    st.download_button(
                        label="📄 Exportar Logs (CSV)",
                        data=csv_logs,
                        file_name=f"logs_processamento_{timestamp_proc}.csv",
                        mime="text/csv",
                        help="Baixa os logs filtrados em formato CSV"
                    )
                
                with col_btn3:
                    # Exportar logs para Excel  
                    buffer_logs = BytesIO()
                    with pd.ExcelWriter(buffer_logs, engine='xlsxwriter') as writer:
                        df_filtrado.to_excel(writer, sheet_name='Logs_Processamento', index=False)
                    buffer_logs.seek(0)
                    
                    st.download_button(
                        label="📊 Exportar Logs (Excel)",
                        data=buffer_logs.getvalue(),
                        file_name=f"logs_processamento_{timestamp_proc}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Baixa os logs filtrados em formato Excel"
                    )
                    
            else:
                st.info("Nenhum log de processamento disponível.")
        
        # Mostrar resumo executivo
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Oportunidades", resumo_execucao.get('total_oportunidades', 0))
        with col2:
            st.metric("Discrepâncias", resumo_execucao.get('total_discrepancias', 0))
        with col3:
            st.metric("Soluções", resumo_execucao.get('total_solucoes', 0))
        with col4:
            st.metric("Produtos", resumo_execucao.get('produtos_analisados', 0))
        
        # Botões de ação
        st.info("Dados processados e salvos na sessão. Clique para revisar:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Ir para Revisão", type="primary", key="goto_revisao_persistent"):
                st.session_state.navegacao_revisao = True
                st.success("Clique em 'Revisão e Edição' no seletor acima para continuar!")
        
        with col2:
            # Gerar PDF com key único para evitar conflitos
            try:
                pdf_data = gerar_relatorio_pdf(resultado_completo, arquivo_nome)
                if pdf_data:
                    st.download_button(
                        label="Download Relatório PDF",
                        data=pdf_data,
                        file_name=f"relatorio_fiscal_{timestamp_proc.replace(':', '-')[:19]}.pdf",
                        mime="application/pdf",
                        type="secondary",
                        key="download_pdf_persistent"
                    )
                else:
                    st.error("Erro ao gerar relatório PDF")
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {str(e)}")
        
        # Dropdown para visualizar relatório tributarista
        resultado_tributarista = resultado_completo.get('tributarista', {})
        if resultado_tributarista.get('relatorio_hibrido'):
            with st.expander("Ver Relatório Tributário Completo"):
                st.markdown(resultado_tributarista['relatorio_hibrido'])
        
    except Exception as e:
        st.error(f"Erro ao exibir resultados: {str(e)}")
        st.session_state.agentes_processados = False

def salvar_dados_temporarios(cabecalho_df, produtos_df, resultado_completo, nome_arquivo):
    """Salva dados em arquivo temporário JSON para persistência"""
    import json
    import os
    from datetime import datetime
    
    try:
        dados_temporarios = {
            'timestamp_salvamento': datetime.now().isoformat(),
            'arquivo_xml_nome': nome_arquivo,
            'cabecalho_df': cabecalho_df.to_dict('records'),
            'produtos_df': produtos_df.to_dict('records'),
            'resultado_validador': resultado_completo.get('validador', {}),
            'resultado_analista': resultado_completo.get('analista', {}),
            'resultado_tributarista': resultado_completo.get('tributarista', {}),
            'resumo_execucao': resultado_completo.get('resumo_execucao', {}),
            'timestamp_processamento': resultado_completo.get('timestamp_processamento')
        }
        
        # Salvar no diretório raiz do projeto
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        arquivo_temp = os.path.join(base_dir, 'temp_nfe_data.json')
        
        with open(arquivo_temp, 'w', encoding='utf-8') as f:
            json.dump(dados_temporarios, f, ensure_ascii=False, indent=2)
            
        st.success("Dados salvos em arquivo temporário")
        
    except Exception as e:
        st.warning(f"Erro ao salvar dados temporários: {str(e)}")


def gerar_relatorio_pdf(resultado_completo, nome_arquivo):
    """Gera relatório PDF com insights dos 3 agentes"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from io import BytesIO
        from datetime import datetime
        
        # Buffer para PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Título
        titulo_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=18, spaceAfter=30)
        story.append(Paragraph("Relatório de Análise Fiscal", titulo_style))
        story.append(Spacer(1, 12))
        
        # Informações básicas
        story.append(Paragraph(f"<b>Arquivo:</b> {nome_arquivo}", styles['Normal']))
        story.append(Paragraph(f"<b>Data do Processamento:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Resumo Executivo
        resumo = resultado_completo.get('resumo_execucao', {})
        story.append(Paragraph("<b>RESUMO EXECUTIVO</b>", styles['Heading2']))
        
        # Tabela de métricas
        dados_metricas = [
            ['Métrica', 'Valor'],
            ['Produtos Analisados', str(resumo.get('produtos_analisados', 0))],
            ['Oportunidades Identificadas', str(resumo.get('total_oportunidades', 0))],
            ['Discrepâncias Encontradas', str(resumo.get('total_discrepancias', 0))],
            ['Soluções Propostas', str(resumo.get('total_solucoes', 0))]
        ]
        
        tabela_metricas = Table(dados_metricas)
        tabela_metricas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(tabela_metricas)
        story.append(Spacer(1, 20))
        
        # Oportunidades do Validador
        validador = resultado_completo.get('validador', {})
        oportunidades = validador.get('oportunidades', [])
        
        if oportunidades:
            story.append(Paragraph("<b>OPORTUNIDADES IDENTIFICADAS</b>", styles['Heading2']))
            for i, oport in enumerate(oportunidades, 1):
                story.append(Paragraph(f"<b>{i}. {oport.get('tipo', 'N/A')}</b>", styles['Heading3']))
                story.append(Paragraph(f"<b>Produto:</b> {oport.get('produto', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Descrição:</b> {oport.get('descricao', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Impacto:</b> {oport.get('impacto', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Ação Recomendada:</b> {oport.get('acao_recomendada', 'N/A')}", styles['Normal']))
                story.append(Spacer(1, 12))
        
        # Discrepâncias
        discrepancias = validador.get('discrepancias', [])
        if discrepancias:
            story.append(Paragraph("<b>DISCREPÂNCIAS ENCONTRADAS</b>", styles['Heading2']))
            for i, disc in enumerate(discrepancias, 1):
                story.append(Paragraph(f"<b>{i}. {disc.get('tipo', 'N/A')} ({disc.get('gravidade', 'N/A')})</b>", styles['Heading3']))
                story.append(Paragraph(f"<b>Produto:</b> {disc.get('produto', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Problema:</b> {disc.get('problema', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Correção:</b> {disc.get('correcao', 'N/A')}", styles['Normal']))
                story.append(Spacer(1, 12))

        # Relatório Final do Analista (se disponível)
        analista = resultado_completo.get('analista', {})
        if analista.get('status') == 'sucesso' and analista.get('relatorio_final'):
            story.append(Paragraph("<b>ANÁLISE DETALHADA DO ANALISTA</b>", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Processar relatório final do analista (markdown)
            relatorio_analista = analista.get('relatorio_final', '')
            
            # Processar markdown simples
            linhas_analista = relatorio_analista.split('\n')
            for linha in linhas_analista:
                linha = linha.strip()
                if not linha:
                    story.append(Spacer(1, 6))
                    continue
                
                if linha.startswith('##'):
                    titulo = linha.replace('##', '').strip()
                    story.append(Paragraph(f"<b>{titulo}</b>", styles['Heading3']))
                elif linha.startswith('**') and linha.endswith('**'):
                    texto_negrito = linha.replace('**', '').strip()
                    story.append(Paragraph(f"<b>{texto_negrito}</b>", styles['Normal']))
                elif linha.startswith('- '):
                    item = linha.replace('- ', '').strip()
                    story.append(Paragraph(f"• {item}", styles['Normal']))
                else:
                    if linha and not linha.startswith('---'):
                        story.append(Paragraph(linha, styles['Normal']))
            
            story.append(Spacer(1, 20))
        
        # Relatório Híbrido do Tributarista (COMPLETO)
        tributarista = resultado_completo.get('tributarista', {})
        if tributarista.get('status') == 'sucesso' and tributarista.get('relatorio_hibrido'):
            story.append(Paragraph("<b>RELATÓRIO TRIBUTÁRIO COMPLETO</b>", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Converter markdown do relatório híbrido para PDF
            relatorio_markdown = tributarista.get('relatorio_hibrido', '')
            
            # Processar o markdown linha por linha
            linhas = relatorio_markdown.split('\n')
            for linha in linhas:
                linha = linha.strip()
                if not linha:
                    story.append(Spacer(1, 6))
                    continue
                
                # Títulos principais (##)
                if linha.startswith('## '):
                    titulo = linha.replace('## ', '').strip()
                    story.append(Paragraph(f"<b>{titulo}</b>", styles['Heading3']))
                    story.append(Spacer(1, 8))
                
                # Títulos secundários (###)
                elif linha.startswith('### '):
                    subtitulo = linha.replace('### ', '').strip()
                    story.append(Paragraph(f"<b>{subtitulo}</b>", styles['Heading4']))
                    story.append(Spacer(1, 6))
                
                # Título principal (#)
                elif linha.startswith('# '):
                    titulo_principal = linha.replace('# ', '').strip()
                    story.append(Paragraph(f"<b>{titulo_principal}</b>", styles['Heading2']))
                    story.append(Spacer(1, 10))
                
                # Tabelas markdown (|)
                elif '|' in linha and not linha.startswith('|---'):
                    # Processar tabela markdown simples
                    colunas = [col.strip() for col in linha.split('|') if col.strip()]
                    if colunas:
                        # Criar linha de tabela simples
                        linha_tabela = ' | '.join(colunas)
                        story.append(Paragraph(linha_tabela, styles['Normal']))
                
                # Lista com bullet points (-)
                elif linha.startswith('- '):
                    item = linha.replace('- ', '').strip()
                    story.append(Paragraph(f"• {item}", styles['Normal']))
                
                # Texto em negrito (**texto**)
                elif '**' in linha:
                    # Substituir **texto** por <b>texto</b>
                    linha_formatada = linha.replace('**', '<b>', 1).replace('**', '</b>', 1)
                    # Continuar substituindo se houver mais
                    while '**' in linha_formatada:
                        linha_formatada = linha_formatada.replace('**', '<b>', 1).replace('**', '</b>', 1)
                    story.append(Paragraph(linha_formatada, styles['Normal']))
                
                # Separadores (---)
                elif linha.startswith('---'):
                    story.append(Spacer(1, 12))
                
                # Texto normal
                else:
                    if linha:
                        story.append(Paragraph(linha, styles['Normal']))
            
            story.append(Spacer(1, 20))
        
        # Gerar PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
        
    except ImportError:
        st.error("Biblioteca reportlab não instalada. Execute: pip install reportlab")
        return None
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")
        return None