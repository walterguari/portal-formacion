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

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        min-height: 3em;
        font-weight: bold;
        border: 1px solid #dce775;
    }
    .stMetric {
        background-color: #f1f8e9;
        padding: 5px;
        border-radius: 5px;
        text-align: center;
        border: 1px solid #c5e1a5;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if 'acceso_concedido' not in st.session_state: st.session_state.acceso_concedido = False

def mostrar_login():
    st.title("🔒 Acceso Restringido")
    col1, col2 = st.columns([1,2])
    with col1:
        clave = st.text_input("Clave de Acceso", type="password")
        if st.button("Entrar"):
            if clave == "CENOA2026": 
                st.session_state.acceso_concedido = True
                st.rerun()
            else:
                st.error("Clave incorrecta")

if not st.session_state.acceso_concedido:
    mostrar_login()
    st.stop()

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# ttl=0 OBLIGA a descargar los datos nuevos cada vez
@st.cache_data(ttl=0)
def load_data():
    try:
        df = pd.read_csv(URL)
        
        # Limpieza de nombres de columnas
        df.columns = df.columns.str.strip().str.upper()
        
        # --- DIAGNÓSTICO DE COLUMNAS ---
        # Buscamos la columna SECTOR aunque tenga otro nombre parecido
        rename_dict = {}
        for col in df.columns:
            if "SECTOR" in col: rename_dict[col] = 'SECTOR'
            elif "ROL" in col: rename_dict[col] = 'CARGO'
            elif "NOMBRE" in col or "COLABORADOR" in col: rename_dict[col] = 'COLABORADOR'
            elif "FORMACION" in col: rename_dict[col] = 'CURSO'
            elif "NIVEL" in col: rename_dict[col] = 'NIVEL'
            elif "CAPACITA" in col: rename_dict[col] = 'ESTADO_NUM'
            
        df = df.rename(columns=rename_dict)
        
        # Limpieza de valores
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
            
        return df
    except Exception as e:
        return None

df = load_data()

# --- BARRA LATERAL ---
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

# ---------------------------------------------------------
# ZONA DE DIAGNÓSTICO (PARA VER POR QUÉ NO SALE)
# ---------------------------------------------------------
if df is None:
    st.error("Error cargando el Excel. Revisa los permisos.")
    st.stop()

if 'SECTOR' not in df.columns:
    st.sidebar.error("⚠️ ERROR: No encuentro la columna 'Sector'")
    st.sidebar.warning("Las columnas que veo en tu Excel son:")
    st.sidebar.code(list(df.columns))
    st.sidebar.info("Solución: Asegúrate que en el Excel la columna A tenga de título 'Sector'.")
# ---------------------------------------------------------

# INICIALIZAR ESTADO
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = "Todos"
if 'filtro_activo' not in st.session_state: st.session_state.filtro_activo = 'Todos'

# BOTONES DE SECTORES (Solo si existe la columna)
if 'SECTOR' in df.columns:
    st.sidebar.markdown("### 📊 Sectores")
    
    # Botón Ver Todos
    if st.sidebar.button("🏢 VER TODOS", use_container_width=True, type="primary" if st.session_state.sector_activo == "Todos" else "secondary"):
        st.session_state.sector_activo = "Todos"
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    sectores = sorted(df['SECTOR'].dropna().unique())
    
    # Grid de botones
    for i, sec in enumerate(sectores):
        # Datos del sector
        df_s = df[df['SECTOR'] == sec]
        avance = (len(df_s[df_s['ESTADO_NUM'] == 1]) / len(df_s) * 100) if len(df_s) > 0 else 0
        color = "red" if avance < 50 else "orange" if avance < 80 else "green"
        
        # Diseño de fila: Indicador + Botón
        c1, c2 = st.sidebar.columns([1, 3])
        with c1:
            st.markdown(f"<h3 style='color:{color}; margin:0; text-align:center;'>●</h3>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:10px; text-align:center;'>{avance:.0f}%</div>", unsafe_allow_html=True)
        with c2:
            tipo = "primary" if st.session_state.sector_activo == sec else "secondary"
            if st.button(f"{sec}", key=f"btn_sec_{i}", type=tipo, use_container_width=True):
                st.session_state.sector_activo = sec
                st.session_state.ultimo_cargo_sel = "Todos"
                st.session_state.colaborador_activo = "Todos"
                st.rerun()
                
    st.sidebar.markdown("---")

    # FILTRO ROL
    if st.session_state.sector_activo != "Todos":
        df_rol = df[df['SECTOR'] == st.session_state.sector_activo]
    else:
        df_rol = df.copy()
        
    st.sidebar.subheader("Puestos:")
    lista_roles = sorted(df_rol['CARGO'].dropna().unique())
    op_roles = ["Todos"] + lista_roles
    
    idx = 0
    if st.session_state.ultimo_cargo_sel in op_roles:
        idx = op_roles.index(st.session_state.ultimo_cargo_sel)
        
    rol_sel = st.sidebar.radio("Selecciona Rol:", op_roles, index=idx)
    
    if rol_sel != st.session_state.ultimo_cargo_sel:
        st.session_state.ultimo_cargo_sel = rol_sel
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    # FILTRO FINAL DATOS
    if rol_sel != "Todos":
        df_main = df_rol[df_rol['CARGO'] == rol_sel]
    else:
        df_main = df_rol

else:
    df_main = df.copy()

# --- CUERPO PRINCIPAL ---
titulo = st.session_state.sector_activo
if st.session_state.ultimo_cargo_sel != "Todos": titulo += f" > {st.session_state.ultimo_cargo_sel}"
st.title(f"🎓 Formación: {titulo}")

if not df_main.empty:
    # 1. COLABORADORES
    st.markdown("### 👤 Colaboradores:")
    nombres = sorted(df_main['COLABORADOR'].unique())
    
    if st.button(f"👥 Ver Todo el Equipo ({len(nombres)})", type="primary" if st.session_state.colaborador_activo == "Todos" else "secondary", use_container_width=True):
        st.session_state.colaborador_activo = "Todos"
        st.session_state.filtro_activo = "Todos"
        st.rerun()
        
    cols = st.columns(4)
    for i, nom in enumerate(nombres):
        tipo = "primary" if st.session_state.colaborador_activo == nom else "secondary"
        if cols[i%4].button(nom, key=f"c_{i}", type=tipo, use_container_width=True):
            st.session_state.colaborador_activo = nom
            st.session_state.filtro_activo = "Todos"
            st.rerun()
            
    st.divider()
    
    # 2. DATOS
    df_v = df_main.copy()
    if st.session_state.colaborador_activo != "Todos":
        df_v = df_v[df_v['COLABORADOR'] == st.session_state.colaborador_activo]
        
    total = len(df_v)
    ok = len(df_v[df_v['ESTADO_NUM'] == 1])
    falta = total - ok
    porc = (ok/total*100) if total > 0 else 0
    
    # VELOCIMETRO
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = porc,
        title = {'text': "Avance"},
        gauge = {'axis': {'range': [None, 100]}, 
                 'bar': {'color': "green" if porc>=80 else "orange" if porc>=50 else "red"}}
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    # BOTONES ESTADO
    c1, c2, c3 = st.columns(3)
    if c1.button(f"📋 Total ({total})"): st.session_state.filtro_activo = "Todos"
    if c2.button(f"⏳ Faltan ({falta})"): st.session_state.filtro_activo = "Faltan"
    if c3.button(f"✅ Listos ({ok})"): st.session_state.filtro_activo = "Cumplieron"
    
    # TABLA
    df_t = df_v.copy()
    if st.session_state.filtro_activo == "Faltan": df_t = df_t[df_t['ESTADO_NUM']==0]
    elif st.session_state.filtro_activo == "Cumplieron": df_t = df_t[df_t['ESTADO_NUM']==1]
    
    st.dataframe(df_t[['SECTOR', 'CARGO', 'COLABORADOR', 'CURSO', 'NIVEL', 'ESTADO_NUM']], use_container_width=True, hide_index=True)
