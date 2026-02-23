import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
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
            if "SECTORES" in col: col_map[col] = 'SECTOR'
            elif "SECTOR" in col: col_map[col] = 'SECTOR'
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

# --- PREPARACIÓN DE DATOS PRINCIPALES ---
titulo = st.session_state.sector_activo
if sel_rol != "Todos": titulo += f" > {sel_rol}"
df_main = df_roles[df_roles['CARGO'] == sel_rol] if sel_rol != "Todos" else df_roles

# =========================================================
# 📌 PESTAÑAS (TABS)
# =========================================================
st.title(f"🎓 Gestión de Formación: {titulo}")

tab1, tab2 = st.tabs(["📊 Tablero de Control", "📅 Planificador (Días Hábiles)"])

# ---------------------------------------------------------
# PESTAÑA 1: TABLERO DE CONTROL
# ---------------------------------------------------------
with tab1:
    if not df_main.empty:
        # PERSONAS
        st.markdown("### 👤 Selecciona Equipo")
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
        
        # CÁLCULOS
        df_view = df_main[df_main['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_main
        total = len(df_view)
        ok = len(df_view[df_view['ESTADO_NUM']==1])
        porc = (ok/total*100) if total > 0 else 0
        
        # EMOCIONES
        if porc == 100:
            mensaje = "🏆 ¡OBJETIVO CUMPLIDO! FELICITACIONES"
            color_msg = "green"
            st.balloons()
        elif porc >= 80:
            mensaje = "🚀 ¡Excelente ritmo! Recta final."
            color_msg = "green"
        elif porc >= 50:
            mensaje = "🔨 Buen trabajo, a no bajar los brazos."
            color_msg = "orange"
        else:
            mensaje = "⚠️ Nivel Crítico: Se requiere plan de acción inmediato."
            color_msg = "red"

        st.markdown(f"<div style='background-color:{'#e8f5e9' if color_msg=='green' else '#fff3e0' if color_msg=='orange' else '#ffebee'}; padding:15px; border-radius:10px; border-left: 5px solid {color_msg}; margin-bottom: 20px;'><h3 style='margin:0; color:{color_msg}'>{mensaje}</h3></div>", unsafe_allow_html=True)

        # GRÁFICO
        c1, c2 = st.columns([1, 2])
        with c1:
            fig = go.Figure(go.Indicator(mode="gauge+number", value=porc, title={'text':"Avance"}, gauge={'axis':{'range':[None,100]}, 'bar':{'color': color_msg}}))
            fig.update_layout(height=250, margin=dict(t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.info(f"Completado: **{ok}** de **{total}** cursos.")
            st.dataframe(df_view[['SECTOR','CARGO','CURSO','ESTADO_NUM']], use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos.")

# ---------------------------------------------------------
# PESTAÑA 2: PLANIFICADOR (DÍAS HÁBILES)
# ---------------------------------------------------------
with tab2:
    # --- FECHA LÍMITE: 20 DE MARZO DE 2026 ---
    fecha_fin = datetime(2026, 3, 20)
    st.markdown("### 📅 Planificación al 20 de Marzo 2026")
    
    # 1. Configuración de Fechas
    fecha_hoy = datetime.now()
    
    # CÁLCULO DE DÍAS HÁBILES (Lunes a Viernes)
    dias_habiles = 0
    temp_date = fecha_hoy
    while temp_date <= fecha_fin:
        # weekday(): 0=Lunes, 4=Viernes, 5=Sábado, 6=Domingo
        if temp_date.weekday() < 5: 
            dias_habiles += 1
        temp_date += timedelta(days=1)
    
    # Semanas "laborales" aproximadas (para agrupar visualmente)
    semanas_restantes = math.ceil(dias_habiles / 5) 

    if dias_habiles < 0:
        st.error("🚨 ¡La fecha límite ha pasado!")
    else:
        st.success(f"🗓️ Quedan **{dias_habiles} días hábiles** (aprox. {semanas_restantes} semanas de trabajo) hasta el cierre del 20/03.")

    st.divider()

    if not df_main.empty:
        # Filtrar solo pendientes
        df_pendientes = df_main[df_main['ESTADO_NUM'] == 0].copy()
        
        if st.session_state.colaborador_activo != 'Todos':
            df_plan = df_pendientes[df_pendientes['COLABORADOR'] == st.session_state.colaborador_activo]
            titulo_plan = f"Plan para: {st.session_state.colaborador_activo}"
        else:
            df_plan = df_pendientes
            titulo_plan = f"Plan Global: {st.session_state.sector_activo} > {sel_rol}"

        total_pendientes_plan = len(df_plan)

        if total_pendientes_plan == 0:
            st.balloons()
            st.success(f"✅ ¡{titulo_plan} no tiene nada pendiente! Objetivo Cumplido.")
        elif semanas_restantes > 0:
            # Cálculo de ritmo
            ritmo_semanal = math.ceil(total_pendientes_plan / semanas_restantes)
            
            c_info, c_metric = st.columns([3, 1])
            with c_info:
                st.markdown(f"#### 🎯 {titulo_plan}")
                st.write(f"Cursos pendientes: **{total_pendientes_plan}**")
                st.info(f"💡 Nuevo Objetivo: Completar **{ritmo_semanal} cursos por semana**.")
            
            with c_metric:
                st.metric("Meta Semanal", f"{ritmo_semanal}", "Cursos")

            # --- GENERADOR DE AGENDA ---
            st.subheader("📆 Cronograma Sugerido")
            
            cursos_pendientes = df_plan[['COLABORADOR', 'CURSO', 'NIVEL']].values.tolist()
            semanas_dict = {i: [] for i in range(1, semanas_restantes + 1)}
            
            for i, curso in enumerate(cursos_pendientes):
                num_semana = (i % semanas_restantes) + 1
                semanas_dict[num_semana].append(curso)

            # Mostrar agenda visual
            for i in range(1, semanas_restantes + 1):
                # Calculamos las fechas de inicio y fin de esa semana "laboral"
                inicio_sem = fecha_hoy + timedelta(weeks=i-1)
                
                tareas_semana = semanas_dict[i]
                titulo_expander = f"📌 Semana {i} (Meta: {len(tareas_semana)} cursos)"
                
                if tareas_semana:
                    with st.expander(titulo_expander, expanded=(i==1)):
                        df_sem = pd.DataFrame(tareas_semana, columns=['Colaborador', 'Curso', 'Nivel'])
                        st.table(df_sem)
                else:
                    st.caption(f"🏁 Semana {i}: Libre (Plan cumplido)")

        else:
            st.error("⏳ ¡Cuidado! Queda muy poco tiempo para la cantidad de cursos pendientes.")
