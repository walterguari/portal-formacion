import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        min-height: 3em;
        font-weight: bold;
        border: 1px solid #dce775;
        margin-bottom: 5px;
    }
    [data-testid="stSidebar"] img {
        margin: 0 auto;
        display: block;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 🔒 SISTEMA DE LOGIN
# =========================================================
if 'acceso_concedido' not in st.session_state: st.session_state.acceso_concedido = False

def mostrar_login():
    st.markdown("<h2 style='text-align: center;'>🔒 Portal Privado</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        clave = st.text_input("Contraseña", type="password")
        if st.button("Ingresar al Sistema", use_container_width=True, type="primary"):
            if clave == "CENOA2026": 
                st.session_state.acceso_concedido = True
                st.rerun()
            else:
                st.error("🚫 Clave incorrecta.")

if not st.session_state.acceso_concedido:
    mostrar_login()
    st.stop()

# =========================================================
# 🚀 APP PRINCIPAL
# =========================================================

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=0)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip().str.upper() 
        
        # MAPEO DE COLUMNAS (Detecta "Sectores" o "Sector")
        col_map = {}
        for col in df.columns:
            if "SECTORES" in col: col_map[col] = 'SECTOR'
            elif "SECTOR" in col: col_map[col] = 'SECTOR'
            elif "ROL" in col: col_map[col] = 'CARGO'
            elif "NOMBRE" in col or "COLABORADOR" in col: col_map[col] = 'COLABORADOR'
            elif "FORMACION" in col: col_map[col] = 'CURSO'
            elif "TIPO" in col: col_map[col] = 'TIPO'
            elif "NIVEL" in col: col_map[col] = 'NIVEL'
            elif "CAPACITA" in col: col_map[col] = 'ESTADO_NUM'

        df = df.rename(columns=col_map)
        
        # Limpieza
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        for c in ['SECTOR', 'CARGO', 'COLABORADOR', 'NIVEL']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.upper()

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- VARIABLES DE ESTADO ---
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'
if 'filtro_activo' not in st.session_state: st.session_state.filtro_activo = 'Todos'

# --- BARRA LATERAL (LOGO + SECTORES) ---
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

# 1. BOTONES DE SECTORES
if not df.empty and 'SECTOR' in df.columns:
    st.sidebar.title("🏢 Sectores")
    
    # Botón Ver Todos
    tipo_todos = "primary" if st.session_state.sector_activo == "Todos" else "secondary"
    if st.sidebar.button("VER TODO", type=tipo_todos, use_container_width=True):
        st.session_state.sector_activo = "Todos"
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    sectores = sorted(df['SECTOR'].unique())
    
    for sec in sectores:
        # Mini gráfico de avance
        df_s = df[df['SECTOR'] == sec]
        avance = (len(df_s[df_s['ESTADO_NUM']==1]) / len(df_s) * 100) if len(df_s) > 0 else 0
        color = "#ef5350" if avance < 50 else "#ffa726" if avance < 80 else "#66bb6a"
        
        c1, c2 = st.sidebar.columns([1, 4])
        with c1:
            st.markdown(f"<div style='margin-top:10px; width:15px; height:15px; background-color:{color}; border-radius:50%;'></div>", unsafe_allow_html=True)
        with c2:
            tipo = "primary" if st.session_state.sector_activo == sec else "secondary"
            if st.button(f"{sec} ({avance:.0f}%)", key=sec, type=tipo, use_container_width=True):
                st.session_state.sector_activo = sec
                st.session_state.ultimo_cargo_sel = "Todos"
                st.session_state.colaborador_activo = "Todos"
                st.rerun()
    st.sidebar.markdown("---")

# 2. FILTRO POR ROL (Depende del sector seleccionado)
st.sidebar.title("👮 Puestos")

# Filtramos los datos según el sector activo
if st.session_state.sector_activo != "Todos":
    df_roles = df[df['SECTOR'] == st.session_state.sector_activo]
else:
    df_roles = df

if not df_roles.empty and 'CARGO' in df_roles.columns:
    lista_cargos = sorted(df_roles['CARGO'].unique().tolist())
    opciones_menu = ["Todos"] + lista_cargos
    
    # Recuperar índice
    idx = 0
    if st.session_state.ultimo_cargo_sel in opciones_menu:
        idx = opciones_menu.index(st.session_state.ultimo_cargo_sel)
        
    cargo_seleccionado = st.sidebar.radio("Selecciona un Rol:", opciones_menu, index=idx)
    
    if cargo_seleccionado != st.session_state.ultimo_cargo_sel:
        st.session_state.ultimo_cargo_sel = cargo_seleccionado
        st.session_state.colaborador_activo = 'Todos'
        st.rerun()
else:
    cargo_seleccionado = "Todos"

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state.acceso_concedido = False
    st.rerun()

# --- CUERPO PRINCIPAL ---
# Título dinámico
titulo = st.session_state.sector_activo
if cargo_seleccionado != "Todos": titulo += f" > {cargo_seleccionado}"
st.title(f"🎓 Formación: {titulo}")

# Filtrado Final de Datos
df_main = df_roles.copy()
if cargo_seleccionado != "Todos":
    df_main = df_main[df_main['CARGO'] == cargo_seleccionado]

if not df_main.empty:
    
    # SECCIÓN COLABORADORES
    st.markdown("### 👤 Equipo")
    if 'COLABORADOR' in df_main.columns:
        lista_nombres = sorted(df_main['COLABORADOR'].unique())
        
        tipo_btn_todos_colab = "primary" if st.session_state.colaborador_activo == 'Todos' else "secondary"
        if st.button(f"👥 Ver Todo el Equipo ({len(lista_nombres)} personas)", type=tipo_btn_todos_colab, use_container_width=True):
             st.session_state.colaborador_activo = 'Todos'
             st.session_state.filtro_activo = 'Todos'
             st.rerun()
        
        cols_nombres = st.columns(4)
        for i, nombre in enumerate(lista_nombres):
            tipo_btn = "primary" if st.session_state.colaborador_activo == nombre else "secondary"
            if cols_nombres[i % 4].button(nombre, key=f"btn_col_{i}", type=tipo_btn, use_container_width=True):
                st.session_state.colaborador_activo = nombre
                st.session_state.filtro_activo = 'Todos'
                st.rerun()

    st.divider()

    # CÁLCULOS
    df_view = df_main.copy()
    if st.session_state.colaborador_activo != 'Todos':
        df_view = df_view[df_view['COLABORADOR'] == st.session_state.colaborador_activo]

    total_registros = len(df_view)
    total_pendientes = len(df_view[df_view['ESTADO_NUM'] == 0])
    total_cumplieron = len(df_view[df_view['ESTADO_NUM'] == 1])
    porcentaje = (total_cumplieron / total_registros * 100) if total_registros > 0 else 0

    # GRÁFICO VELOCÍMETRO
    color_gauge = "red" if porcentaje < 50 else "orange" if porcentaje < 80 else "green"
    
    col_grafico, col_texto = st.columns([1, 2])
    with col_grafico:
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = porcentaje,
            title = {'text': "Avance"},
            gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': color_gauge}}
        ))
        fig.update_layout(height=250, margin=dict(t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_texto:
        st.info(f"📊 **Resumen:** {total_cumplieron} completados de {total_registros}.")
        if total_pendientes == 0:
            st.success("✅ ¡Objetivo Cumplido!")
        else:
            st.warning(f"Faltan {total_pendientes} cursos.")

    # TABLA FINAL
    st.markdown("### 📋 Detalle")
    
    df_table = df_view.copy()
    
    # Filtros rápidos de tabla
    c1, c2 = st.columns(2)
    if c1.button("⏳ Ver Pendientes"): st.session_state.filtro_activo = 'Faltan'
    if c2.button("✅ Ver Cumplidos"): st.session_state.filtro_activo = 'Cumplieron'
    
    if st.session_state.filtro_activo == 'Faltan':
        df_table = df_table[df_table['ESTADO_NUM'] == 0]
    elif st.session_state.filtro_activo == 'Cumplieron':
        df_table = df_table[df_table['ESTADO_NUM'] == 1]

    cols_ver = ['SECTOR', 'CARGO', 'CURSO', 'NIVEL', 'ESTADO_NUM']
    if st.session_state.colaborador_activo == 'Todos': cols_ver.insert(0, 'COLABORADOR')
    
    cols_final = [c for c in cols_ver if c in df_table.columns]
    
    st.dataframe(
        df_table[cols_final],
        use_container_width=True,
        hide_index=True,
        column_config={
            "ESTADO_NUM": st.column_config.CheckboxColumn("OK", disabled=True),
        }
    )
else:
    st.warning("No se encontraron datos para esta selección.")
