import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import math

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 8px; font-weight: bold; border: 1px solid #dce775; margin-bottom: 5px;}
    [data-testid="stSidebar"] img {display: block; margin: 0 auto 20px auto;}
    .big-font { font-size:20px !important; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4CAF50; }
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
        df.columns = df.columns.str.strip().str.upper()
        
        col_map = {}
        for col in df.columns:
            if "SECTORES" in col or "SECTOR" in col: col_map[col] = 'SECTOR'
            elif "ROL" in col: col_map[col] = 'CARGO'
            elif "NOMBRE" in col or "COLABORADOR" in col: col_map[col] = 'COLABORADOR'
            elif "FORMACION" in col: col_map[col] = 'CURSO'
            elif "NIVEL" in col: col_map[col] = 'NIVEL'
            elif "CAPACITA" in col: col_map[col] = 'ESTADO_NUM'

        df = df.rename(columns=col_map)
        df = df.loc[:, ~df.columns.duplicated()]

        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        
        for c in ['SECTOR', 'CARGO', 'COLABORADOR', 'NIVEL']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.upper()

        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# --- VARIABLES DE ESTADO ---
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'
if 'nivel_seleccionado' not in st.session_state: st.session_state.nivel_seleccionado = 'Ambos'

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

# --- PREPARACIÓN DE DATOS PRINCIPALES ---
titulo = st.session_state.sector_activo
if sel_rol != "Todos": titulo += f" > {sel_rol}"
df_main = df_roles[df_roles['CARGO'] == sel_rol] if sel_rol != "Todos" else df_roles

# =========================================================
# 📌 CUERPO PRINCIPAL
# =========================================================
st.title(f"🎓 Gestión de Formación: {titulo}")

tab1, tab2 = st.tabs(["📊 Tablero de Control", "📅 Planificador & Gantt"])

