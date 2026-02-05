import streamlit as st
import pandas as pd

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
    section[data-testid="stSidebar"] .stRadio label {
        font-weight: bold;
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
        # Normalizar nombres de columnas (Quitar espacios extra y poner Título)
        df.columns = df.columns.str.strip().str.title()
        
        # --- MAPEO DE COLUMNAS (Aquí está el cambio clave) ---
        col_map = {
            'Rol En El Concesionario': 'CARGO',    # Usamos la Columna A como el filtro principal
            'Nombre Del Colaborador': 'COLABORADOR',
            'Formacion': 'CURSO',
            'Tipo De Curso': 'TIPO',
            'Niveles': 'NIVEL',
            'Capacitaciones': 'ESTADO_NUM'
        }
        # Renombrar solo las columnas que encuentre
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        
        # LIMPIEZA DE DATOS
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        if 'NIVEL' in df.columns:
            df['NIVEL'] = df['NIVEL'].astype(str).str.strip().str.title()

        if 'CARGO' in df.columns:
            df['CARGO'] = df['CARGO'].astype(str).str.strip().str.title()

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- BARRA LATERAL (FILTRO POR ROL) ---
st.sidebar.title("🏢 Filtro por Rol")

df_filtrado_cargo = df.copy()

# Variables para manejar la selección
lista_cargos = []
cargo_seleccionado = "Todos"

if not df.empty and 'CARGO' in df.columns:
    # 1. Lista de Roles únicos (de la Columna A)
    lista_cargos = sorted(df['CARGO'].dropna().unique().tolist())
    
    # 2. Menú de selección
    opciones_menu = ["Todos"] + lista_cargos
    cargo_seleccionado = st.sidebar.radio("Selecciona un Rol:", opciones_menu)
    
    # 3. Filtrado
    if cargo_seleccionado != "Todos":
        df_filtrado_cargo = df[df['CARGO'] == cargo_seleccionado]
        st.sidebar.success(f"Rol: {cargo_seleccionado}")
        st.sidebar.metric("Colaboradores", len(df_filtrado_cargo))
    else:
        st.sidebar.info("Mostrando toda la nómina")

st.sidebar.markdown("---")

# --- MEMORIA DE FILTROS SUPERIORES ---
if 'filtro_activo' not in st.session_state:
    st.session_state.filtro_activo = 'Todos'

# --- TÍTULO ---
titulo_principal = f"🎓 Control de Formación - {cargo_seleccionado}"
st.title(titulo_principal)

if not df_filtrado_cargo.empty:
    
    # --- CÁLCULO DE INDICADORES (KPIs) ---
    total_personas_cargo = len(df_filtrado_cargo)
    total_pendientes = len(df_filtrado_cargo[df_filtrado_cargo['ESTADO_NUM'] == 0])
    total_cumplieron = len(df_filtrado_cargo[df_filtrado_cargo['ESTADO_NUM'] == 1])
    
    # Niveles
    df_n1 = df_filtrado_cargo[df_filtrado_cargo['NIVEL'].astype(str).str.contains("1", na=False)]
    df_n2 = df_filtrado_cargo[df_filtrado_cargo['NIVEL'].astype(str).str.contains("2", na=False)]
    
    total_n1 = len(df_n1)
    total_n2 = len(df_n2)

    # --- BOTONERA SUPERIOR ---
    st.markdown("### 📊 Estado del Grupo Seleccionado:")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    
    # Estilos de botones
    b_all = "primary" if st.session_state.filtro_activo == 'Todos' else "secondary"
    b_fal = "primary" if st.session_state.filtro_activo == 'Faltan' else "secondary"
    b_ok = "primary" if st.session_state.filtro_activo == 'Cumplieron' else "secondary"
    b_n1 = "primary" if st.session_state.filtro_activo == 'Nivel 1' else "secondary"
    b_n2 = "primary" if st.session_state.filtro_activo == 'Nivel 2' else "secondary"

    if c1.button(f"📋 Ver Lista ({total_personas_cargo})", type=b_all, use_container_width=True):
        st.session_state.filtro_activo = 'Todos'
    if c2.button(f"⏳ Faltan ({total_pendientes})", type=b_fal, use_container_width=True):
        st.session_state.filtro_activo = 'Faltan'
    if c3.button(f"✅ Cumplieron ({total_cumplieron})", type=b_ok, use_container_width=True):
        st.session_state.filtro_activo = 'Cumplieron'
    if c4.button(f"🔹 Nivel 1 ({total_n1})", type=b_n1, use_container_width=True):
        st.session_state.filtro_activo = 'Nivel 1'
    if c5.button(f"🔸 Nivel 2 ({total_n2})", type=b_n2, use_container_width=True):
        st.session_state.filtro_activo = 'Nivel 2'

    st.divider()

    # --- APLICACIÓN DEL FILTRO SUPERIOR ---
    df_final_view = df_filtrado_cargo.copy()
    subtitulo = "Listado Completo"

    if st.session_state.filtro_activo == 'Faltan':
        df_final_view = df_final_view[df_final_view['ESTADO_NUM'] == 0]
        subtitulo = "⚠️ Personas Pendientes"
    elif st.session_state.filtro_activo == 'Cumplieron':
        df_final_view = df_final_view[df_final_view['ESTADO_NUM'] == 1]
        subtitulo = "✅ Personas Cumplidoras"
    elif st.session_state.filtro_activo == 'Nivel 1':
        df_final_view = df_n1
        subtitulo = "🔹 Listado Nivel 1"
    elif st.session_state.filtro_activo == 'Nivel 2':
        df_final_view = df_n2
        subtitulo = "🔸 Listado Nivel 2"

    # --- TABLA DE RESULTADOS ---
    st.subheader(f"{subtitulo} ({len(df_final_view)})")
    
    cols_mostrar = ['COLABORADOR', 'CARGO', 'CURSO', 'NIVEL', 'ESTADO_NUM']
    cols_reales = [c for c in cols_mostrar if c in df_final_view.columns]

    st.dataframe(
        df_final_view[cols_reales],
        use_container_width=True,
        hide_index=True,
        column_config={
            "ESTADO_NUM": st.column_config.CheckboxColumn("Realizado", disabled=True),
            "COLABORADOR": st.column_config.TextColumn("Colaborador", width="medium"),
            "CARGO": st.column_config.TextColumn("Rol / Cargo", width="medium"), # Etiqueta actualizada
            "CURSO": st.column_config.TextColumn("Capacitación", width="large"),
        }
    )

else:
    st.warning("No se encontraron datos. Verifica la conexión con Google Sheets.")
