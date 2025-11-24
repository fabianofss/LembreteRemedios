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
#creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

# Abre a planilha pelo nome
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1HQlAXtNT1sLCOePXTMD0SwgRcRjuIP8MdXBZwGZVOj4/edit?usp=sharing")

# Seleciona as abas
users_sheet = spreadsheet.worksheet("Usuarios")
meds_sheet = spreadsheet.worksheet("Medicamentos")

# --- Funções Auxiliares ---
# Obtém a lista de usuários
def get_users():
    """Retorna uma lista de nomes de usuários."""
    records = users_sheet.get_all_records()
    return [record['Nome'] for record in records]
# Obtém a lista de medicamentos
def get_meds():
    """Retorna um DataFrame com os medicamentos."""
    return pd.DataFrame(meds_sheet.get_all_records())
# Adiciona um novo usuário
def add_user(name):
    """Adiciona um novo usuário na planilha."""
    users_sheet.append_row([name])
# Adiciona um novo medicamento
def add_med(user, med_name, interval, doses, start_time):
    """Adiciona um novo medicamento na planilha."""
    for i in range(int(doses)):
        dose_time = start_time + timedelta(hours=int(interval) * i)
        meds_sheet.append_row([user, med_name, dose_time.strftime("%Y-%m-%d %H:%M:%S"), "Pendente"])

# --- Interface do Streamlit ---
st.set_page_config(page_title="Gerenciador de Medicamentos", layout="wide")

st.title("💊 Gerenciador de Medicamentos")
st.markdown("---")

# Barra lateral de navegação
st.sidebar.title("Navegação")
page = st.sidebar.radio("Ir para", ["Tela Principal", "Cadastrar Usuário", "Cadastrar Medicamento", "Base de Dados"])

