import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO

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
st.title("🧾 Extrator de Nota Fiscal Eletrônica (NF-e XML)")

uploaded_file = st.file_uploader("Selecione o arquivo XML da NF-e", type=["xml"])

if uploaded_file is not None:
    xml_content = uploaded_file.read().decode("utf-8")

    cabecalho_df, produtos_df = extrair_dados_xml(xml_content)

    with st.expander("📋 Dados Gerais da NF-e", expanded=True):
        st.dataframe(cabecalho_df.T, use_container_width=True)

    with st.expander("📦 Produtos e Impostos Detalhados", expanded=False):
        st.dataframe(produtos_df, use_container_width=True)

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

    st.success("✅ Extração concluída com sucesso!")
