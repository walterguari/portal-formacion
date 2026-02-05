import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        min-height: 3em; /* Altura mínima para que se vean bien */
        height: auto;
        font-weight: bold;
        border: 1px solid #dce775;
        white-space: pre-wrap; /* Permite que nombres largos bajen de línea */
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
        df.columns = df.columns.str.strip().str.title()
        
        col_map = {
            'Rol En El Concesionario': 'CARGO',
            'Nombre Del Colaborador': 'COLABORADOR',
            'Formacion': 'CURSO',
            'Tipo De Curso': 'TIPO',
            'Niveles': 'NIVEL',
            'Capacitaciones': 'ESTADO_NUM'
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        if 'NIVEL' in df.columns:
            df['NIVEL'] = df['NIVEL'].astype(str).str.strip().str.title()

        if 'CARGO' in df.columns:
            df['CARGO'] = df['CARGO'].astype(str).str.strip().str.title()

        if 'COLABORADOR' in df.columns:
            df['COLABORADOR'] = df['COLABORADOR'].astype(str).str.strip().str.upper()

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- BARRA LATERAL (FILTRO POR ROL) ---
st.sidebar.title("🏢 Filtro por Rol")

df_filtrado_cargo = df.copy()
lista_cargos = []
cargo_seleccionado = "Todos"

# Gestión de memoria para resetear colaborador si cambia el cargo
if 'ultimo_cargo_sel' not in st.session_state:
    st.session_state.ultimo_cargo_sel = "Todos"

if not df.empty and 'CARGO' in df.columns:
    lista_cargos = sorted(df['CARGO'].dropna().unique().tolist())
    opciones_menu = ["Todos"] + lista_cargos
    cargo_seleccionado = st.sidebar.radio("Selecciona un Rol:", opciones_menu)
    
    # Detectar cambio de cargo para resetear el filtro de persona
    if cargo_seleccionado != st.session_state.ultimo_cargo_sel:
        st.session_state.colaborador_activo = 'Todos'
        st.session_state.ultimo_cargo_sel = cargo_seleccionado

    if cargo_seleccionado != "Todos":
        df_filtrado_cargo = df[df['CARGO'] == cargo_seleccionado]
        st.sidebar.success(f"Rol: {cargo_seleccionado}")
        st.sidebar.metric("Colaboradores", len(df_filtrado_cargo))
    else:
        st.sidebar.info("Mostrando toda la nómina")

st.sidebar.markdown("---")

# --- MEMORIA DE FILTROS ---
if 'filtro_activo' not in st.session_state: st.session_state.filtro_activo = 'Todos'
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'

# --- TÍTULO ---
st.title(f"🎓 Control de Formación - {cargo_seleccionado}")

if not df_filtrado_cargo.empty:
    
    # --- KPIs ---
    total_personas_cargo = len(df_filtrado_cargo)
    total_pendientes = len(df_filtrado_cargo[df_filtrado_cargo['ESTADO_NUM'] == 0])
    total_cumplieron = len(df_filtrado_cargo[df_filtrado_cargo['ESTADO_NUM'] == 1])
    
    # Niveles
    df_n1 = df_filtrado_cargo[df_filtrado_cargo['NIVEL'].astype(str).str.contains("1", na=False)]
    df_n2 = df_filtrado_cargo[df_filtrado_cargo['NIVEL'].astype(str).str.contains("2", na=False)]
    total_n1 = len(df_n1)
    total_n2 = len(df_n2)

    # --- BOTONERA SUPERIOR (ESTADO) ---
    st.markdown("### 📊 Estado del Grupo:")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    # Estilos
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

    # --- APLICACIÓN DE FILTRO DE ESTADO ---
    df_estado_view = df_filtrado_cargo.copy()
    subtitulo_estado = "Listado Completo"

    if st.session_state.filtro_activo == 'Faltan':
        df_estado_view = df_estado_view[df_estado_view['ESTADO_NUM'] == 0]
        subtitulo_estado = "⚠️ Pendientes"
    elif st.session_state.filtro_activo == 'Cumplieron':
        df_estado_view = df_estado_view[df_estado_view['ESTADO_NUM'] == 1]
        subtitulo_estado = "✅ Cumplidoras"
    elif st.session_state.filtro_activo == 'Nivel 1':
        df_estado_view = df_n1
        subtitulo_estado = "🔹 Nivel 1"
    elif st.session_state.filtro_activo == 'Nivel 2':
        df_estado_view = df_n2
        subtitulo_estado = "🔸 Nivel 2"

    # =========================================================
    # NUEVA SECCIÓN: BOTONES DE COLABORADORES
    # =========================================================
    if 'COLABORADOR' in df_filtrado_cargo.columns:
        # Obtenemos nombres únicos del rol seleccionado
        lista_nombres = sorted(df_filtrado_cargo['COLABORADOR'].unique())
        
        st.markdown(f"### 👤 Colaboradores en este Rol ({len(lista_nombres)}):")
        
        # Botón para resetear la selección de persona
        tipo_btn_todos_colab = "primary" if st.session_state.colaborador_activo == 'Todos' else "secondary"
        if st.button("👥 Ver Todos los Colaboradores", type=tipo_btn_todos_colab, use_container_width=True):
             st.session_state.colaborador_activo = 'Todos'
        
        # Generamos cuadrícula de botones (4 por fila)
        cols_nombres = st.columns(4)
        for i, nombre in enumerate(lista_nombres):
            # Color del botón si está seleccionado
            tipo_btn = "primary" if st.session_state.colaborador_activo == nombre else "secondary"
            
            # Usamos el operador módulo (%) para distribuir en columnas
            if cols_nombres[i % 4].button(nombre, key=f"btn_col_{i}", type=tipo_btn, use_container_width=True):
                st.session_state.colaborador_activo = nombre

        st.divider()

    # --- APLICACIÓN FILTRO FINAL (COLABORADOR) ---
    df_final_view = df_estado_view.copy()
    
    # Si hay un colaborador específico seleccionado, filtramos
    if st.session_state.colaborador_activo != 'Todos':
        df_final_view = df_final_view[df_final_view['COLABORADOR'] == st.session_state.colaborador_activo]
        st.info(f"Mostrando cursos de: **{st.session_state.colaborador_activo}** ({subtitulo_estado})")
    else:
        st.caption(f"Mostrando: {subtitulo_estado}")

    # --- TABLA DE RESULTADOS ---
    cols_mostrar = ['COLABORADOR', 'CARGO', 'CURSO', 'NIVEL', 'ESTADO_NUM']
    cols_reales = [c for c in cols_mostrar if c in df_final_view.columns]

    st.dataframe(
        df_final_view[cols_reales],
        use_container_width=True,
        hide_index=True,
        column_config={
            "ESTADO_NUM": st.column_config.CheckboxColumn("Realizado", disabled=True),
            "COLABORADOR": st.column_config.TextColumn("Colaborador", width="medium"),
            "CARGO": st.column_config.TextColumn("Rol / Cargo", width="medium"),
            "CURSO": st.column_config.TextColumn("Capacitación", width="large"),
        }
    )

else:
    st.warning("No se encontraron datos.")
