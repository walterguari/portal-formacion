import streamlit as st
import pandas as pd
import os # --- NUEVO: Importamos 'os' para verificar si existe la imagen

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Portal Formación 2026", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🎓" # --- NUEVO: Icono en la pestaña del navegador
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        min-height: 3em;
        height: auto;
        font-weight: bold;
        border: 1px solid #dce775;
        white-space: pre-wrap;
    }
    section[data-testid="stSidebar"] .stRadio label {
        font-weight: bold;
    }
    .stMetric {
        background-color: #f1f8e9;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #c5e1a5;
        text-align: center;
    }
    /* Ajuste para que el logo se vea centrado y limpio */
    [data-testid="stSidebar"] > div:first-child img {
        margin-bottom: 20px;
        max-height: 150px; /* Altura máxima para que no ocupe toda la barra */
        object-fit: contain;
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

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'
if 'filtro_activo' not in st.session_state: st.session_state.filtro_activo = 'Todos'

# =========================================================
# --- BARRA LATERAL (LOGO + FILTRO) ---
# =========================================================

# --- NUEVO: LÓGICA PARA MOSTRAR EL LOGO ---
# Busca un archivo llamado 'logo.png' o 'logo.jpg' en la carpeta
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
elif os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
# ------------------------------------------

st.sidebar.title("🏢 Filtro por Rol")
df_filtrado_cargo = df.copy()
lista_cargos = []
cargo_seleccionado = "Todos"

if not df.empty and 'CARGO' in df.columns:
    lista_cargos = sorted(df['CARGO'].dropna().unique().tolist())
    opciones_menu = ["Todos"] + lista_cargos
    cargo_seleccionado = st.sidebar.radio("Selecciona un Rol:", opciones_menu)
    
    # Reseteo al cambiar de rol
    if cargo_seleccionado != st.session_state.ultimo_cargo_sel:
        st.session_state.colaborador_activo = 'Todos'
        st.session_state.filtro_activo = 'Todos'
        st.session_state.ultimo_cargo_sel = cargo_seleccionado

    if cargo_seleccionado != "Todos":
        df_filtrado_cargo = df[df['CARGO'] == cargo_seleccionado]
        st.sidebar.success(f"Rol: {cargo_seleccionado}")
    else:
        st.sidebar.info("Mostrando toda la nómina")

st.sidebar.markdown("---")

# --- TÍTULO PRINCIPAL ---
st.title(f"🎓 Control de Formación - {cargo_seleccionado}")

if not df_filtrado_cargo.empty:
    
    # 1. SECCIÓN DE COLABORADORES
    st.markdown("### 👤 Selecciona un Colaborador:")
    
    if 'COLABORADOR' in df_filtrado_cargo.columns:
        lista_nombres = sorted(df_filtrado_cargo['COLABORADOR'].unique())
        
        tipo_btn_todos_colab = "primary" if st.session_state.colaborador_activo == 'Todos' else "secondary"
        if st.button(f"👥 Ver Todo el Equipo ({len(lista_nombres)} personas)", type=tipo_btn_todos_colab, use_container_width=True):
             st.session_state.colaborador_activo = 'Todos'
             st.session_state.filtro_activo = 'Todos'
        
        cols_nombres = st.columns(4)
        for i, nombre in enumerate(lista_nombres):
            tipo_btn = "primary" if st.session_state.colaborador_activo == nombre else "secondary"
            if cols_nombres[i % 4].button(nombre, key=f"btn_col_{i}", type=tipo_btn, use_container_width=True):
                st.session_state.colaborador_activo = nombre
                st.session_state.filtro_activo = 'Todos'

    st.divider()

    # 2. CÁLCULOS DE ESTADO (Persona o Grupo)
    df_persona_view = df_filtrado_cargo.copy()
    nombre_visual = "del Grupo Completo"
    
    if st.session_state.colaborador_activo != 'Todos':
        df_persona_view = df_persona_view[df_persona_view['COLABORADOR'] == st.session_state.colaborador_activo]
        nombre_visual = f"de {st.session_state.colaborador_activo}"

    total_registros = len(df_persona_view)
    total_pendientes = len(df_persona_view[df_persona_view['ESTADO_NUM'] == 0])
    total_cumplieron = len(df_persona_view[df_persona_view['ESTADO_NUM'] == 1])
    
    # Cálculo de Porcentaje
    porcentaje_cumplimiento = (total_cumplieron / total_registros * 100) if total_registros > 0 else 0

    # Lógica de Niveles (Pendientes vs Totales)
    df_n1 = df_persona_view[df_persona_view['NIVEL'].astype(str).str.contains("1", na=False)]
    df_n2 = df_persona_view[df_persona_view['NIVEL'].astype(str).str.contains("2", na=False)]
    
    # Cuántos faltan por nivel
    falta_n1 = len(df_n1[df_n1['ESTADO_NUM'] == 0])
    falta_n2 = len(df_n2[df_n2['ESTADO_NUM'] == 0])

    # 3. INDICADOR DE PORCENTAJE
    c_kpi1, c_kpi2 = st.columns([1, 3])
    with c_kpi1:
        st.metric(label="🏆 Cumplimiento Global", value=f"{porcentaje_cumplimiento:.1f}%")
    with c_kpi2:
        st.write("Progreso de Formación:")
        st.progress(int(porcentaje_cumplimiento))

    # 4. BOTONERA DE ESTADO DETALLADA
    st.markdown(f"### 📊 Detalle {nombre_visual}:")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    
    b_all = "primary" if st.session_state.filtro_activo == 'Todos' else "secondary"
    b_fal = "primary" if st.session_state.filtro_activo == 'Faltan' else "secondary"
    b_ok = "primary" if st.session_state.filtro_activo == 'Cumplieron' else "secondary"
    b_n1 = "primary" if st.session_state.filtro_activo == 'Nivel 1' else "secondary"
    b_n2 = "primary" if st.session_state.filtro_activo == 'Nivel 2' else "secondary"

    # Etiquetas Dinámicas
    txt_n1 = f"🔹 Nivel 1 (Faltan: {falta_n1})"
    txt_n2 = f"🔸 Nivel 2 (Faltan: {falta_n2})"

    if c1.button(f"📋 Total Cursos ({total_registros})", type=b_all, use_container_width=True):
        st.session_state.filtro_activo = 'Todos'
    if c2.button(f"⏳ Faltan ({total_pendientes})", type=b_fal, use_container_width=True):
        st.session_state.filtro_activo = 'Faltan'
    if c3.button(f"✅ Cumplieron ({total_cumplieron})", type=b_ok, use_container_width=True):
        st.session_state.filtro_activo = 'Cumplieron'
    if c4.button(txt_n1, type=b_n1, use_container_width=True):
        st.session_state.filtro_activo = 'Nivel 1'
    if c5.button(txt_n2, type=b_n2, use_container_width=True):
        st.session_state.filtro_activo = 'Nivel 2'

    # 5. TABLA FINAL
    st.markdown("<br>", unsafe_allow_html=True)
    
    df_final_view = df_persona_view.copy()
    subtitulo = "Todos los cursos asignados"

    if st.session_state.filtro_activo == 'Faltan':
        df_final_view = df_final_view[df_final_view['ESTADO_NUM'] == 0]
        subtitulo = "Solo cursos pendientes"
    elif st.session_state.filtro_activo == 'Cumplieron':
        df_final_view = df_final_view[df_final_view['ESTADO_NUM'] == 1]
        subtitulo = "Solo cursos realizados"
    elif st.session_state.filtro_activo == 'Nivel 1':
        df_final_view = df_n1
        subtitulo = f"Cursos Nivel 1 (Pendientes: {falta_n1})"
    elif st.session_state.filtro_activo == 'Nivel 2':
        df_final_view = df_n2
        subtitulo = f"Cursos Nivel 2 (Pendientes: {falta_n2})"

    st.caption(f"Mostrando: {subtitulo}")

    # Columnas a mostrar
    cols_mostrar = ['CARGO', 'CURSO', 'NIVEL', 'ESTADO_NUM']
    if st.session_state.colaborador_activo == 'Todos':
        cols_mostrar.insert(0, 'COLABORADOR')

    cols_reales = [c for c in cols_mostrar if c in df_final_view.columns]

    st.dataframe(
        df_final_view[cols_reales],
        use_container_width=True,
        hide_index=True,
        column_config={
            "ESTADO_NUM": st.column_config.CheckboxColumn("Realizado", disabled=True),
            "COLABORADOR": st.column_config.TextColumn("Colaborador", width="medium"),
            "CARGO": st.column_config.TextColumn("Rol", width="medium"),
            "CURSO": st.column_config.TextColumn("Capacitación", width="large"),
        }
    )

else:
    st.warning("No se encontraron datos.")
