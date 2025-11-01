import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO
import zipfile
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

def exibir_relatorio_tributario(relatorio):
    import re
    # Remove emojis
    relatorio = relatorio.replace("🧮", "").replace("🔢", "").replace("🚨", "").replace("🏭", "")

    # Fix bold syntax and remove extra spaces
    relatorio = re.sub(r'\*\*\s*(.*?)\s*:\*\*', r'**\1:**', relatorio)

    st.markdown(relatorio, unsafe_allow_html=True)

# ==============================
# STREAMLIT INTERFACE
# ==============================
def main_screen():
    st.set_page_config(layout="wide")
    st.markdown("""
    <style>
        /* Alvo nos botões das abas */
        .st-emotion-cache-13qj2pw p {
            font-size: 1.1rem; /* Aumenta o tamanho da fonte */
        }

        /* Alvo no contêiner das abas para adicionar uma borda inferior */
        .st-emotion-cache-1hb1y26 {
            border-bottom: 2px solid #f0f2f6;
        }

        /* Alvo no botão da aba selecionada */
        .st-emotion-cache-13qj2pw[aria-selected="true"] {
            border-bottom: 2px solid #2196f3; /* Cor azul para a aba ativa */
            color: #2196f3; /* Cor do texto da aba ativa */
        }
        
        /* Efeito hover para os botões das abas */
        .st-emotion-cache-13qj2pw:hover {
            background-color: #f0f2f6; /* Cor de fundo suave no hover */
            color: #2196f3; /* Cor do texto no hover */
        }


    </style>
    """, unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>CaaS - Compliance as a Service</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Passo 1: Carregue o arquivo XML")
    uploaded_file = st.file_uploader("Selecione o arquivo XML da NF-e", type=["xml"])
    st.markdown("<br>", unsafe_allow_html=True)

    if uploaded_file is not None:
        st.subheader("Passo 2: Analise os dados")
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
        
        tab1, tab2 = st.tabs(["Visualização dos Dados", "Análise com IA"])

        with tab1:
            # Manter expandables normais + adicionar dropdown criptografado
            with st.expander("Dados Gerais da NF-e", expanded=True):
                st.dataframe(cabecalho_df.T, use_container_width=True)

            with st.expander("Produtos e Impostos Detalhados", expanded=False):
                st.dataframe(produtos_df, use_container_width=True)

            # NOVO - Dropdown para dados criptografados
            with st.expander("Dados Criptografados", expanded=False):
                tab_c1, tab_c2 = st.tabs(["Cabeçalho", "Produtos"])
                
                with tab_c1:
                    st.dataframe(cabecalho_criptografado, use_container_width=True)
                
                with tab_c2:
                    st.dataframe(produtos_criptografado, use_container_width=True)
        
        with tab2:
            # Análise Fiscal com IA
            st.subheader("Busca de Regras Fiscais")
            
            # Verificar se já existe um resultado processado na sessão
            if (st.session_state.get('agentes_processados') and 
                st.session_state.get('arquivo_xml_nome') == uploaded_file.name):
                st.info("Resultados anteriores carregados da sessão")
                pdf_data_from_agents, pdf_file_name_from_agents = exibir_resultados_processamento()
                if pdf_data_from_agents and pdf_file_name_from_agents:
                    st.session_state.pdf_data_report = pdf_data_from_agents
                    st.session_state.pdf_file_name_report = pdf_file_name_from_agents
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
                            pdf_data_from_agents, pdf_file_name_from_agents = exibir_resultados_processamento()
                            if pdf_data_from_agents and pdf_file_name_from_agents:
                                st.session_state.pdf_data_report = pdf_data_from_agents
                                st.session_state.pdf_file_name_report = pdf_file_name_from_agents
                            
                        else:
                            st.error("Erro no processamento dos agentes")
                            st.write("Detalhes:", resultado_completo.get('detalhes', {}))
                                
                    except Exception as e:
                        st.error(f"Erro crítico na orquestração: {str(e)}")
                        st.session_state.agentes_processados = False

        st.subheader("Passo 3: Exporte os resultados")
        
        # Botão para baixar o ZIP com XML e Relatório PDF
        if st.session_state.get('pdf_data_report') and st.session_state.get('pdf_file_name_report'):
            zip_data = gerar_zip_relatorio_e_xml(
                xml_content,
                st.session_state.pdf_data_report,
                st.session_state.arquivo_xml_nome,
                st.session_state.pdf_file_name_report
            )
            if zip_data:
                st.download_button(
                    label="Baixar XML e Relatório (ZIP)",
                    data=zip_data,
                    file_name=f"nfe_relatorio_{st.session_state.timestamp_processamento.replace(':', '-')[:19]}.zip",
                    mime="application/zip",
                    type="primary",
                    key="download_zip_completo"
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
        with st.expander("Histórico de Processamento", expanded=False):
            if 'log_processamento' in st.session_state and st.session_state.log_processamento:
                df_logs_historico = pd.DataFrame(st.session_state.log_processamento)
                
                # Filtros para o histórico
                col_filtro1, col_filtro2 = st.columns(2)
                
                with col_filtro1:
                    agentes_disponiveis = ["Todos"] + df_logs_historico["Agente"].unique().tolist()
                    filtro_agente = st.selectbox("Filtrar por Agente:", agentes_disponiveis, key="filtro_agente_selectbox")
                
                with col_filtro2:
                    status_disponiveis = ["Todos"] + df_logs_historico["Status"].unique().tolist()
                    filtro_status = st.selectbox("Filtrar por Status:", status_disponiveis, key="filtro_status_selectbox")
                
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
                st.subheader("Estatísticas do Processamento")
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
                    if st.button("Limpar Logs", help="Remove todos os logs do histórico"):
                        st.session_state.log_processamento = []
                        st.rerun()
                
                with col_btn2:
                    # Exportar logs para CSV
                    csv_logs = df_filtrado.to_csv(index=False)
                    st.download_button(
                        label="Exportar Logs (CSV)",
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
                        label="Exportar Logs (Excel)",
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
        
        # Gerar PDF com key único para evitar conflitos
        pdf_data = None
        pdf_file_name = None
        try:
            pdf_data = gerar_relatorio_pdf(resultado_completo, arquivo_nome)
            if pdf_data:
                pdf_file_name = f"relatorio_fiscal_{timestamp_proc.replace(':', '-')[:19]}.pdf"
            else:
                st.error("Erro ao gerar relatório PDF")
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {str(e)}")
        
        # Dropdown para visualizar relatório tributarista
        resultado_tributarista = resultado_completo.get('tributarista', {})
        if resultado_tributarista.get('relatorio_hibrido'):
            with st.expander("Relatório Tributário Completo"):
                exibir_relatorio_tributario(resultado_tributarista['relatorio_hibrido'])
        
        return pdf_data, pdf_file_name

    except Exception as e:
        st.error(f"Erro ao exibir resultados: {str(e)}")
        st.session_state.agentes_processados = False
        return None, None

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
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from io import BytesIO
        from datetime import datetime
        
        # Buffer para PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Estilo do corpo do texto
        body_style = ParagraphStyle('BodyText', parent=styles['Normal'], alignment=TA_JUSTIFY, leading=14)

        story = []
        
        # Adicionar a logo
        logo = "assets/LOGO.png"
        img = Image(logo, width=100, height=100)
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Spacer(1, 12))

        # Título
        titulo_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=18, spaceAfter=30, alignment=TA_CENTER)
        story.append(Paragraph("Relatório de Análise Fiscal", titulo_style))
        story.append(Spacer(1, 12))
        
        # Informações básicas
        story.append(Paragraph(f"<b>Arquivo:</b> {nome_arquivo}", body_style))
        story.append(Paragraph(f"<b>Data do Processamento:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", body_style))
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
                story.append(Paragraph(f"<b>Produto:</b> {oport.get('produto', 'N/A')}", body_style))
                story.append(Paragraph(f"<b>Descrição:</b> {oport.get('descricao', 'N/A')}", body_style))
                story.append(Paragraph(f"<b>Impacto:</b> {oport.get('impacto', 'N/A')}", body_style))
                story.append(Paragraph(f"<b>Ação Recomendada:</b> {oport.get('acao_recomendada', 'N/A')}", body_style))
                story.append(Spacer(1, 12))
        
        # Discrepâncias
        discrepancias = validador.get('discrepancias', [])
        if discrepancias:
            story.append(Paragraph("<b>DISCREPÂNCIAS ENCONTRADAS</b>", styles['Heading2']))
            for i, disc in enumerate(discrepancias, 1):
                story.append(Paragraph(f"<b>{i}. {disc.get('tipo', 'N/A')} ({disc.get('gravidade', 'N/A')})</b>", styles['Heading3']))
                story.append(Paragraph(f"<b>Produto:</b> {disc.get('produto', 'N/A')}", body_style))
                story.append(Paragraph(f"<b>Problema:</b> {disc.get('problema', 'N/A')}", body_style))
                story.append(Paragraph(f"<b>Correção:</b> {disc.get('correcao', 'N/A')}", body_style))
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
                    story.append(Paragraph(f"<b>{texto_negrito}</b>", body_style))
                elif linha.startswith('- '):
                    item = linha.replace('- ', '').strip()
                    story.append(Paragraph(f"• {item}", body_style))
                else:
                    if linha and not linha.startswith('---'):
                        story.append(Paragraph(linha, body_style))
            
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
                        story.append(Paragraph(linha_tabela, body_style))
                
                # Lista com bullet points (-)
                elif linha.startswith('- '):
                    item = linha.replace('- ', '').strip()
                    story.append(Paragraph(f"• {item}", body_style))
                
                # Texto em negrito (**texto**)
                elif '**' in linha:
                    # Substituir **texto** por <b>texto</b>
                    linha_formatada = linha.replace('**', '<b>', 1).replace('**', '</b>', 1)
                    # Continuar substituindo se houver mais
                    while '**' in linha_formatada:
                        linha_formatada = linha_formatada.replace('**', '<b>', 1).replace('**', '</b>', 1)
                    story.append(Paragraph(linha_formatada, body_style))
                
                # Separadores (---)
                elif linha.startswith('---'):
                    story.append(Spacer(1, 12))
                
                # Texto normal
                else:
                    if linha:
                        story.append(Paragraph(linha, body_style))
            
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

def gerar_zip_relatorio_e_xml(xml_content, pdf_data, xml_file_name, pdf_file_name):
    """Gera um arquivo ZIP contendo o XML original e o relatório PDF."""
    try:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr(xml_file_name, xml_content.encode("utf-8"))
            zip_file.writestr(pdf_file_name, pdf_data)
        return zip_buffer.getvalue()
    except Exception as e:
        st.error(f"Erro ao gerar ZIP: {str(e)}")
        return None
