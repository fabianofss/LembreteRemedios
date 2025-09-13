import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# --- Configuração do Google Sheets ---
# Autenticação
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
client = gspread.authorize(creds)

# Abre a planilha pelo nome
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1HQlAXtNT1sLCOePXTMD0SwgRcRjuIP8MdXBZwGZVOj4/edit?usp=sharing")

# Seleciona as abas
users_sheet = spreadsheet.worksheet("Usuarios")
meds_sheet = spreadsheet.worksheet("Medicamentos")

# --- Funções Auxiliares ---
def get_users():
    """Retorna uma lista de nomes de usuários."""
    records = users_sheet.get_all_records()
    return [record['Nome'] for record in records]

def get_meds():
    """Retorna um DataFrame com os medicamentos."""
    return pd.DataFrame(meds_sheet.get_all_records())

def add_user(name):
    """Adiciona um novo usuário na planilha."""
    users_sheet.append_row([name])

def add_med(user, med_name, interval, doses):
    """Adiciona um novo medicamento na planilha."""
    start_time = datetime.now()
    for i in range(int(doses)):
        dose_time = start_time + timedelta(hours=int(interval) * i)
        meds_sheet.append_row([user, med_name, dose_time.strftime("%Y-%m-%d %H:%M:%S"), "Pendente"])

# --- Interface do Streamlit ---
st.set_page_config(page_title="Gerenciador de Medicamentos", layout="wide")

st.title("💊 Gerenciador de Medicamentos")
st.markdown("---")

# Barra lateral de navegação
st.sidebar.title("Navegação")
page = st.sidebar.radio("Ir para", ["Tela Principal", "Cadastrar Usuário", "Cadastrar Medicamento"])

if page == "Tela Principal":
    st.header("Próximos Medicamentos")

    meds_df = get_meds()

    if meds_df.empty:
        st.info("Nenhum medicamento cadastrado ainda. Vá para a tela de cadastro para começar.")
    else:
        # Converte a coluna de horário para datetime
        meds_df['Horario'] = pd.to_datetime(meds_df['Horario'])

        # Filtra medicamentos pendentes
        pending_meds = meds_df[meds_df['Status'] == 'Pendente'].sort_values(by='Horario')

        if not pending_meds.empty:
            next_med = pending_meds.iloc[0]
            st.subheader("Próximo a ser tomado:")
            col1, col2, col3 = st.columns(3)
            col1.metric("Paciente", next_med['Usuario'])
            col2.metric("Medicamento", next_med['Medicamento'])
            col3.metric("Horário", next_med['Horario'].strftime("%d/%m/%Y %H:%M"))

            st.markdown("---")
            st.subheader("Lista de Próximos Medicamentos")
            st.dataframe(pending_meds[['Usuario', 'Medicamento', 'Horario']].rename(columns={'Usuario': 'Paciente', 'Medicamento': 'Remédio', 'Horario': 'Data e Hora'}), use_container_width=True)
        else:
            st.success("Todos os medicamentos já foram administrados!")

elif page == "Cadastrar Usuário":
    st.header("Cadastrar Novo Usuário")
    with st.form("new_user_form", clear_on_submit=True):
        new_user_name = st.text_input("Nome do Usuário")
        submitted = st.form_submit_button("Cadastrar")
        if submitted and new_user_name:
            add_user(new_user_name)
            st.success(f"Usuário '{new_user_name}' cadastrado com sucesso!")
        elif submitted:
            st.error("Por favor, insira o nome do usuário.")

elif page == "Cadastrar Medicamento":
    st.header("Cadastrar Novo Medicamento")
    users = get_users()
    if not users:
        st.warning("Nenhum usuário cadastrado. Por favor, cadastre um usuário primeiro.")
    else:
        with st.form("new_med_form", clear_on_submit=True):
            selected_user = st.selectbox("Selecione o Usuário", options=users)
            med_name = st.text_input("Nome do Medicamento")
            interval = st.number_input("Intervalo entre as doses (em horas)", min_value=1, step=1)
            doses = st.number_input("Quantidade de doses", min_value=1, step=1)

            submitted = st.form_submit_button("Cadastrar Medicamento")
            if submitted:
                if selected_user and med_name and interval and doses:
                    add_med(selected_user, med_name, interval, doses)
                    st.success(f"Medicamento '{med_name}' cadastrado para '{selected_user}' com sucesso!")
                else:
                    st.error("Por favor, preencha todos os campos.")