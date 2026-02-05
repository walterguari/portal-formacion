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
        white-space: pre-wrap;
    }
    section[data-testid="stSidebar"] .stRadio label {
        font-weight: bold;
    }
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

# --- LOGIN (Opcional) ---
if 'acceso_concedido' not in st.session_state: st.session_state.acceso_concedido = False

def mostrar_login():
    st.markdown("<h2 style='text-align: center;'>🔒 Acceso Privado</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        clave = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True, type="primary"):
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
GID = "245378054" # Pestaña "Avance Formación"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=0) 
def load_data():
    try:
        df = pd.read_csv(URL)
        
        # 1. Normalizar nombres de columnas (Quitar espacios)
        df.columns = df.columns.str.strip()
        
        # 2. Renombrar columnas clave según TU archivo real
        # Tu archivo tiene: "Sector", "Rol en el Concesionario", "Nombre del colaborador", "Capacitaciones"
        col_map = {
            'Sector': 'SECTOR',
            'Rol en el Concesionario': 'CARGO',
            'Nombre del colaborador': 'COLABORADOR',
            'Formacion': 'CURSO',
            'Niveles': 'NIVEL',
            'Capacitaciones': 'ESTADO_NUM'
        }
        # Renombrar solo si existen
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        
        # 3. Limpieza de datos
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        # Convertir textos a mayúsculas para evitar duplicados (ej: "Venta" vs "VENTA")
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
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = "Todos"
if 'filtro_activo' not in st.session_state: st.session_state.filtro_activo = "Todos"

# =========================================================
# --- BARRA LATERAL IZQUIERDA ---
# =========================================================

# 1. Logo
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

# 2. BOTONES DE SECTOR (Lo que pediste)
if not df.empty and 'SECTOR' in df.columns:
    st.sidebar.markdown("### 📊 Sectores")
    
    # Botón para "Ver Todos"
    btn_todos_tipo = "primary" if st.session_state.sector_activo == "Todos" else "secondary"
    if st.sidebar.button("🏢 VER EMPRESA COMPLETA", type=btn_todos_tipo, use_container_width=True):
        st.session_state.sector_activo = "Todos"
        st.session_state.ultimo_cargo_sel = "Todos"
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    # Obtener lista de sectores únicos
    lista_sectores = sorted(df['SECTOR'].dropna().unique())
    
    # Crear los botones uno por uno
    for i, sector in enumerate(lista_sectores):
        # Calcular % del sector
        df_s = df[df['SECTOR'] == sector]
        total_s = len(df_s)
        ok_s = len(df_s[df_s['ESTADO_NUM'] == 1])
        porc_s = (ok_s / total_s * 100) if total_s > 0 else 0
        
        # Color del indicador
        color = "#ef5350" if porc_s < 50 else "#ffa726" if porc_s < 80 else "#66bb6a"
        
        # Diseño: 2 Columnas (Gráfico pequeño + Botón grande)
        c1, c2 = st.sidebar.columns([1, 3])
        
        with c1:
            # Gráfico Circular Pequeño (Donut chart)
            fig = go.Figure(go.Pie(
                values=[porc_s, 100-porc_s],
                hole=0.7,
                textinfo='none',
                marker=dict(colors=[color, '#e0e0e0']),
                hoverinfo='skip'
            ))
            fig.update_layout(showlegend=False, margin=dict(l=0,r=0,t=0,b=0), height=40, width=40)
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
            
        with c2:
            # Botón del Sector
            tipo_btn = "primary" if st.session_state.sector_activo == sector else "secondary"
            # Etiqueta del botón con nombre y %
            label = f"{sector}\n({porc_s:.0f}%)"
            
            if st.button(label, key=f"btn_sec_{i}", type=tipo_btn, use_container_width=True):
                st.session_state.sector_activo = sector
                st.session_state.ultimo_cargo_sel = "Todos" # Resetear filtros hijos
                st.session_state.colaborador_activo = "Todos"
                st.rerun()
    
    st.sidebar.markdown("---")

    # 3. FILTRO DE PUESTO (Depende del Sector)
    st.sidebar.subheader("Puestos:")
    
    # Filtramos la base según el sector elegido arriba
    if st.session_state.sector_activo != "Todos":
        df_filtrado_sector = df[df['SECTOR'] == st.session_state.sector_activo]
    else:
        df_filtrado_sector = df.copy()
        
    lista_cargos = sorted(df_filtrado_sector['CARGO'].dropna().unique())
    opciones_cargos = ["Todos"] + lista_cargos
    
    # Mantener selección si es válida
    idx_cargo = 0
    if st.session_state.ultimo_cargo_sel in opciones_cargos:
        idx_cargo = opciones_cargos.index(st.session_state.ultimo_cargo_sel)
        
    cargo_sel = st.sidebar.radio("Selecciona:", opciones_cargos, index=idx_cargo)
    
    if cargo_sel != st.session_state.ultimo_cargo_sel:
        st.session_state.ultimo_cargo_sel = cargo_sel
        st.session_state.colaborador_activo = "Todos"
        st.rerun()

    # Definir DF Principal
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
    df_main = df.copy()
    if df.empty:
        st.warning("Esperando datos...")

# =========================================================
# --- CUERPO PRINCIPAL (DERECHA) ---
# =========================================================

# Título
titulo = st.session_state.sector_activo
if st.session_state.ultimo_cargo_sel != "Todos": titulo += f" > {st.session_state.ultimo_cargo_sel}"
st.title(f"🎓 Formación: {titulo}")

if not df_main.empty:
    
    # 1. FILTRO DE PERSONAS (Botones)
    st.markdown("### 👤 Colaboradores:")
    if 'COLABORADOR' in df_main.columns:
        nombres = sorted(df_main['COLABORADOR'].unique())
        
        # Botón Ver Todos
        tipo_todos = "primary" if st.session_state.colaborador_activo == "Todos" else "secondary"
        if st.button(f"👥 Ver Todo el Equipo ({len(nombres)})", type=tipo_todos, use_container_width=True):
            st.session_state.colaborador_activo = "Todos"
            st.rerun()
            
        # Grid de nombres
        cols = st.columns(4)
        for i, nom in enumerate(nombres):
            tipo = "primary" if st.session_state.colaborador_activo == nom else "secondary"
            if cols[i%4].button(nom, key=f"col_{i}", type=tipo, use_container_width=True):
                st.session_state.colaborador_activo = nom
                st.rerun()
    
    st.divider()
    
    # 2. CÁLCULO DE DATOS
    df_view = df_main.copy()
    if st.session_state.colaborador_activo != "Todos":
        df_view = df_view[df_view['COLABORADOR'] == st.session_state.colaborador_activo]
        
    total = len(df_view)
    ok = len(df_view[df_view['ESTADO_NUM'] == 1])
    pendientes = total - ok
    porc = (ok/total*100) if total > 0 else 0
    
    # Niveles
    df_n1 = df_view[df_view['NIVEL'].str.contains("1", na=False)]
    falta_n1 = len(df_n1[df_n1['ESTADO_NUM']==0])
    
    df_n2 = df_view[df_view['NIVEL'].str.contains("2", na=False)]
    falta_n2 = len(df_n2[df_n2['ESTADO_NUM']==0])

    # 3. VELOCÍMETRO GRANDE
    color_g = "red" if porc < 50 else "orange" if porc < 80 else "green"
    
    c_g, c_t = st.columns([1, 2])
    with c_g:
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = porc,
            title = {'text': "Avance General"},
            gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': color_g}}
        ))
        fig.update_layout(height=250, margin=dict(l=20,r=20,t=30,b=20))
        st.plotly_chart(fig, use_container_width=True)
        
    with c_t:
        st.markdown(f"### Estado: {'🏆 Excelente' if porc >= 80 else '⚠️ Atención'}")
        st.info(f"Se han completado **{ok}** de **{total}** cursos.")
        
    # 4. BOTONES DE ESTADO (Filtros rápidos)
    c1, c2, c3, c4, c5 = st.columns(5)
    
    b_all = "primary" if st.session_state.filtro_activo == "Todos" else "secondary"
    if c1.button(f"📋 Total ({total})", type=b_all, use_container_width=True): 
        st.session_state.filtro_activo = "Todos"
        st.rerun()
        
    b_fal = "primary" if st.session_state.filtro_activo == "Faltan" else "secondary"
    if c2.button(f"⏳ Faltan ({pendientes})", type=b_fal, use_container_width=True): 
        st.session_state.filtro_activo = "Faltan"
        st.rerun()
        
    b_ok = "primary" if st.session_state.filtro_activo == "Cumplieron" else "secondary"
    if c3.button(f"✅ Listos ({ok})", type=b_ok, use_container_width=True): 
        st.session_state.filtro_activo = "Cumplieron"
        st.rerun()

    b_n1 = "primary" if st.session_state.filtro_activo == "N1" else "secondary"
    if c4.button(f"🔹 N1 (Falta {falta_n1})", type=b_n1, use_container_width=True): 
        st.session_state.filtro_activo = "N1"
        st.rerun()

    b_n2 = "primary" if st.session_state.filtro_activo == "N2" else "secondary"
    if c5.button(f"🔸 N2 (Falta {falta_n2})", type=b_n2, use_container_width=True): 
        st.session_state.filtro_activo = "N2"
        st.rerun()

    # 5. TABLA DE DETALLE
    st.markdown("<br>", unsafe_allow_html=True)
    df_tab = df_view.copy()
    
    if st.session_state.filtro_activo == "Faltan": df_tab = df_tab[df_tab['ESTADO_NUM']==0]
    elif st.session_state.filtro_activo == "Cumplieron": df_tab = df_tab[df_tab['ESTADO_NUM']==1]
    elif st.session_state.filtro_activo == "N1": df_tab = df_n1
    elif st.session_state.filtro_activo == "N2": df_tab = df_n2
    
    # Columnas a mostrar
    cols = ['SECTOR', 'CARGO', 'CURSO', 'NIVEL', 'ESTADO_NUM']
    if st.session_state.colaborador_activo == "Todos":
        cols.insert(0, 'COLABORADOR')
        
    # Verificar que existan antes de mostrar
    cols_final = [c for c in cols if c in df_tab.columns]
    
    st.dataframe(
        df_tab[cols_final],
        use_container_width=True,
        hide_index=True,
        column_config={
            "ESTADO_NUM": st.column_config.CheckboxColumn("OK", disabled=True),
            "SECTOR": st.column_config.TextColumn("Sector", width="small"),
            "CURSO": st.column_config.TextColumn("Capacitación", width="large")
        }
    )

else:
    st.info("No hay datos para mostrar con los filtros actuales.")
