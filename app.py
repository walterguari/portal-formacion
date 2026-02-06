import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 8px; font-weight: bold; border: 1px solid #dce775; margin-bottom: 5px;}
    [data-testid="stSidebar"] img {display: block; margin: 0 auto 20px auto;}
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if 'acceso_concedido' not in st.session_state: st.session_state.acceso_concedido = False

def mostrar_login():
    st.markdown("<h2 style='text-align: center;'>🔒 Portal Privado</h2>", unsafe_allow_html=True)
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

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=0)
def load_data():
    try:
        df = pd.read_csv(URL)
        
        # 1. Estandarizar cabeceras
        df.columns = df.columns.str.strip().str.upper()
        
        # 2. Mapa de renombrado
        col_map = {}
        for col in df.columns:
            if "SECTORES" in col: col_map[col] = 'SECTOR'
            elif "SECTOR" in col: col_map[col] = 'SECTOR'
            elif "ROL" in col: col_map[col] = 'CARGO'
            elif "NOMBRE" in col or "COLABORADOR" in col: col_map[col] = 'COLABORADOR'
            elif "FORMACION" in col: col_map[col] = 'CURSO'
            elif "NIVEL" in col: col_map[col] = 'NIVEL'
            elif "CAPACITA" in col: col_map[col] = 'ESTADO_NUM'

        df = df.rename(columns=col_map)
        
        # 3. ¡SOLUCIÓN AL ERROR! Eliminar columnas duplicadas
        # Si por error hay dos columnas "SECTOR", se queda solo con la primera
        df = df.loc[:, ~df.columns.duplicated()]

        # 4. Limpieza de datos
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        # Convertir textos a mayúsculas
        for c in ['SECTOR', 'CARGO', 'COLABORADOR', 'NIVEL']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.upper()

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- VARIABLES ---
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'

# --- BARRA LATERAL ---
if os.path.exists("logo.png"): st.sidebar.image("logo.png", use_container_width=True)

# SECTORES
if not df.empty and 'SECTOR' in df.columns:
    st.sidebar.title("🏢 Sectores")
    if st.sidebar.button("VER TODO", type=("primary" if st.session_state.sector_activo == "Todos" else "secondary")):
        st.session_state.sector_activo = "Todos"
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    for sec in sorted(df['SECTOR'].unique()):
        # Indicador visual
        df_s = df[df['SECTOR'] == sec]
        avance = (len(df_s[df_s['ESTADO_NUM']==1]) / len(df_s) * 100) if len(df_s) > 0 else 0
        color = "#ef5350" if avance < 50 else "#ffa726" if avance < 80 else "#66bb6a"
        
        c1, c2 = st.sidebar.columns([1, 4])
        with c1: st.markdown(f"<div style='margin-top:10px; width:15px; height:15px; background-color:{color}; border-radius:50%;'></div>", unsafe_allow_html=True)
        with c2:
            if st.button(f"{sec} ({avance:.0f}%)", key=sec, type=("primary" if st.session_state.sector_activo == sec else "secondary")):
                st.session_state.sector_activo = sec
                st.session_state.ultimo_cargo_sel = "Todos"
                st.session_state.colaborador_activo = "Todos"
                st.rerun()
    st.sidebar.markdown("---")

# FILTRO ROL
st.sidebar.title("👮 Puestos")
df_roles = df[df['SECTOR'] == st.session_state.sector_activo] if st.session_state.sector_activo != "Todos" else df
roles = ["Todos"] + sorted(df_roles['CARGO'].unique().tolist()) if 'CARGO' in df_roles.columns else ["Todos"]

idx = roles.index(st.session_state.ultimo_cargo_sel) if st.session_state.ultimo_cargo_sel in roles else 0
sel_rol = st.sidebar.radio("Selecciona:", roles, index=idx)

if sel_rol != st.session_state.ultimo_cargo_sel:
    st.session_state.ultimo_cargo_sel = sel_rol
    st.session_state.colaborador_activo = 'Todos'
    st.rerun()

if st.sidebar.button("🔒 Salir"):
    st.session_state.acceso_concedido = False
    st.rerun()

# --- PRINCIPAL ---
titulo = st.session_state.sector_activo
if sel_rol != "Todos": titulo += f" > {sel_rol}"
st.title(f"🎓 Formación: {titulo}")

df_main = df_roles[df_roles['CARGO'] == sel_rol] if sel_rol != "Todos" else df_roles

if not df_main.empty:
    # PERSONAS
    st.markdown("### 👤 Equipo")
    nombres = sorted(df_main['COLABORADOR'].unique())
    if st.button(f"👥 Ver Todo ({len(nombres)})", type=("primary" if st.session_state.colaborador_activo == 'Todos' else "secondary")):
         st.session_state.colaborador_activo = 'Todos'
         st.rerun()
    
    cols = st.columns(4)
    for i, nom in enumerate(nombres):
        if cols[i%4].button(nom, key=f"btn_{i}", type=("primary" if st.session_state.colaborador_activo == nom else "secondary")):
            st.session_state.colaborador_activo = nom
            st.rerun()
    
    st.divider()
    
    # DATOS
    df_view = df_main[df_main['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_main
    total = len(df_view)
    ok = len(df_view[df_view['ESTADO_NUM']==1])
    porc = (ok/total*100) if total > 0 else 0
    
    # GRÁFICO
    c1, c2 = st.columns([1, 2])
    with c1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=porc, title={'text':"Avance"}, gauge={'axis':{'range':[None,100]}, 'bar':{'color': ("green" if porc>=80 else "orange" if porc>=50 else "red")}}))
        fig.update_layout(height=250, margin=dict(t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.info(f"Completado: **{ok}/{total}**")
        st.dataframe(df_view[['SECTOR','CARGO','CURSO','ESTADO_NUM']], use_container_width=True, hide_index=True)
else:
    st.warning("No hay datos.")
