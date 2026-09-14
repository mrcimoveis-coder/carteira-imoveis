import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E LOGOMARCA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Carteira de Imóveis | MRC Imóveis", page_icon="🏢", layout="wide")

try:
    st.image("https://raw.githubusercontent.com/mrcimoveis-coder/portal-intranet/main/logo.jpeg", width=260)
except Exception:
    pass

# -----------------------------------------------------------------------------
# CONEXÃO COM GOOGLE SHEETS
# -----------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_google_sheets(nome_aba=None):
    credenciais_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in credenciais_dict:
        credenciais_dict["private_key"] = credenciais_dict["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(credenciais_dict, scopes=SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key("1yJBZZ0nDnJKsf31H6sfG_vve19TJIRfGIZ4ATCKQS7k")
    
    if nome_aba:
        try:
            return spreadsheet.worksheet(nome_aba)
        except Exception:
            return spreadsheet.add_worksheet(title=nome_aba, rows="200", cols="20")
    return spreadsheet.sheet1

# -----------------------------------------------------------------------------
# CONTROLE DE ACESSO
# -----------------------------------------------------------------------------
SENHA_CORRETA = "431360"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito — Carteira")
    senha_input = st.text_input("Digite a senha de acesso interno:", type="password")
    if st.button("Entrar", type="primary"):
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

aba_triagem, aba_cadastro, aba_consulta, aba_editar = st.tabs([
    "📥 Triagem / Novos Leads", 
    "➕ Cadastrar Novo Imóvel", 
    "🔍 Consultar e Pesquisar Carteira", 
    "✏️ Editar e Excluir"
])

# -----------------------------------------------------------------------------
# ABA 1: TRIAGEM DE LEADS VINDOS DO SITE (NOVO)
# -----------------------------------------------------------------------------
with aba_triagem:
    st.subheader("📥 Imóveis Enviados pelo Site (Pendentes de Aprovação)")
    st.caption("Verifique as informações enviadas pelos proprietários e aprove para mover o imóvel diretamente para a sua base principal.")

    try:
        sheet_leads = conectar_google_sheets("Leads_Captacao")
        dados_leads_raw = sheet_leads.get_all_records()
        
        if not dados_leads_raw:
            st.info("🎉 Nenhum lead pendente de triagem no momento!")
        else:
            df_leads = pd.DataFrame(dados_leads_raw)
            st.write(f"**Total de novos imóveis aguardando revisão:** {len(df_leads)}")
            st.markdown("---")

            for idx_l, row_l in df_leads.iterrows():
                linha_real_lead = idx_l + 2
                
                with st.expander(f"🔑 {row_l.get('Endereco_Imovel', 'Imóvel sem endereço')} — {row_l.get('Proprietario_Nome', 'Proprietário')} ({row_l.get('Finalidade', 'N/I')})", expanded=True):
                    
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**👤 Proprietário:** {row_l.get('Proprietario_Nome', '')}")
                    c1.markdown(f"**📱 Telefone:** {row_l.get('Proprietario_Telefone', '')}")
                    c1.markdown(f"**✉️ E-mail:** {row_l.get('Proprietario_Email', '')}")

                    c2.markdown(f"**📍 Endereço:** {row_l.get('Endereco_Imovel', '')}")
                    c2.markdown(f"**🏢 Finalidade:** {row_l.get('Finalidade', '')}")
                    c2.markdown(f"**💰 Valor Pretendido:** {row_l.get('Valor_Pretendido', '')}")

                    c3.markdown(f"**🏢 Condomínio:** {row_l.get('Valor_Condominio', '')}")
                    c3.markdown(f"**🏛️ IPTU:** {row_l.get('Valor_IPTU', '')}")
                    c3.markdown(f"**🔑 Chaves:** {row_l.get('Chaves_Local', '')}")

                    st.markdown(f"**📝 Observações do Form:** {row_l.get('Observacoes', '')}")
                    st.markdown("---")

                    btn_c1, btn_c2 = st.columns([2, 1])
                    
                    if btn_c1.button("✅ Aprovar e Mover para Carteira Oficial", key=f"btn_aprov_{idx_l}", type="primary"):
                        try:
                            # Prepara linha oficial na carteira
                            nova_linha_oficial = [
                                datetime.now().strftime("%d/%m/%Y %H:%M"),
                                str(row_l.get('Proprietario_Nome', '')),
                                str(row_l.get('Proprietario_Telefone', '')),
                                str(row_l.get('Proprietario_Email', '')),
                                str(row_l.get('Endereco_Imovel', '')),
                                str(row_l.get('Bairro', 'A definir')),
                                str(row_l.get('Tipo_Imovel', 'Apartamento')),
                                str(row_l.get('Finalidade', 'Locação')),
                                str(row_l.get('Valor_Pretendido', '')),
                                str(row_l.get('Valor_Condominio', '')),
                                str(row_l.get('Valor_IPTU', '')),
                                "Disponível",
                                str(row_l.get('Chaves_Local', '')),
                                str(row_l.get('Observacoes', ''))
                            ]
                            
                            sheet.append_row(nova_linha_oficial)
                            sheet_leads.delete_rows(linha_real_lead)
                            
                            st.success(f"✅ Imóvel **{row_l.get('Endereco_Imovel', '')}** aprovado e inserido na carteira!")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()
                        except Exception as e_ap:
                            st.error(f"Erro ao aprovar lead: {e_ap}")

                    if btn_c2.button("🗑️ Descartar Lead", key=f"btn_desc_{idx_l}"):
                        try:
                            sheet_leads.delete_rows(linha_real_lead)
                            st.warning("Lead descartado.")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()
                        except Exception as e_dc:
                            st.error(f"Erro ao descartar lead: {e_dc}")

    except Exception as e_tr:
        st.error(f"Erro ao carregar triagem de leads: {e_tr}")

# -----------------------------------------------------------------------------
# ABA 2: CADASTRAR NOVO IMÓVEL
# -----------------------------------------------------------------------------
with aba_cadastro:
    st.subheader("Novo Cadastro Rápido")
    
    if st.session_state.get("reset_carteira_form", False):
        st.session_state["c_prop_nome"] = ""
        st.session_state["c_prop_tel"] = ""
        st.session_state["c_prop_email"] = ""
        st.session_state["c_endereco"] = ""
        st.session_state["c_bairro"] = ""
        st.session_state["c_valor"] = ""
        st.session_state["c_cond"] = ""
        st.session_state["c_iptu"] = ""
        st.session_state["c_chaves"] = ""
        st.session_state["c_obs"] = ""
        st.session_state["reset_carteira_form"] = False
    
    with st.form("form_novo_imovel", clear_on_submit=False):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            proprietario_nome = st.text_input("Nome do Proprietário *", key="c_prop_nome")
            proprietario_telefone = st.text_input("Telefone / WhatsApp do Proprietário *", placeholder="(61) 90000-0000", key="c_prop_tel")
            proprietario_email = st.text_input("E-mail do Proprietário", key="c_prop_email")
        with col_p2:
            tipo_imovel = st.selectbox("Tipo de Imóvel *", ["Apartamento", "Casa", "Loja Comercial", "Sala Comercial", "Terreno", "Outro"], key="c_tipo")
            finalidade = st.selectbox("Finalidade *", ["Locação", "Venda", "Locação e Venda"], key="c_fin")
            status = st.selectbox("Status Atual *", ["Disponível", "Em Negociação", "Alugado", "Vendido", "Suspenso"], key="c_status")

        endereco_imovel = st.text_input("Endereço Completo do Imóvel (com Bloco/Apto) *", key="c_endereco")
        
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            bairro = st.text_input("Bairro / Região *", placeholder="Ex: Asa Sul, Sudoeste, Águas Claras", key="c_bairro")
            valor_pretendido = st.text_input("Valor Pretendido (R$) *", placeholder="Ex: 3500 ou 750000", key="c_valor")
        with col_v2:
            valor_condominio = st.text_input("Valor Condomínio (R$)", placeholder="Ex: 600", key="c_cond")
            valor_iptu = st.text_input("Valor IPTU (R$)", placeholder="Ex: 1500", key="c_iptu")
        with col_v3:
            chaves_local = st.text_input("Localização das Chaves / Acesso *", placeholder="Ex: Na portaria, com o dono, no escritório", key="c_chaves")

        observacoes = st.text_area("Observações Internas (Ex: aceita proposta, horário de visita, etc.)", key="c_obs")

        btn_salvar = st.form_submit_button("💾 Salvar na Carteira", type="primary")

    if btn_salvar:
        faltantes = []
        if not proprietario_nome:
            faltantes.append("Nome do Proprietário")
        if not proprietario_telefone:
            faltantes.append("Telefone / WhatsApp do Proprietário")
        if not endereco_imovel:
            faltantes.append("Endereço Completo do Imóvel")
        if not bairro:
            faltantes.append("Bairro / Região")
        if not valor_pretendido:
            faltantes.append("Valor Pretendido")
        if not chaves_local:
            faltantes.append("Localização das Chaves / Acesso")

        if faltantes:
            st.error(f"⚠️ **Preencha os seguintes campos obrigatórios antes de salvar:** {', '.join(faltantes)}.")
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
                
                st.session_state["reset_carteira_form"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao salvar dados: {e}")

# -----------------------------------------------------------------------------
# ABA 3: CONSULTAR E PESQUISAR CARTEIRA
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
                if "Finalidade" in df.columns:
                    filtro_finalidade = st.multiselect("Filtrar Finalidade:", options=df["Finalidade"].unique().tolist(), default=df["Finalidade"].unique().tolist())
                else:
                    filtro_finalidade = []
            with col_f3:
                if "Status" in df.columns:
                    filtro_status = st.multiselect("Filtrar Status:", options=df["Status"].unique().tolist(), default=df["Status"].unique().tolist())
                else:
                    filtro_status = []

            if "Finalidade" in df.columns and "Status" in df.columns:
                df_filtrado = df[
                    (df["Finalidade"].isin(filtro_finalidade)) &
                    (df["Status"].isin(filtro_status))
                ]
            else:
                df_filtrado = df

            if busca_texto:
                termo = busca_texto.lower()
                cols_busca = [col for col in ["Proprietario_Nome", "Endereco_Imovel", "Bairro"] if col in df.columns]
                
                if cols_busca:
                    df_filtrado = df_filtrado[df_filtrado[cols_busca].apply(lambda row: row.astype(str).str.lower().str.contains(termo).any(), axis=1)]

            st.write(f"**Total de Imóveis encontrados:** {len(df_filtrado)}")
            
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

# -----------------------------------------------------------------------------
# ABA 4: EDIÇÃO E EXCLUSÃO
# -----------------------------------------------------------------------------
with aba_editar:
    st.subheader("Alterar ou Excluir Registro")
    
    try:
        dados_raw = sheet.get_all_records()
        if dados_raw:
            df = pd.DataFrame(dados_raw)
            nome_coluna_endereco = df.columns[4] if len(df.columns) > 4 else None
            
            if nome_coluna_endereco:
                lista_imoveis = df[nome_coluna_endereco].dropna().unique().tolist()
                imovel_selecionado = st.selectbox("Selecione o imóvel que deseja gerenciar:", [""] + lista_imoveis)
                
                if imovel_selecionado:
                    linha_idx = df.index[df[nome_coluna_endereco] == imovel_selecionado].tolist()[0]
                    dados_atuais = df.iloc[linha_idx]
                    linha_real = linha_idx + 2
                    
                    with st.form("form_editar_dados"):
                        st.info(f"Editando dados do imóvel: **{imovel_selecionado}**")
                        
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            novo_status = st.selectbox("Status Atual", ["Disponível", "Em Negociação", "Alugado", "Vendido", "Suspenso"], 
                                                       index=["Disponível", "Em Negociação", "Alugado", "Vendido", "Suspenso"].index(dados_atuais.iloc[11]) if dados_atuais.iloc[11] in ["Disponível", "Em Negociação", "Alugado", "Vendido", "Suspenso"] else 0)
                            novo_valor = st.text_input("Valor Pretendido", value=str(dados_atuais.iloc[8]))
                        with col_e2:
                            novo_chaves = st.text_input("Localização das Chaves", value=str(dados_atuais.iloc[12]))
                            novas_obs = st.text_area("Observações", value=str(dados_atuais.iloc[13]))
                            
                        btn_atualizar = st.form_submit_button("🔄 Confirmar Alterações", type="primary")
                        
                        if btn_atualizar:
                            sheet.update_cell(linha_real, 12, novo_status)
                            sheet.update_cell(linha_real, 9, novo_valor)
                            sheet.update_cell(linha_real, 13, novo_chaves)
                            sheet.update_cell(linha_real, 14, novas_obs)
                            
                            st.success("✅ Dados atualizados com sucesso!")
                            st.rerun()
                    
                    st.markdown("---")
                    st.markdown("### ❌ Excluir Imóvel da Carteira")
                    st.warning("Cuidado: Esta ação apagará permanentemente este imóvel do banco de dados.")
                    
                    confirmar_exclusao = st.checkbox("Tenho certeza que desejo excluir este registro")
                    
                    if confirmar_exclusao:
                        if st.button("🗑️ Apagar Registro Definitivamente", type="primary"):
                            try:
                                try:
                                    sheet.delete_rows(linha_real)
                                except AttributeError:
                                    sheet.delete_row(linha_real)
                                
                                st.success("✅ Registro excluído com sucesso!")
                                st.cache_data.clear()
                                st.cache_resource.clear()
                                st.rerun()
                            except Exception as e_del:
                                st.error(f"❌ Erro ao tentar excluir o imóvel: {e_del}")
                            
    except Exception as e:
        st.error(f"Erro ao carregar módulo de edição: {e}")
