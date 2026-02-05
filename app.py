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

# Usamos ttl=0 para forzar la recarga y detectar la columna nueva
@st.cache_data(ttl=0) 
def load_data():
    try:
        df = pd.read_csv(URL)
        
        # Limpieza básica de nombres de columnas
        df.columns = df.columns.str.strip().str.title()
        
        # --- MAPEO DE COLUMNAS (Incluyendo Sector) ---
        # Buscamos variaciones comunes por si hay espacios extra
        df.rename(columns=lambda x: x.strip(), inplace=True)
        
        col_map = {
            'Sector': 'SECTOR', # Columna A
            'Rol En El Concesionario': 'CARGO', # Columna B
            'Nombre Del Colaborador': 'COLABORADOR',
            'Formacion': 'CURSO',
            'Tipo De Curso': 'TIPO',
            'Niveles': 'NIVEL',
            'Capacitaciones': 'ESTADO_NUM'
        }
        # Renombramos solo las que existen
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        
        # Conversiones de tipos
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

# --- GESTIÓN DE ESTADO ---
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

# 2. INDICADORES DE SECTOR (LO QUE PEDISTE)
if not df.empty and 'SECTOR' in df.columns:
    st.sidebar.markdown("### 📊 Selecciona Sector")
    
    # Botón para resetear (Ver Todos)
    btn_todos_style = "primary" if st.session_state.sector_activo == "Todos" else "secondary"
    if st.sidebar.button("🏢 EMPRESA COMPLETA", type=btn_todos_style, use_container_width=True):
        st.session_state.sector_activo = "Todos"
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    # Obtenemos lista de sectores
    sectores = sorted(df['SECTOR'].dropna().unique())
    
    # Creamos grid de 2 columnas para los botones de sector
    cols_sec = st.sidebar.columns(2)
    
    for i, sector in enumerate(sectores):
        # Calculamos % de ese sector
        df_s = df[df['SECTOR'] == sector]
        total_s = len(df_s)
        ok_s = len(df_s[df_s['ESTADO_NUM'] == 1])
        porc_s = (ok_s / total_s * 100) if total_s > 0 else 0
        
        # Color del gráfico
        color_s = "#ef5350" if porc_s < 50 else "#ffa726" if porc_s < 80 else "#66bb6a"
        
        with cols_sec[i % 2]: # Alternar columnas
            # 1. Mini Gráfico Circular
            fig = go.Figure(go.Pie(
                values=[porc_s, 100-porc_s],
                hole=0.6,
                textinfo='none',
                marker=dict(colors=[color_s, '#e0e0e0']),
                hoverinfo='skip'
            ))
            fig.update_layout(showlegend=False, margin=dict(l=0,r=0,t=0,b=0), height=50, width=50)
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
            
            # 2. Botón del Sector
            btn_style = "primary" if st.session_state.sector_activo == sector else "secondary"
            # Nombre corto si es muy largo
            nombre_btn = f"{sector}\n({porc_s:.0f}%)"
            
            if st.button(nombre_btn, key=f"btn_sec_{i}", type=btn_style, use_container_width=True):
                st.session_state.sector_activo = sector
                st.session_state.ultimo_cargo_sel = "Todos" # Resetear rol al cambiar sector
                st.session_state.colaborador_activo = "Todos"
                st.rerun()
                
    st.sidebar.markdown("---")

    # 3. FILTRO DE ROL (Filtrado por el Sector elegido)
    st.sidebar.subheader(f"Roles en: {st.session_state.sector_activo}")
    
    if st.session_state.sector_activo != "Todos":
        df_filtrado_sector = df[df['SECTOR'] == st.session_state.sector_activo]
    else:
        df_filtrado_sector = df.copy()

    lista_cargos = sorted(df_filtrado_sector['CARGO'].dropna().unique().tolist())
    opciones_rol = ["Todos"] + lista_cargos
    
    # Mantener selección si existe en la nueva lista
    idx_rol = 0
    if st.session_state.ultimo_cargo_sel in opciones_rol:
        idx_rol = opciones_rol.index(st.session_state.ultimo_cargo_sel)
    
    cargo_sel = st.sidebar.radio("Puesto:", opciones_rol, index=idx_rol)
    
    # Actualizar estado si cambia
    if cargo_sel != st.session_state.ultimo_cargo_sel:
        st.session_state.ultimo_cargo_sel = cargo_sel
        st.session_state.colaborador_activo = "Todos"
        st.session_state.filtro_activo = "Todos"
        st.rerun()

    # Filtrar DF principal
    if cargo_sel != "Todos":
        df_main = df_filtrado_sector[df_filtrado_sector['CARGO'] == cargo_sel]
    else:
        df_main = df_filtrado_sector

    # Botón Salir
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Salir"):
        st.session_state.acceso_concedido = False
        st.rerun()

else:
    # Fallback si no hay columna Sector
    if not df.empty: st.sidebar.error("⚠️ No se detectó la columna 'Sector'. Revisa el Excel.")
    df_main = df.copy()

# =========================================================
# --- CUERPO PRINCIPAL ---
# =========================================================

# Título Dinámico
txt_sector = st.session_state.sector_activo
txt_cargo = st.session_state.ultimo_cargo_sel
titulo = f"Formación: {txt_sector}"
if txt_cargo != "Todos": titulo += f" > {txt_cargo}"

st.title(f"🎓 {titulo}")

if not df_main.empty:
    
    # 1. SELECCIÓN DE COLABORADOR
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

    # 2. CÁLCULOS Y GRÁFICOS
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

    # Velocímetro Principal
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

    # 3. FILTROS RÁPIDOS
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

    # 4. TABLA
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
    st.warning("No hay datos para mostrar.")
