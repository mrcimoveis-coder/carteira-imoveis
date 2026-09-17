import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from decimal import Decimal, InvalidOperation
import unicodedata

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E LOGOMARCA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Carteira de Imóveis | MRC Imóveis", page_icon="🏢", layout="wide")

LOGO_URL = "https://raw.githubusercontent.com/mrcimoveis-coder/portal-intranet/main/logo.jpeg"

try:
    st.image(LOGO_URL, width=260)
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
SENHA_CORRETA = "431220"

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

def normalizar_busca(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto_sem_acentos = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return texto_sem_acentos.casefold().strip()

def formatar_moeda_brl(valor):
    """Formata números e textos monetários sem reinterpretar ponto de milhar como decimal."""
    if valor is None or str(valor).strip() == "":
        return ""
    original = str(valor).strip()
    limpo = original.upper().replace("R$", "").replace("\xa0", "").replace(" ", "")

    if "," in limpo:
        normalizado = limpo.replace(".", "").replace(",", ".")
    elif limpo.count(".") > 1:
        normalizado = limpo.replace(".", "")
    elif limpo.count(".") == 1:
        inteiro, decimal = limpo.split(".", 1)
        normalizado = inteiro + decimal if len(decimal) == 3 else limpo
    else:
        normalizado = limpo

    try:
        numero = Decimal(normalizado)
    except (InvalidOperation, ValueError):
        return original

    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def carregar_carteira_com_linhas(sheet_carteira):
    """Lê os valores como aparecem no Sheets e conserva a linha real para edição segura."""
    valores = sheet_carteira.get_all_values()
    if not valores:
        return pd.DataFrame()

    cabecalho = valores[0]
    registros = []
    for linha_planilha, linha in enumerate(valores[1:], start=2):
        linha_completa = list(linha) + [""] * max(0, len(cabecalho) - len(linha))
        linha_completa = linha_completa[:len(cabecalho)]
        if not any(str(valor).strip() for valor in linha_completa):
            continue
        registro = dict(zip(cabecalho, linha_completa))
        registro["_linha_planilha"] = linha_planilha
        registros.append(registro)
    return pd.DataFrame(registros)

aba_triagem, aba_cadastro, aba_consulta, aba_editar = st.tabs([
    "📥 Triagem / Novos Leads", 
    "➕ Cadastrar Novo Imóvel", 
    "🔍 Consultar e Pesquisar Carteira", 
    "✏️ Editar Imóvel"
])

# -----------------------------------------------------------------------------
# ABA 1: TRIAGEM DE LEADS VINDOS DO SITE
# -----------------------------------------------------------------------------
with aba_triagem:
    st.subheader("📥 Imóveis Enviados pelo Site (Pendentes de Aprovação)")
    st.caption("Verifique as informações enviadas pelos proprietários e aprove para mover o imóvel diretamente para a sua base principal.")

    try:
        sheet_leads = conectar_google_sheets("Leads_Captacao")
        todos_valores = sheet_leads.get_all_values()
        
        if not todos_valores:
            st.info("🎉 Nenhum lead pendente de triagem no momento!")
        else:
            primeira_linha = todos_valores[0]
            if "Proprietario_Nome" in primeira_linha or "Endereco_Imovel" in primeira_linha:
                header = primeira_linha
                linhas_dados = todos_valores[1:]
            else:
                header = [
                    "Data_Registro", "Proprietario_Nome", "Proprietario_Telefone", "Proprietario_Email",
                    "Endereco_Imovel", "Bairro", "Tipo_Imovel", "Finalidade", "Valor_Pretendido",
                    "Valor_Condominio", "Valor_IPTU", "Status", "Chaves_Local", "Observacoes"
                ]
                linhas_dados = todos_valores

            if not linhas_dados:
                st.info("🎉 Nenhum lead pendente de triagem no momento!")
            else:
                st.write(f"**Total de novos imóveis aguardando revisão:** {len(linhas_dados)}")
                st.markdown("---")

                for idx, row in enumerate(linhas_dados):
                    def get_val(col_idx):
                        if len(row) > col_idx and row[col_idx]:
                            return row[col_idx]
                        return "N/I"

                    data_reg = get_val(0)
                    prop_nome = get_val(1)
                    prop_tel = get_val(2)
                    prop_email = get_val(3)
                    end_imovel = get_val(4)
                    bairro_lead = get_val(5)
                    tipo_lead = get_val(6)
                    fin_lead = get_val(7)
                    val_pret = get_val(8)
                    val_cond = get_val(9)
                    val_iptu = get_val(10)
                    status_lead = get_val(11)
                    chaves_lead = get_val(12)
                    obs_lead = get_val(13)

                    linha_real_lead = idx + (2 if header == primeira_linha else 1)

                    with st.expander(f"🔑 {end_imovel} — {prop_nome} ({fin_lead})", expanded=True):
                        c1, c2, c3 = st.columns(3)
                        c1.markdown(f"**👤 Proprietário:** {prop_nome}")
                        c1.markdown(f"**📱 Telefone:** {prop_tel}")
                        c1.markdown(f"**✉️ E-mail:** {prop_email}")

                        c2.markdown(f"**📍 Endereço:** {end_imovel}")
                        c2.markdown(f"**🏢 Finalidade:** {fin_lead}")
                        c2.markdown(f"**💰 Valor Pretendido:** {val_pret}")

                        c3.markdown(f"**🏢 Condomínio:** {val_cond}")
                        c3.markdown(f"**🏛️ IPTU:** {val_iptu}")
                        c3.markdown(f"**🔑 Chaves:** {chaves_lead}")

                        st.markdown(f"**📝 Observações do Form:** {obs_lead}")
                        st.markdown("---")

                        btn_c1, btn_c2 = st.columns([2, 1])
                        
                        if btn_c1.button("✅ Aprovar e Mover para Carteira Oficial", key=f"btn_aprov_{idx}", type="primary"):
                            try:
                                nova_linha_oficial = [
                                    data_reg,
                                    prop_nome,
                                    prop_tel,
                                    prop_email,
                                    end_imovel,
                                    bairro_lead if bairro_lead != "N/I" else "A definir",
                                    tipo_lead if tipo_lead != "N/I" else "Apartamento",
                                    fin_lead if fin_lead != "N/I" else "Locação",
                                    val_pret if val_pret != "N/I" else "",
                                    val_cond if val_cond != "N/I" else "",
                                    val_iptu if val_iptu != "N/I" else "",
                                    "Disponível",
                                    chaves_lead if chaves_lead != "N/I" else "",
                                    obs_lead if obs_lead != "N/I" else ""
                                ]
                                
                                sheet.append_row(nova_linha_oficial)
                                sheet_leads.delete_rows(linha_real_lead)
                                
                                st.success(f"✅ Imóvel **{end_imovel}** aprovado e inserido na carteira!")
                                st.cache_data.clear()
                                st.cache_resource.clear()
                                st.rerun()
                            except Exception as e_ap:
                                st.error(f"Erro ao aprovar lead: {e_ap}")

                        if btn_c2.button("🗑️ Descartar Lead", key=f"btn_desc_{idx}"):
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
        df = carregar_carteira_com_linhas(sheet)
        if df.empty:
            st.info("Nenhum imóvel cadastrado na carteira até o momento.")
        else:
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
                termo = normalizar_busca(busca_texto)
                cols_busca = [col for col in ["Proprietario_Nome", "Endereco_Imovel", "Bairro"] if col in df.columns]

                if cols_busca:
                    mascara = df_filtrado[cols_busca].apply(
                        lambda row: any(termo in normalizar_busca(valor) for valor in row),
                        axis=1,
                    )
                    df_filtrado = df_filtrado[mascara]

            st.write(f"**Total de Imóveis encontrados:** {len(df_filtrado)}")

            df_exibicao = df_filtrado.drop(columns=["_linha_planilha"], errors="ignore").copy()
            for coluna_valor in ["Valor_Pretendido", "Valor_Condominio", "Valor_IPTU"]:
                if coluna_valor in df_exibicao.columns:
                    df_exibicao[coluna_valor] = df_exibicao[coluna_valor].apply(formatar_moeda_brl)

            st.dataframe(
                df_exibicao,
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
    st.subheader("Alterar Dados do Imóvel")
    st.caption("As alterações feitas nesta área apenas atualizam o imóvel. Nenhum registro será excluído ao confirmar uma edição.")

    if st.session_state.pop("carteira_edicao_sucesso", False):
        st.success("✅ Dados atualizados com sucesso!")
    
    try:
        df = carregar_carteira_com_linhas(sheet)
        if not df.empty:
            nome_coluna_endereco = "Endereco_Imovel" if "Endereco_Imovel" in df.columns else None

            if nome_coluna_endereco:
                indices_imoveis = df.index[df[nome_coluna_endereco].astype(str).str.strip() != ""].tolist()

                def rotulo_imovel(indice):
                    if indice is None:
                        return "Selecione um imóvel"
                    endereco = str(df.at[indice, nome_coluna_endereco])
                    proprietario = str(df.at[indice, "Proprietario_Nome"]) if "Proprietario_Nome" in df.columns else ""
                    return f"{endereco} — {proprietario}" if proprietario else endereco

                imovel_selecionado = st.selectbox(
                    "Selecione o imóvel que deseja editar:",
                    [None] + indices_imoveis,
                    format_func=rotulo_imovel,
                )

                if imovel_selecionado is not None:
                    dados_atuais = df.loc[imovel_selecionado]
                    linha_real = int(dados_atuais["_linha_planilha"])
                    endereco_selecionado = str(dados_atuais[nome_coluna_endereco])
                    cabecalho_planilha = sheet.row_values(1)
                    colunas_planilha = {nome: indice + 1 for indice, nome in enumerate(cabecalho_planilha)}

                    with st.form("form_editar_dados"):
                        st.info(f"Editando dados do imóvel: **{endereco_selecionado}**")

                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            novo_status = st.selectbox("Status Atual", ["Disponível", "Em Negociação", "Alugado", "Vendido", "Suspenso"], 
                                                       index=["Disponível", "Em Negociação", "Alugado", "Vendido", "Suspenso"].index(dados_atuais.get("Status", "")) if dados_atuais.get("Status", "") in ["Disponível", "Em Negociação", "Alugado", "Vendido", "Suspenso"] else 0)
                            novo_valor = st.text_input("Valor Pretendido", value=str(dados_atuais.get("Valor_Pretendido", "")))
                        with col_e2:
                            novo_chaves = st.text_input("Localização das Chaves", value=str(dados_atuais.get("Chaves_Local", "")))
                            novas_obs = st.text_area("Observações", value=str(dados_atuais.get("Observacoes", "")))
                            
                        btn_atualizar = st.form_submit_button("🔄 Confirmar Alterações", type="primary")
                        
                        if btn_atualizar:
                            campos_atualizados = {
                                "Status": novo_status,
                                "Valor_Pretendido": novo_valor,
                                "Chaves_Local": novo_chaves,
                                "Observacoes": novas_obs,
                            }
                            for nome_coluna, novo_conteudo in campos_atualizados.items():
                                if nome_coluna not in colunas_planilha:
                                    raise ValueError(f"Coluna obrigatória não encontrada: {nome_coluna}")
                                sheet.update_cell(linha_real, colunas_planilha[nome_coluna], novo_conteudo)

                            st.session_state["carteira_edicao_sucesso"] = True
                            st.rerun()

                    with st.expander("🗑️ Excluir este imóvel (ação separada)", expanded=False):
                        st.warning("Somente o botão abaixo exclui o imóvel. Confirmar alterações no formulário acima não apaga o registro.")
                        confirmar_exclusao = st.checkbox(
                            "Tenho certeza que desejo excluir este registro definitivamente",
                            key=f"confirmar_exclusao_{linha_real}",
                        )

                        if confirmar_exclusao:
                            if st.button("🗑️ Apagar Registro Definitivamente", type="primary", key=f"excluir_{linha_real}"):
                                try:
                                    try:
                                        sheet.delete_rows(linha_real)
                                    except AttributeError:
                                        sheet.delete_row(linha_real)

                                    st.success("✅ Registro excluído com sucesso!")
                                    st.rerun()
                                except Exception as e_del:
                                    st.error(f"❌ Erro ao tentar excluir o imóvel: {e_del}")
                            
    except Exception as e:
        st.error(f"Erro ao carregar módulo de edição: {e}")
