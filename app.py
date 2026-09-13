import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DE ACESSO E CONEXÃO COM GOOGLE SHEETS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Carteira de Imóveis | MRC Imóveis", page_icon="🏢", layout="wide")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_google_sheets():
    credenciais_dict = dict(st.secrets["gcp_service_account"])
    # Ajusta quebras de linha na chave privada
    if "private_key" in credenciais_dict:
        credenciais_dict["private_key"] = credenciais_dict["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(credenciais_dict, scopes=SCOPES)
    client = gspread.authorize(credentials)
    return client.open("Carteira_Imoveis_MRC").sheet1

# -----------------------------------------------------------------------------
# CONTROLE DE ACESSO (SENHA DE PROTEÇÃO INTERNA)
# -----------------------------------------------------------------------------
SENHA_CORRETA = "431360"  # Você pode alterar a senha interna aqui

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito — MRC Imóveis")
    senha_input = st.text_input("Digite a senha de acesso interno:", type="password")
    if st.button("Entrar"):
        if senha_input == SENHA_CORRETA:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("❌ Senha incorreta.")
    st.stop()

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPAL
# -----------------------------------------------------------------------------
try:
    sheet = conectar_google_sheets()
except Exception as e:
    st.error(f"❌ Erro ao conectar com o Google Sheets: {e}")
    st.stop()

st.title("🏢 Carteira de Imóveis — Gestão Comercial")
st.write("Centralização de acervo, proprietários e acompanhamento de negociações.")

aba_cadastro, aba_consulta = st.tabs(["➕ Cadastrar Novo Imóvel", "🔍 Consultar e Pesquisar Carteira"])

# -----------------------------------------------------------------------------
# ABA 1: CADASTRAR NOVO IMÓVEL
# -----------------------------------------------------------------------------
with aba_cadastro:
    st.subheader("Novo Cadastro Rápido")
    
    with st.form("form_novo_imovel", clear_on_submit=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            proprietario_nome = st.text_input("Nome do Proprietário *")
            proprietario_telefone = st.text_input("Telefone / WhatsApp do Proprietário *", placeholder="(61) 90000-0000")
            proprietario_email = st.text_input("E-mail do Proprietário")
        with col_p2:
            tipo_imovel = st.selectbox("Tipo de Imóvel *", ["Apartamento", "Casa", "Loja Comercial", "Sala Comercial", "Terreno", "Outro"])
            finalidade = st.selectbox("Finalidade *", ["Locação", "Venda", "Locação e Venda"])
            status = st.selectbox("Status Atual *", ["Disponível", "Em Negociação", "Alugado", "Vendido", "Suspenso"])

        endereco_imovel = st.text_input("Endereço Completo do Imóvel (com Bloco/Apto) *")
        
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            bairro = st.text_input("Bairro / Região *", placeholder="Ex: Asa Sul, Sudoeste, Águas Claras")
            valor_pretendido = st.text_input("Valor Pretendido (R$) *", placeholder="Ex: 3500 ou 750000")
        with col_v2:
            valor_condominio = st.text_input("Valor Condomínio (R$)", placeholder="Ex: 600")
            valor_iptu = st.text_input("Valor IPTU (R$)", placeholder="Ex: 1500")
        with col_v3:
            chaves_local = st.text_input("Localização das Chaves / Acesso *", placeholder="Ex: Na portaria, com o dono, no escritório")

        observacoes = st.text_area("Observações Internas (Ex: aceita proposta, horário de visita, etc.)")

        btn_salvar = st.form_submit_button("💾 Salvar na Carteira", type="primary")

    if btn_salvar:
        if not proprietario_nome or not proprietario_telefone or not endereco_imovel or not bairro or not valor_pretendido or not chaves_local:
            st.error("⚠️ Preencha todos os campos obrigatórios (*).")
        else:
            try:
                data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                nova_linha = [
                    data_hoje, proprietario_nome, proprietario_telefone, proprietario_email,
                    endereco_imovel, bairro, tipo_imovel, finalidade, valor_pretendido,
                    valor_condominio, valor_iptu, status, chaves_local, observacoes
                ]
                sheet.append_row(nova_linha)
                st.success("✅ Imóvel cadastrado com sucesso na planilha!")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Erro ao salvar dados: {e}")

# -----------------------------------------------------------------------------
# ABA 2: CONSULTAR E PESQUISAR CARTEIRA
# -----------------------------------------------------------------------------
with aba_consulta:
    st.subheader("Consulta e Filtros de Imóveis")
    
    try:
        dados_raw = sheet.get_all_records()
        if not dados_raw:
            st.info("Nenhum imóvel cadastrado na carteira até o momento.")
        else:
            df = pd.DataFrame(dados_raw)

            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                busca_texto = st.text_input("🔎 Pesquisar (Nome, Endereço ou Bairro):")
            with col_f2:
                filtro_finalidade = st.multiselect("Filtrar Finalidade:", options=df["Finalidade"].unique().tolist(), default=df["Finalidade"].unique().tolist())
            with col_f3:
                filtro_status = st.multiselect("Filtrar Status:", options=df["Status"].unique().tolist(), default=df["Status"].unique().tolist())

            # Aplicação dos Filtros
            df_filtrado = df[
                (df["Finalidade"].isin(filtro_finalidade)) &
                (df["Status"].isin(filtro_status))
            ]

            if busca_texto:
                termo = busca_texto.lower()
                df_filtrado = df_filtrado[
                    df_filtrado["Proprietario_Nome"].astype(str).str.lower().str.contains(termo) |
                    df_filtrado["Endereco_Imovel"].astype(str).str.lower().str.contains(termo) |
                    df_filtrado["Bairro"].astype(str).str.lower().str.contains(termo)
                ]

            st.write(f"**Total de Imóveis encontrados:** {len(df_filtrado)}")
            
            # Exibição da Tabela Interativa
            st.dataframe(
                df_filtrado,
                column_config={
                    "Proprietario_Telefone": st.column_config.LinkColumn("Telefone", display_text=r"📱 (61) .*"),
                },
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(f"❌ Erro ao carregar a carteira: {e}")