if page == "Tela Principal":
    st.header("Visão Geral do Tratamento")

    meds_df = get_meds()

    if meds_df.empty:
        st.info("Nenhum medicamento cadastrado ainda. Vá para a tela de cadastro para começar.")
    else:
        # Garante que a coluna de horário esteja no formato datetime
        meds_df['Horario'] = pd.to_datetime(meds_df['Horario'])

        # --- Seção: Próximos Medicamentos ---
        st.subheader("🗓️ Próximos Medicamentos")

        # Obter data e hora atual
        now = datetime.now()

        # Filtra medicamentos pendentes que ainda não venceram
        pending_meds = meds_df[
            (meds_df['Status'] == 'Pendente') &
            (meds_df['Horario'] > now)
        ].sort_values(by='Horario')

        if not pending_meds.empty:
            next_med = pending_meds.iloc[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Paciente", next_med['Usuario'])
            col2.metric("Medicamento", next_med['Medicamento'])
            col3.metric("Horário", next_med['Horario'].strftime("%d/%m/%Y %H:%M"))

            st.markdown("##### Lista de Próximos Medicamentos")
            # Renomeia as colunas para exibição na tabela
            pending_display = pending_meds[['Usuario', 'Medicamento', 'Horario']].rename(columns={'Usuario': 'Paciente', 'Medicamento': 'Remédio', 'Horario': 'Data e Hora'})
            st.dataframe(pending_display, use_container_width=True, hide_index=True)
        else:
            st.info("Não há medicamentos pendentes com horários futuros.")

        st.markdown("---") # Divisor visual

        # --- Seção: Gráficos e Estatísticas ---
        st.header("📊 Estatísticas do Tratamento")

        # Filtra apenas os medicamentos que já foram administrados
        admin_df = meds_df[meds_df['Status'].str.lower() == 'administrado'].copy()

        if admin_df.empty:
            st.warning("Nenhuma dose foi marcada como 'Administrado' ainda. Os gráficos aparecerão aqui quando houver dados.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                # --- Gráfico 1: Medicamentos Mais Administrados ---
                st.subheader("Medicamentos Mais Administrados")
                
                # Conta a ocorrência de cada medicamento
                meds_count = admin_df['Medicamento'].value_counts()
                
                # Exibe o gráfico de barras
                st.bar_chart(meds_count)
                st.caption("Este gráfico mostra a contagem total de doses administradas por tipo de medicamento.")


            with col2:
                # --- Gráfico 2: Histórico de Doses Administradas por Dia ---
                st.subheader("Histórico de Doses por Dia")
                
                # Define a coluna 'Horario' como índice para agrupar por dia
                admin_df.set_index('Horario', inplace=True)
                
                # Agrupa por dia e conta o número de doses (registros)
                doses_per_day = admin_df.resample('D').size()
                doses_per_day.rename("Doses Administradas", inplace=True)
                
                # Exibe o gráfico de área
                st.area_chart(doses_per_day)
                st.caption("Este gráfico mostra o número de doses totais administradas em cada dia.")

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
            
            # Campos para data e hora da primeira dose
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Data da primeira dose", value=datetime.now().date())
            with col2:
                start_time = st.time_input("Horário da primeira dose", value=datetime.now().time())

            submitted = st.form_submit_button("Cadastrar Medicamento")
            if submitted:
                if selected_user and med_name and interval and doses and start_date and start_time:
                    # Combina data e hora em um objeto datetime
                    start_datetime = datetime.combine(start_date, start_time)
                    add_med(selected_user, med_name, interval, doses, start_datetime)
                    st.success(f"Medicamento '{med_name}' cadastrado para '{selected_user}' com primeira dose em {start_datetime.strftime('%d/%m/%Y às %H:%M')}!")
                else:
                    st.error("Por favor, preencha todos os campos.")

if page == "Base de Dados":
    st.header("Base de Dados de Medicamentos")

    df = get_meds()

    if df.empty:
        st.warning("⚠️ Nenhum registro encontrado na base de dados.")
    else:
        
        # Converter a coluna de horário para datetime
        df['Horario'] = pd.to_datetime(df['Horario'])

        # Criar colunas para os filtros
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Filtro de Paciente
            pacientes = ['Todos'] + sorted(df['Usuario'].unique().tolist())
            paciente_selecionado = st.selectbox('👤 Paciente', pacientes)
        
        with col2:
            # Filtro de Medicamento
            medicamentos = ['Todos'] + sorted(df['Medicamento'].unique().tolist())
            medicamento_selecionado = st.selectbox('💊 Medicamento', medicamentos)
        
        with col3:
            # Filtro de Data Inicial
            data_min = df['Horario'].min().date()
            data_max = df['Horario'].max().date()
            data_inicial = st.date_input(
                '📅 Data Inicial',
                value=data_min,
                min_value=data_min,
                max_value=data_max
            )
        
        with col4:
            # Filtro de Data Final
            data_final = st.date_input(
                '📅 Data Final',
                value=data_max,
                min_value=data_min,
                max_value=data_max
            )
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if paciente_selecionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['Usuario'] == paciente_selecionado]
        
        if medicamento_selecionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['Medicamento'] == medicamento_selecionado]
        
        # Filtrar por intervalo de datas
        df_filtrado = df_filtrado[
            (df_filtrado['Horario'].dt.date >= data_inicial) &
            (df_filtrado['Horario'].dt.date <= data_final)
        ]
        
        # Exibir métricas Tomado
        st.markdown("---")
        metric1, metric2, metric3, metric4 = st.columns(4)
        
        with metric1:
            st.metric("📋 Total de Registros", len(df_filtrado))
        
        with metric2:
            st.metric("👥 Pacientes", df_filtrado['Usuario'].nunique())

        with metric3:
            st.metric("💊 Medicamentos", df_filtrado['Medicamento'].nunique())
        
        with metric4:
            # Contar doses tomadas
            doses_tomadas = df_filtrado[df_filtrado['Status'] == 'Administrado'].shape[0]
            st.metric("✅ Doses Tomadas", doses_tomadas)
        
        st.markdown("---")
        
        # Opções de visualização
        col_opcoes1, col_opcoes2, col_opcoes3 = st.columns(3)
        
        with col_opcoes1:
            mostrar_apenas_pendentes = st.checkbox('📌 Mostrar apenas doses pendentes')
        
        with col_opcoes2:
            ordenar_por = st.selectbox(
                '🔽 Ordenar por',
                ['Horario', 'Usuario', 'Medicamento', 'Status'],
                index=0
            )
        
        with col_opcoes3:
            ordem = st.radio('Ordem', ['Crescente', 'Decrescente'], horizontal=True)
        
        # Aplicar filtro de pendentes
        if mostrar_apenas_pendentes:
            df_filtrado = df_filtrado[df_filtrado['Status'] == 'Pendente']
        
        # Ordenar
        ascending = True if ordem == 'Crescente' else False
        df_filtrado = df_filtrado.sort_values(by=ordenar_por, ascending=ascending)
        
        # Exibir tabela
        st.markdown("### 📋 Registros")
        
        if df_filtrado.empty:
            st.info("ℹ️ Nenhum registro encontrado com os filtros aplicados.")
        else:
            # Formatar a coluna de data para exibição
            df_display = df_filtrado.copy()
            df_display['Horario'] = df_display['Horario'].dt.strftime('%d/%m/%Y %H:%M')

            # Colorir linhas baseado no status
            def highlight_status(row):
                # Define a cor da fonte como preta para todas as condições
                style = 'color: black; '
                
                # Usa a coluna 'Status' original para a lógica
                status = row['Status']
                
                # Usa a coluna 'Horario' original para comparar com a data atual
                # Precisamos acessar o dataframe original 'df_filtrado' porque 'df_display' tem o horário formatado como texto
                horario_real = df_filtrado.loc[row.name, 'Horario']
                agora = datetime.now()

                if status == 'Administrado':
                    style += 'background-color: #d4edda;'  # Verde claro
                elif status == 'Pendente' and horario_real < agora:
                    style += 'background-color: #ff4b4b;'  # Vermelho claro para atrasados
                else: # Status é 'Pendente' e ainda não venceu
                    style += 'background-color: #fff3cd;'  # Amarelo claro
                
                return [style] * len(row)
            
            st.dataframe(
                df_display.style.apply(highlight_status, axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            # Legenda
            st.markdown("""
            **Legenda de cores:**
            - 🟢 Verde: Dose tomada
            - 🟡 Amarelo: Dose pendente (ainda não vencida)
            - 🔴 Vermelho: Dose atrasada (não tomada no horário)
            """)
            
            # Botão de download
            st.markdown("---")
            csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Baixar dados filtrados (CSV)",
                data=csv,
                file_name=f"medicamentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Botão para atualizar dados
        st.markdown("---")
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()