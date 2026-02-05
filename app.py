import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
        border: 1px solid #dce775;
    }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip().str.title() # Normalizar nombres
        
        # RENOMBRAR COLUMNAS PARA FACILITAR EL USO
        # Ajusta estos nombres si en tu Excel cambian ligeramente
        col_map = {
            'Nombre Del Colaborador': 'COLABORADOR',
            'Cargo': 'CARGO',
            'Formacion': 'CURSO',
            'Tipo De Curso': 'TIPO',
            'Niveles': 'NIVEL',
            'Capacitaciones': 'ESTADO_NUM' # 1 = SI, 0 = NO
        }
        # Renombramos solo las columnas que existan
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        
        # Asegurarnos que ESTADO_NUM sea numérico (rellenar vacíos con 0)
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        # Limpieza de Nivel (para asegurar que "Nivel 1" y "nivel 1" sean lo mismo)
        if 'NIVEL' in df.columns:
            df['NIVEL'] = df['NIVEL'].astype(str).str.strip().str.title()

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- GESTIÓN DEL ESTADO (MEMORIA DE FILTROS) ---
if 'filtro_activo' not in st.session_state:
    st.session_state.filtro_activo = 'Todos'

# --- TÍTULO ---
st.title("🎓 Control de Formación 2026")

if not df.empty:
    
    # --- CÁLCULO DE INDICADORES (KPIs) ---
    # 1. Estado (0 o 1)
    total_pendientes = len(df[df['ESTADO_NUM'] == 0])
    total_cumplieron = len(df[df['ESTADO_NUM'] == 1])
    
    # 2. Niveles (Buscamos texto que contenga "1" o "2")
    # Ajustamos la lógica para ser flexibles si dice "Nivel 1" o solo "1"
    df_n1 = df[df['NIVEL'].astype(str).str.contains("1", na=False)]
    df_n2 = df[df['NIVEL'].astype(str).str.contains("2", na=False)]
    
    total_n1 = len(df_n1)
    total_n2 = len(df_n2)

    # --- BOTONES DE FILTRO SUPERIOR ---
    st.markdown("### 🔘 Selecciona un grupo para filtrar:")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    
    # Definimos el color del botón (Primary = Activo, Secondary = Inactivo)
    btn_todos = "primary" if st.session_state.filtro_activo == 'Todos' else "secondary"
    btn_faltan = "primary" if st.session_state.filtro_activo == 'Faltan' else "secondary"
    btn_ok = "primary" if st.session_state.filtro_activo == 'Cumplieron' else "secondary"
    btn_n1 = "primary" if st.session_state.filtro_activo == 'Nivel 1' else "secondary"
    btn_n2 = "primary" if st.session_state.filtro_activo == 'Nivel 2' else "secondary"

    # Botón 1: TODOS
    if c1.button(f"📋 Ver Todos ({len(df)})", type=btn_todos, use_container_width=True):
        st.session_state.filtro_activo = 'Todos'
        
    # Botón 2: FALTAN (0) - Rojo/Alerta visual en el texto
    if c2.button(f"⏳ Faltan ({total_pendientes})", type=btn_faltan, use_container_width=True):
        st.session_state.filtro_activo = 'Faltan'

    # Botón 3: CUMPLIERON (1)
    if c3.button(f"✅ Cumplieron ({total_cumplieron})", type=btn_ok, use_container_width=True):
        st.session_state.filtro_activo = 'Cumplieron'

    # Botón 4: NIVEL 1
    if c4.button(f"🔹 Nivel 1 ({total_n1})", type=btn_n1, use_container_width=True):
        st.session_state.filtro_activo = 'Nivel 1'

    # Botón 5: NIVEL 2
    if c5.button(f"🔸 Nivel 2 ({total_n2})", type=btn_n2, use_container_width=True):
        st.session_state.filtro_activo = 'Nivel 2'

    st.divider()

    # --- APLICACIÓN DEL FILTRO ---
    df_view = df.copy()
    titulo_tabla = "Listado General"

    if st.session_state.filtro_activo == 'Faltan':
        df_view = df_view[df_view['ESTADO_NUM'] == 0]
        titulo_tabla = "⚠️ Personas que NO han realizado la capacitación"
        st.warning(f"Mostrando {len(df_view)} colaboradores pendientes.")
        
    elif st.session_state.filtro_activo == 'Cumplieron':
        df_view = df_view[df_view['ESTADO_NUM'] == 1]
        titulo_tabla = "✅ Personas que YA completaron la capacitación"
        st.success(f"Mostrando {len(df_view)} colaboradores capacitados.")
        
    elif st.session_state.filtro_activo == 'Nivel 1':
        df_view = df_n1
        titulo_tabla = "🔹 Listado Nivel 1"
        
    elif st.session_state.filtro_activo == 'Nivel 2':
        df_view = df_n2
        titulo_tabla = "🔸 Listado Nivel 2"

    # --- TABLA DE RESULTADOS ---
    st.subheader(titulo_tabla)
    
    # Columnas a mostrar (limpias)
    cols_mostrar = ['COLABORADOR', 'CARGO', 'CURSO', 'NIVEL', 'ESTADO_NUM']
    # Filtramos solo las que existen realmente en el dataframe
    cols_reales = [c for c in cols_mostrar if c in df_view.columns]

    st.dataframe(
        df_view[cols_reales],
        use_container_width=True,
        hide_index=True,
        column_config={
            "ESTADO_NUM": st.column_config.CheckboxColumn(
                "Realizado?",
                help="1 = Sí, 0 = No",
                disabled=True # Solo lectura
            ),
            "COLABORADOR": st.column_config.TextColumn("Colaborador", width="medium"),
            "CURSO": st.column_config.TextColumn("Capacitación", width="large"),
        }
    )

else:
    st.warning("No se encontraron datos. Verifica la conexión con la hoja de cálculo.")
