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

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=0)
def load_data():
    try:
        df = pd.read_csv(URL)
        
        # 1. Limpieza de cabeceras
        df.columns = df.columns.str.strip().str.upper()
        
        # 2. RENOMBRADO INTELIGENTE
        # Esto busca "SECTOR" en tu Excel aunque tenga espacios o sea singular/plural
        rename_dict = {}
        for col in df.columns:
            if "SECTOR" in col: rename_dict[col] = 'SECTOR' # Detecta "Sector" o "Sectores"
            elif "AREA" in col: rename_dict[col] = 'SECTOR'
            elif "ROL" in col: rename_dict[col] = 'CARGO'
            elif "NOMBRE" in col or "COLABORADOR" in col: rename_dict[col] = 'COLABORADOR'
            elif "FORMACION" in col or "CURSO" in col: rename_dict[col] = 'CURSO'
            elif "NIVEL" in col: rename_dict[col] = 'NIVEL'
            elif "CAPACITA" in col: rename_dict[col] = 'ESTADO_NUM'
            
        df = df.rename(columns=rename_dict)
        
        # 3. Limpieza de valores
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        # Convertir a texto y mayúsculas
        for c in ['SECTOR', 'CARGO', 'COLABORADOR', 'NIVEL']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.upper()
                
        return df
    except Exception as e:
        st.error(f"Error leyendo datos: {e}")
        return None

df = load_data()

# --- ESTADO DE LA APP ---
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = "Todos"

# =========================================================
# 🏗️ BARRA LATERAL IZQUIERDA
# =========================================================

# 1. Logo
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

# 2. BOTONES DE SECTORES
if df is not None and 'SECTOR' in df.columns:
    st.sidebar.header("🏢 Sectores")
    
    # Botón Ver Todos
    tipo_todos = "primary" if st.session_state.sector_activo == "Todos" else "secondary"
    if st.sidebar.button("VER TODO", type=tipo_todos, use_container_width=True):
        st.session_state.sector_activo = "Todos"
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
        st.rerun()
    
    # Lista de sectores únicos
    sectores = sorted(df['SECTOR'].unique())
    
    for sec in sectores:
        # Calcular avance del sector
        df_s = df[df['SECTOR'] == sec]
        total = len(df_s)
        ok = len(df_s[df_s['ESTADO_NUM'] == 1])
        porc = (ok / total * 100) if total > 0 else 0
        
        # Color del indicador
        color = "#ef5350" if porc < 50 else "#ffa726" if porc < 80 else "#66bb6a"
        
        # Diseño: Indicador + Botón
        c1, c2 = st.sidebar.columns([1, 4])
        with c1:
            st.markdown(f"<div style='margin-top:10px; width:15px; height:15px; background-color:{color}; border-radius:50%;'></div>", unsafe_allow_html=True)
        with c2:
            tipo = "primary" if st.session_state.sector_activo == sec else "secondary"
            if st.button(f"{sec} ({porc:.0f}%)", key=sec, type=tipo, use_container_width=True):
                st.session_state.sector_activo = sec
                st.session_state.ultimo_cargo_sel = "Todos"
                st.session_state.colaborador_activo = "Todos"
                st.rerun()
                
    st.sidebar.markdown("---")
    
    # 3. FILTRO DE ROL (Dependiente del Sector)
    st.sidebar.header("👮 Puestos")
    
    if st.session_state.sector_activo != "Todos":
        df_roles = df[df['SECTOR'] == st.session_state.sector_activo]
    else:
        df_roles = df
        
    roles = ["Todos"] + sorted(df_roles['CARGO'].unique().tolist())
    
    idx = 0
    if st.session_state.ultimo_cargo_sel in roles:
        idx = roles.index(st.session_state.ultimo_cargo_sel)
        
    sel_rol = st.sidebar.radio("Selecciona:", roles, index=idx)
    
    if sel_rol != st.session_state.ultimo_cargo_sel:
        st.session_state.ultimo_cargo_sel = sel_rol
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

else:
    if df is not None:
        st.sidebar.error("⚠️ No encuentro la columna 'Sector'.")
        st.sidebar.write("Columnas leídas:", list(df.columns))
    df_roles = df if df is not None else pd.DataFrame()

# =========================================================
# 🏠 CUERPO PRINCIPAL
# =========================================================

# Título Dinámico
titulo = st.session_state.sector_activo
if st.session_state.ultimo_cargo_sel != "Todos": titulo += f" > {st.session_state.ultimo_cargo_sel}"
st.title(f"🎓 Formación: {titulo}")

# Filtrado de datos principal
if df is not None:
    df_main = df_roles.copy()
    if st.session_state.ultimo_cargo_sel != "Todos":
        df_main = df_main[df_main['CARGO'] == st.session_state.ultimo_cargo_sel]

    if not df_main.empty:
        # --- 1. PERSONAS ---
        st.subheader("👤 Equipo")
        if 'COLABORADOR' in df_main.columns:
            nombres = sorted(df_main['COLABORADOR'].unique())
            
            tipo_col = "primary" if st.session_state.colaborador_activo == "Todos" else "secondary"
            if st.button(f"👥 Ver Todo el Equipo ({len(nombres)})", type=tipo_col, use_container_width=True):
                st.session_state.colaborador_activo = "Todos"
                st.rerun()
                
            cols = st.columns(4)
            for i, nom in enumerate(nombres):
                tipo = "primary" if st.session_state.colaborador_activo == nom else "secondary"
                if cols[i % 4].button(nom, key=f"user_{i}", type=tipo, use_container_width=True):
                    st.session_state.colaborador_activo = nom
                    st.rerun()

        st.divider()

        # --- 2. DATOS Y MÉTRICAS ---
        df_view = df_main.copy()
        if st.session_state.colaborador_activo != "Todos":
            df_view = df_view[df_view['COLABORADOR'] == st.session_state.colaborador_activo]
            
        total = len(df_view)
        ok = len(df_view[df_view['ESTADO_NUM'] == 1])
        porc = (ok / total * 100) if total > 0 else 0
        
        # Gráfico Velocímetro
        color_g = "green" if porc >= 80 else "orange" if porc >= 50 else "red"
        
        c1, c2 = st.columns([1, 2])
        with c1:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number", value = porc,
                title = {'text': "Progreso"},
                gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': color_g}}
            ))
            fig.update_layout(height=250, margin=dict(t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.info(f"📊 **Estado:** {ok} completados de {total} asignados.")
            
            # Tabla final
            if 'ESTADO_NUM' in df_view.columns:
                st.dataframe(
                    df_view[['SECTOR', 'CARGO', 'COLABORADOR', 'CURSO', 'NIVEL', 'ESTADO_NUM']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={"ESTADO_NUM": st.column_config.CheckboxColumn("Completado", disabled=True)}
                )
    else:
        st.info("No hay datos para mostrar.")
else:
    st.error("No se pudieron cargar los datos.")
