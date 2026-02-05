import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Portal Formación 2026", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🎓"
)

# =========================================================
# 🔒 SISTEMA DE LOGIN
# =========================================================
if 'acceso_concedido' not in st.session_state: 
    st.session_state.acceso_concedido = False

def mostrar_login():
    st.markdown("""
    <style>
        .block-container {padding-top: 5rem; text-align: center;}
        input {text-align: center;}
    </style>
    """, unsafe_allow_html=True)
    st.title("🔒 Portal Privado")
    st.write("Por favor, ingresa la clave de acceso.")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        clave = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if clave == "CENOA2026": 
                st.session_state.acceso_concedido = True
                st.rerun()
            else:
                st.error("🚫 Clave incorrecta.")

if not st.session_state.acceso_concedido:
    mostrar_login()
    st.stop()

# =========================================================
# 🚀 APLICACIÓN PRINCIPAL
# =========================================================

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        min-height: 3em;
        font-weight: bold;
        border: 1px solid #dce775;
        white-space: pre-wrap;
    }
    section[data-testid="stSidebar"] .stRadio label {
        font-weight: bold;
    }
    /* Centrar logo */
    [data-testid="stSidebar"] > div:first-child img {
        margin-bottom: 10px;
        max-height: 120px;
        object-fit: contain;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# IMPORTANTE: ttl=0 obliga a descargar los datos SIEMPRE, sin guardar caché viejo
@st.cache_data(ttl=0) 
def load_data():
    try:
        df = pd.read_csv(URL)
        
        # 1. LIMPIEZA AGRESIVA DE COLUMNAS
        # Quitamos espacios al principio y final, y pasamos a mayúsculas
        df.columns = df.columns.str.strip().str.upper()
        
        # 2. RENOMBRADO INTELIGENTE
        # Buscamos variaciones comunes
        rename_dict = {}
        for col in df.columns:
            if "SECTOR" in col or "AREA" in col: rename_dict[col] = 'SECTOR'
            elif "ROL" in col: rename_dict[col] = 'CARGO'
            elif "NOMBRE" in col or "COLABORADOR" in col: rename_dict[col] = 'COLABORADOR'
            elif "FORMACION" in col: rename_dict[col] = 'CURSO'
            elif "NIVEL" in col: rename_dict[col] = 'NIVEL'
            elif "CAPACITA" in col: rename_dict[col] = 'ESTADO_NUM'
            
        df = df.rename(columns=rename_dict)
        
        # 3. LIMPIEZA DE DATOS
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        for col in ['SECTOR', 'CARGO', 'NIVEL', 'COLABORADOR']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()

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

# =========================================================
# --- BARRA LATERAL ---
# =========================================================

# 1. LOGO
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

# --- DEBUGGING (DIAGNÓSTICO) ---
# Si no encuentra SECTOR, muestra qué columnas SÍ encontró para ayudarte
if not df.empty and 'SECTOR' not in df.columns:
    st.sidebar.error("⚠️ NO VEO LA COLUMNA 'SECTOR'")
    st.sidebar.info(f"Columnas encontradas: {list(df.columns)}")
    st.sidebar.warning("Intenta presionar 'C' y luego 'Clear Cache' en tu teclado.")

# 2. BOTONES DE SECTORES (MINI DASHBOARD)
if not df.empty and 'SECTOR' in df.columns:
    st.sidebar.markdown("### 📊 Selecciona Sector")
    
    # Botón Ver Todos
    if st.sidebar.button("🏢 EMPRESA COMPLETA", type="primary" if st.session_state.sector_activo == "Todos" else "secondary", use_container_width=True):
        st.session_state.sector_activo = "Todos"
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    sectores_unicos = sorted(df['SECTOR'].dropna().unique())
    
    # Grid de botones
    for i, sector in enumerate(sectores_unicos):
        df_sec = df[df['SECTOR'] == sector]
        total = len(df_sec)
        ok = len(df_sec[df_sec['ESTADO_NUM'] == 1])
        porc = (ok / total * 100) if total > 0 else 0
        
        # Color semáforo
        color = "#ef5350" if porc < 50 else "#ffa726" if porc < 80 else "#66bb6a"
        
        # Usamos columnas para poner el indicador al lado del nombre o arriba
        # Diseño compacto: Botón con el nombre y porcentaje
        label_btn = f"{sector}\n({porc:.0f}%)"
        
        # Estilo visual del botón
        btn_type = "primary" if st.session_state.sector_activo == sector else "secondary"
        
        # Creamos una fila con dos columnas: 1 pequeña para el gráfico, 1 grande para el botón
        c_graf, c_btn = st.sidebar.columns([1, 3])
        
        with c_graf:
            fig_mini = go.Figure(go.Pie(
                values=[porc, 100-porc], hole=0.7, textinfo='none',
                marker=dict(colors=[color, '#eeeeee']), hoverinfo='skip'
            ))
            fig_mini.update_layout(showlegend=False, margin=dict(l=0,r=0,t=0,b=0), height=35, width=35)
            st.plotly_chart(fig_mini, use_container_width=True, config={'staticPlot': True})
            
        with c_btn:
            if st.button(f"{sector}", key=f"btn_sec_{i}", type=btn_type, use_container_width=True):
                st.session_state.sector_activo = sector
                st.session_state.ultimo_cargo_sel = "Todos"
                st.session_state.colaborador_activo = "Todos"
                st.rerun()

    st.sidebar.markdown("---")

    # 3. FILTRO DE ROL
    st.sidebar.subheader(f"Roles en: {st.session_state.sector_activo}")
    
    if st.session_state.sector_activo != "Todos":
        df_filtrado_sector = df[df['SECTOR'] == st.session_state.sector_activo]
    else:
        df_filtrado_sector = df.copy()

    lista_cargos = sorted(df_filtrado_sector['CARGO'].dropna().unique().tolist())
    opciones_rol = ["Todos"] + lista_cargos
    
    idx = 0
    if st.session_state.ultimo_cargo_sel in opciones_rol:
        idx = opciones_rol.index(st.session_state.ultimo_cargo_sel)
        
    cargo_sel = st.sidebar.radio("Puesto:", opciones_rol, index=idx)
    
    if cargo_sel != st.session_state.ultimo_cargo_sel:
        st.session_state.ultimo_cargo_sel = cargo_sel
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    if cargo_sel != "Todos":
        df_main = df_filtrado_sector[df_filtrado_sector['CARGO'] == cargo_sel]
    else:
        df_main = df_filtrado_sector

    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Salir"):
        st.session_state.acceso_concedido = False
        st.rerun()

else:
    df_main = df.copy()

# =========================================================
# --- CUERPO PRINCIPAL ---
# =========================================================

titulo = f"{st.session_state.sector_activo}"
if st.session_state.ultimo_cargo_sel != "Todos": titulo += f" > {st.session_state.ultimo_cargo_sel}"

st.title(f"🎓 Formación: {titulo}")

if not df_main.empty:
    
    # COLABORADORES
    st.markdown("### 👤 Selecciona Colaborador:")
    if 'COLABORADOR' in df_main.columns:
        lista_nombres = sorted(df_main['COLABORADOR'].unique())
        
        tipo_btn_todos = "primary" if st.session_state.colaborador_activo == 'Todos' else "secondary"
        
        if st.button(f"👥 Ver Todo el Equipo ({len(lista_nombres)})", type=tipo_btn_todos, use_container_width=True):
             st.session_state.colaborador_activo = 'Todos'
             st.session_state.filtro_activo = 'Todos'
        
        cols_nombres = st.columns(4)
        for i, nombre in enumerate(lista_nombres):
            tipo_btn = "primary" if st.session_state.colaborador_activo == nombre else "secondary"
            if cols_nombres[i % 4].button(nombre, key=f"btn_col_{i}", type=tipo_btn, use_container_width=True):
                st.session_state.colaborador_activo = nombre
                st.session_state.filtro_activo = 'Todos'
    
    st.divider()

    # CÁLCULOS
    df_view = df_main.copy()
    if st.session_state.colaborador_activo != 'Todos':
        df_view = df_view[df_view['COLABORADOR'] == st.session_state.colaborador_activo]

    total_reg = len(df_view)
    pendientes = len(df_view[df_view['ESTADO_NUM'] == 0])
    cumplidos = len(df_view[df_view['ESTADO_NUM'] == 1])
    porcentaje = (cumplidos / total_reg * 100) if total_reg > 0 else 0
    
    df_n1 = df_view[df_view['NIVEL'].str.contains("1", na=False)]
    df_n2 = df_view[df_view['NIVEL'].str.contains("2", na=False)]
    falta_n1 = len(df_n1[df_n1['ESTADO_NUM'] == 0])
    falta_n2 = len(df_n2[df_n2['ESTADO_NUM'] == 0])

    # VELOCÍMETRO
    color_g = "red" if porcentaje < 50 else "orange" if porcentaje < 80 else "green"
    msg = "⚠️ Crítico" if porcentaje < 50 else "🔨 En Proceso" if porcentaje < 80 else "🏆 Excelente"
    
    c_graph, c_txt = st.columns([1, 2])
    with c_graph:
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = porcentaje,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Avance Actual"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': color_g},
                'steps': [{'range': [0, 100], 'color': "#f5f5f5"}],
                'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': porcentaje}
            }
        ))
        fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with c_txt:
        st.markdown(f"### {msg}")
        st.info(f"Completado: **{cumplidos}/{total_reg}** cursos.")
        if pendientes == 0 and total_reg > 0: st.success("✅ ¡Todo al día!")

    # FILTROS RÁPIDOS
    c1, c2, c3, c4, c5 = st.columns(5)
    b_all = "primary" if st.session_state.filtro_activo == 'Todos' else "secondary"
    b_fal = "primary" if st.session_state.filtro_activo == 'Faltan' else "secondary"
    b_ok = "primary" if st.session_state.filtro_activo == 'Cumplieron' else "secondary"
    b_n1 = "primary" if st.session_state.filtro_activo == 'Nivel 1' else "secondary"
    b_n2 = "primary" if st.session_state.filtro_activo == 'Nivel 2' else "secondary"

    if c1.button(f"📋 Total ({total_reg})", type=b_all, use_container_width=True): st.session_state.filtro_activo = 'Todos'
    if c2.button(f"⏳ Faltan ({pendientes})", type=b_fal, use_container_width=True): st.session_state.filtro_activo = 'Faltan'
    if c3.button(f"✅ Listos ({cumplidos})", type=b_ok, use_container_width=True): st.session_state.filtro_activo = 'Cumplieron'
    if c4.button(f"🔹 N1 (Falta {falta_n1})", type=b_n1, use_container_width=True): st.session_state.filtro_activo = 'Nivel 1'
    if c5.button(f"🔸 N2 (Falta {falta_n2})", type=b_n2, use_container_width=True): st.session_state.filtro_activo = 'Nivel 2'

    # TABLA
    st.markdown("<br>", unsafe_allow_html=True)
    df_table = df_view.copy()
    if st.session_state.filtro_activo == 'Faltan': df_table = df_table[df_table['ESTADO_NUM'] == 0]
    elif st.session_state.filtro_activo == 'Cumplieron': df_table = df_table[df_table['ESTADO_NUM'] == 1]
    elif st.session_state.filtro_activo == 'Nivel 1': df_table = df_n1
    elif st.session_state.filtro_activo == 'Nivel 2': df_table = df_n2

    cols = ['SECTOR', 'CARGO', 'CURSO', 'NIVEL', 'ESTADO_NUM']
    if st.session_state.colaborador_activo == 'Todos': cols.insert(0, 'COLABORADOR')
    cols_reales = [c for c in cols if c in df_table.columns]
    
    st.dataframe(
        df_table[cols_reales], use_container_width=True, hide_index=True,
        column_config={"ESTADO_NUM": st.column_config.CheckboxColumn("OK", disabled=True)}
    )
else:
    st.warning("No hay datos.")
