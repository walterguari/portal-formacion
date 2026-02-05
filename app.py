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
    .stMetric {
        background-color: #f1f8e9;
        padding: 5px;
        border-radius: 5px;
        text-align: center;
        border: 1px solid #c5e1a5;
    }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# Usamos clear_on_submit para evitar caché viejo si cambian las columnas
@st.cache_data(ttl=30) 
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip().str.title()
        
        # --- MAPEO INTELIGENTE ---
        # Buscamos columnas aunque tengan espacios extra
        df.rename(columns=lambda x: x.strip().title(), inplace=True)
        
        col_map = {
            'Sector': 'SECTOR',
            'Rol En El Concesionario': 'CARGO',
            'Nombre Del Colaborador': 'COLABORADOR',
            'Formacion': 'CURSO',
            'Tipo De Curso': 'TIPO',
            'Niveles': 'NIVEL',
            'Capacitaciones': 'ESTADO_NUM'
        }
        # Solo renombramos si existen
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        # Convertir a mayúsculas para estandarizar
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
elif os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)

# --- DEBUG: Verificar si se detecta la columna SECTOR ---
if not df.empty and 'SECTOR' not in df.columns:
    st.sidebar.error("⚠️ No veo la columna 'Sector'. Pulsa 'Clear Cache' (C) o revisa el Excel.")
    # Intento de autodetectar si tiene otro nombre
    posibles = [c for c in df.columns if 'SECTOR' in c.upper() or 'AREA' in c.upper()]
    if posibles: st.sidebar.info(f"¿Será esta?: {posibles[0]}")

# 2. MINI DASHBOARD DE SECTORES
if not df.empty and 'SECTOR' in df.columns:
    st.sidebar.markdown("### 📊 Avance por Sector")
    
    sectores_unicos = sorted(df['SECTOR'].dropna().unique())
    
    # Crear grid de mini indicadores
    cols = st.sidebar.columns(3) # 3 columnas fijas para que queden ordenados
    
    for i, sector in enumerate(sectores_unicos):
        df_sec = df[df['SECTOR'] == sector]
        total = len(df_sec)
        ok = len(df_sec[df_sec['ESTADO_NUM'] == 1])
        porc = (ok / total * 100) if total > 0 else 0
        
        # Color dinámico
        color = "#ef5350" if porc < 50 else "#ffa726" if porc < 80 else "#66bb6a"
        
        with cols[i % 3]: 
            fig_mini = go.Figure(go.Pie(
                values=[porc, 100-porc],
                hole=0.7,
                textinfo='none',
                marker=dict(colors=[color, '#eeeeee']),
                hoverinfo='skip'
            ))
            fig_mini.update_layout(
                showlegend=False, 
                margin=dict(l=0, r=0, t=0, b=0), 
                height=50, 
                width=50,
            )
            st.plotly_chart(fig_mini, use_container_width=True, config={'staticPlot': True})
            # Etiqueta pequeña
            st.markdown(f"<div style='text-align: center; font-size: 10px; line-height: 1.1;'><b>{sector[:10]}</b><br>{porc:.0f}%</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True) # Espacio

    st.sidebar.markdown("---")

    # 3. FILTRO DE SECTOR
    st.sidebar.subheader("1️⃣ Filtro Sector")
    opciones_sector = ["Todos"] + sectores_unicos
    sector_sel = st.sidebar.selectbox("Selecciona Área:", opciones_sector)
    
    if sector_sel != st.session_state.sector_activo:
        st.session_state.sector_activo = sector_sel
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
    
    if sector_sel != "Todos":
        df_filtrado_sector = df[df['SECTOR'] == sector_sel]
    else:
        df_filtrado_sector = df.copy()

    # 4. FILTRO DE ROL
    st.sidebar.subheader("2️⃣ Filtro Rol")
    lista_cargos = sorted(df_filtrado_sector['CARGO'].dropna().unique().tolist())
    opciones_rol = ["Todos"] + lista_cargos
    
    cargo_sel = st.sidebar.radio("Selecciona Puesto:", opciones_rol)
    
    if cargo_sel != st.session_state.ultimo_cargo_sel:
        st.session_state.ultimo_cargo_sel = cargo_sel
        st.session_state.colaborador_activo = "Todos"
        st.session_state.filtro_activo = "Todos"

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

titulo = f"Formación: {sector_sel}" if 'sector_sel' in locals() and sector_sel != "Todos" else "Formación: General"
if 'cargo_sel' in locals() and cargo_sel != "Todos": titulo += f" > {cargo_sel}"

st.title(f"🎓 {titulo}")

if not df_main.empty:
    
    # SELECCIÓN COLABORADOR
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
            if cols_nombres[i % 4].button(nombre, key=f"btn_{i}", type=tipo_btn, use_container_width=True):
                st.session_state.colaborador_activo = nombre
                st.session_state.filtro_activo = 'Todos'
    
    st.divider()

    # DATOS
    df_view = df_main.copy()
    nombre_visual = "del Grupo"
    
    if st.session_state.colaborador_activo != 'Todos':
        df_view = df_view[df_view['COLABORADOR'] == st.session_state.colaborador_activo]
        nombre_visual = f"de {st.session_state.colaborador_activo}"

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
            title = {'text': "Avance"},
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
        if pendientes == 0: st.success("✅ ¡Todo al día!")

    # BOTONES ESTADO
    st.markdown(f"### 📊 Detalle {nombre_visual}:")
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
        df_table[cols_reales], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "ESTADO_NUM": st.column_config.CheckboxColumn("OK", disabled=True),
            "SECTOR": st.column_config.TextColumn("Sector", width="small"),
            "COLABORADOR": st.column_config.TextColumn("Nombre", width="medium"),
            "CURSO": st.column_config.TextColumn("Capacitación", width="large")
        }
    )
else:
    st.warning("No hay datos.")
