import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 8px; font-weight: bold; border: 1px solid #dce775;}
    [data-testid="stSidebar"] img {display: block; margin: 0 auto 20px auto;}
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
# REVISAR: ¿Es este el ID correcto?
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=0) # ttl=0 para que NO guarde memoria vieja
def load_data():
    try:
        # Leemos el archivo
        df = pd.read_csv(URL)
        
        # 1. Limpieza de Cabeceras (Mayúsculas y sin espacios)
        df.columns = df.columns.str.strip().str.upper()
        
        # 2. Renombrado flexible
        # Intenta encontrar columnas aunque se llamen parecido
        rename_map = {}
        for col in df.columns:
            if "SECTOR" in col or "AREA" in col or "GERENCIA" in col: rename_map[col] = 'SECTOR'
            elif "ROL" in col or "CARGO" in col: rename_map[col] = 'CARGO'
            elif "NOMBRE" in col or "COLABORADOR" in col: rename_map[col] = 'COLABORADOR'
            elif "FORMACION" in col or "CURSO" in col: rename_map[col] = 'CURSO'
            elif "NIVEL" in col: rename_map[col] = 'NIVEL'
            elif "CAPACITA" in col or "ESTADO" in col: rename_map[col] = 'ESTADO_NUM'
            
        df = df.rename(columns=rename_map)
        
        # 3. Convertir columna de estado a números
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
            
        return df
    except Exception as e:
        return None

df = load_data()

# --- BARRA LATERAL ---
if os.path.exists("logo.png"): st.sidebar.image("logo.png", use_container_width=True)

# ---------------------------------------------------------------------
# 🚨 ZONA DE DIAGNÓSTICO (ESTO TE DIRÁ QUÉ PASA)
# ---------------------------------------------------------------------
if df is None:
    st.error("❌ Error fatal: No se pudo leer el Excel. Verifica los permisos del link.")
    st.stop()

# Si NO encuentra la columna SECTOR, muestra la ayuda en rojo
if 'SECTOR' not in df.columns:
    st.sidebar.error("⚠️ NO VEO LA COLUMNA 'SECTOR'")
    st.sidebar.warning("Estas son las columnas que estoy leyendo de tu Excel:")
    st.sidebar.code(list(df.columns))
    st.sidebar.info("👉 Solución: Verifica que en la FILA 1 de tu Excel exista una columna llamada 'Sector' o 'Area'. Si la agregaste recién, presiona 'C' en tu teclado para borrar caché.")
# ---------------------------------------------------------------------

# Inicializar variables
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = "Todos"

# --- BOTONES DE SECTOR ---
if 'SECTOR' in df.columns:
    st.sidebar.markdown("### 📊 Sectores")
    
    # Botón Ver Todos
    tipo_t = "primary" if st.session_state.sector_activo == "Todos" else "secondary"
    if st.sidebar.button("🏢 VER TODOS", type=tipo_t, use_container_width=True):
        st.session_state.sector_activo = "Todos"
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    sectores = sorted(df['SECTOR'].dropna().astype(str).unique())
    
    for i, sec in enumerate(sectores):
        # Calcular %
        d_s = df[df['SECTOR'] == sec]
        avance = (len(d_s[d_s['ESTADO_NUM']==1]) / len(d_s) * 100) if len(d_s) > 0 else 0
        color = "#ef5350" if avance < 50 else "#ffa726" if avance < 80 else "#66bb6a"
        
        # Diseño Botón + Indicador
        c1, c2 = st.sidebar.columns([1, 4])
        with c1:
            st.markdown(f"<div style='background-color:{color}; width:15px; height:15px; border-radius:50%; margin-top:10px;'></div>", unsafe_allow_html=True)
        with c2:
            tipo = "primary" if st.session_state.sector_activo == sec else "secondary"
            if st.button(f"{sec} ({avance:.0f}%)", key=f"btn_{i}", type=tipo, use_container_width=True):
                st.session_state.sector_activo = sec
                st.session_state.ultimo_cargo_sel = "Todos"
                st.session_state.colaborador_activo = "Todos"
                st.rerun()
                
    st.sidebar.markdown("---")
    
    # Filtro Cargo
    df_rol = df[df['SECTOR'] == st.session_state.sector_activo] if st.session_state.sector_activo != "Todos" else df
    roles = ["Todos"] + sorted(df_rol['CARGO'].dropna().astype(str).unique())
    
    idx = roles.index(st.session_state.ultimo_cargo_sel) if st.session_state.ultimo_cargo_sel in roles else 0
    sel_rol = st.sidebar.radio("Puesto:", roles, index=idx)
    
    if sel_rol != st.session_state.ultimo_cargo_sel:
        st.session_state.ultimo_cargo_sel = sel_rol
        st.session_state.colaborador_activo = "Todos"
        st.rerun()
        
    df_main = df_rol[df_rol['CARGO'] == sel_rol] if sel_rol != "Todos" else df_rol

else:
    df_main = df.copy()

# --- CUERPO PRINCIPAL ---
st.title(f"🎓 {st.session_state.sector_activo}")

if not df_main.empty:
    # 1. Colaboradores
    st.write("### 👤 Equipo")
    nombres = sorted(df_main['COLABORADOR'].dropna().astype(str).unique())
    
    if st.button(f"👥 Ver Todo el Equipo ({len(nombres)})", use_container_width=True, type="primary" if st.session_state.colaborador_activo == "Todos" else "secondary"):
        st.session_state.colaborador_activo = "Todos"
        st.rerun()
        
    cols = st.columns(4)
    for i, nom in enumerate(nombres):
        tipo = "primary" if st.session_state.colaborador_activo == nom else "secondary"
        if cols[i%4].button(nom, key=f"c_{i}", type=tipo, use_container_width=True):
            st.session_state.colaborador_activo = nom
            st.rerun()
    
    st.divider()
    
    # 2. Datos
    d_v = df_main[df_main['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != "Todos" else df_main
    
    ok = len(d_v[d_v['ESTADO_NUM'] == 1])
    total = len(d_v)
    porc = (ok/total*100) if total > 0 else 0
    
    # Velocímetro
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = porc, title = {'text': "Avance"},
        gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "green" if porc>=80 else "orange" if porc>=50 else "red"}}
    ))
    fig.update_layout(height=200, margin=dict(t=30,b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabla
    st.dataframe(d_v, use_container_width=True, hide_index=True)