# ---------------------------------------------------------
# PESTAÑA 1: TABLERO DE CONTROL
# ---------------------------------------------------------
with tab1:
    if not df_main.empty:
        # SELECCIÓN DE EQUIPO CON % INDIVIDUAL
        st.markdown("### 👤 Selecciona Equipo")
        nombres = sorted(df_main['COLABORADOR'].unique())
        
        cols = st.columns(4)
        if cols[0].button(f"👥 Ver Todo ({len(nombres)})", type=("primary" if st.session_state.colaborador_activo == 'Todos' else "secondary")):
             st.session_state.colaborador_activo = 'Todos'
             st.rerun()
        
        for i, nom in enumerate(nombres):
            df_colab = df_main[df_main['COLABORADOR'] == nom]
            total_c = len(df_colab)
            ok_c = len(df_colab[df_colab['ESTADO_NUM'] == 1])
            porc_c = (ok_c / total_c * 100) if total_c > 0 else 0
            
            texto_boton = f"{nom} ({porc_c:.0f}%)"
            
            if cols[(i+1)%4].button(texto_boton, key=f"btn_{i}", type=("primary" if st.session_state.colaborador_activo == nom else "secondary")):
                st.session_state.colaborador_activo = nom
                st.rerun()
        
        st.divider()

        # SELECTORES DE NIVEL
        st.markdown("### ⚖️ Filtrar Indicador por Nivel")
        c_n1, c_n2, c_nb = st.columns(3)
        with c_n1:
            if st.button("NIVEL 1", type=("primary" if st.session_state.nivel_seleccionado == 'NIVEL 1' else "secondary")):
                st.session_state.nivel_seleccionado = 'NIVEL 1'; st.rerun()
        with c_n2:
            if st.button("NIVEL 2", type=("primary" if st.session_state.nivel_seleccionado == 'NIVEL 2' else "secondary")):
                st.session_state.nivel_seleccionado = 'NIVEL 2'; st.rerun()
        with c_nb:
            if st.button("AMBOS NIVELES", type=("primary" if st.session_state.nivel_seleccionado == 'Ambos' else "secondary")):
                st.session_state.nivel_seleccionado = 'Ambos'; st.rerun()

        # Filtrado de cálculos
        df_view = df_main[df_main['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_main
        if st.session_state.nivel_seleccionado != 'Ambos':
            df_view_calc = df_view[df_view['NIVEL'] == st.session_state.nivel_seleccionado]
        else:
            df_view_calc = df_view

        total = len(df_view_calc)
        ok = len(df_view_calc[df_view_calc['ESTADO_NUM']==1])
        porc = (ok/total*100) if total > 0 else 0
        
        color_msg = "green" if porc >= 80 else "orange" if porc >= 50 else "red"
        st.markdown(f"<div style='background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid {color_msg};'><h4>Avance {st.session_state.nivel_seleccionado}: {porc:.1f}%</h4></div>", unsafe_allow_html=True)

        c1, c2 = st.columns([1, 2])
        with c1:
            fig = go.Figure(go.Indicator(mode="gauge+number", value=porc, gauge={'axis':{'range':[None,100]}, 'bar':{'color': color_msg}}))
            fig.update_layout(height=250, margin=dict(t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.info(f"Completado: **{ok}** de **{total}** cursos.")
            st.dataframe(df_view_calc[['SECTOR','CARGO','CURSO','NIVEL','ESTADO_NUM']], use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# PESTAÑA 2: PLANIFICADOR & GANTT
# ---------------------------------------------------------
with tab2:
    fecha_fin = datetime(2026, 3, 20)
    fecha_hoy = datetime.now()
    
    dias_habiles = 0
    temp_date = fecha_hoy
    while temp_date <= fecha_fin:
        if temp_date.weekday() < 5: dias_habiles += 1
        temp_date += timedelta(days=1)
    
    semanas_restantes = max(1, math.ceil(dias_habiles / 5))

    st.subheader(f"📅 Planificación al 20/03/2026")
    st.info(f"Quedan **{dias_habiles} días hábiles** (aprox. {semanas_restantes} semanas).")
    
    df_pendientes = df_main[df_main['ESTADO_NUM'] == 0]
    if st.session_state.nivel_seleccionado != 'Ambos':
        df_pendientes = df_pendientes[df_pendientes['NIVEL'] == st.session_state.nivel_seleccionado]
    
    if st.session_state.colaborador_activo != 'Todos':
        df_plan = df_pendientes[df_pendientes['COLABORADOR'] == st.session_state.colaborador_activo]
    else:
        df_plan = df_pendientes

    if not df_plan.empty:
        ritmo = math.ceil(len(df_plan) / semanas_restantes)
        st.metric("Meta de Capacitación", f"{ritmo} cursos/semana")

        # --- GRÁFICO DE GANTT ---
        st.markdown("### 📊 Cronograma Visual (Gantt)")
        df_gantt = []
        cursos_list = df_plan[['COLABORADOR', 'CURSO', 'NIVEL']].values.tolist()
        
        for i, curso in enumerate(cursos_list):
            num_sem = (i // ritmo)
            inicio = fecha_hoy + timedelta(weeks=num_sem)
            fin = inicio + timedelta(days=4)
            df_gantt.append(dict(
                Task=curso[0], 
                Start=inicio.strftime('%Y-%m-%d'), 
                Finish=fin.strftime('%Y-%m-%d'), 
                Resource=curso[2]
            ))

        if df_gantt:
            fig_gantt = ff.create_gantt(df_gantt, index_col='Resource', show_colorbar=True, group_tasks=True, showgrid_x=True)
            fig_gantt.update_layout(height=450)
            st.plotly_chart(fig_gantt, use_container_width=True)

        # --- AGENDA DETALLADA ---
        st.markdown("### 📆 Agenda por Semanas")
        for s in range(semanas_restantes):
            tareas = cursos_list[s*ritmo : (s+1)*ritmo]
            if tareas:
                with st.expander(f"Semana {s+1}"):
                    st.table(pd.DataFrame(tareas, columns=['Colaborador', 'Curso', 'Nivel']))
    else:
        st.success("🎉 ¡Objetivo cumplido! No hay tareas pendientes para esta selección.")
