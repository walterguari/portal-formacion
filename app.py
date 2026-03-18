import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import math
from streamlit_calendar import calendar

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 8px; font-weight: bold; margin-bottom: 5px; height: 45px;}
    [data-testid="stSidebar"] img {display: block; margin: 0 auto 20px auto;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; padding: 10px 20px; }
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
GID_GENERAL = "245378054"
GID_PLANIF = "829571230"

URL_GENERAL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_GENERAL}"
URL_PLANIF = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PLANIF}"

@st.cache_data(ttl=60)
def load_data_general():
    try:
        df = pd.read_csv(URL_GENERAL)
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
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=60)
def load_planificacion():
    try:
        df_p = pd.read_csv(URL_PLANIF)
        df_p.columns = df_p.columns.str.strip().str.upper()
        # Convertir columna FECHA a formato datetime
        if 'FECHA' in df_p.columns:
            df_p['FECHA_DT'] = pd.to_datetime(df_p['FECHA'], dayfirst=True, errors='coerce')
        return df_p
    except Exception: return pd.DataFrame()

df = load_data_general()
df_planif_raw = load_planificacion()

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
        st.session_state.sector_activo = "Todos"; st.session_state.ultimo_cargo_sel = "Todos"; st.session_state.colaborador_activo = "Todos"; st.rerun()

    for sec in sorted(df['SECTOR'].unique()):
        df_s = df[df['SECTOR'] == sec]
        avance = (len(df_s[df_s['ESTADO_NUM']==1]) / len(df_s) * 100) if len(df_s) > 0 else 0
        color_sidebar = "#ef5350" if avance < 50 else "#ffa726" if avance < 90 else "#66bb6a"
        c1, c2 = st.sidebar.columns([1, 4])
        with c1: st.markdown(f"<div style='margin-top:10px; width:15px; height:15px; background-color:{color_sidebar}; border-radius:50%;'></div>", unsafe_allow_html=True)
        with c2:
            if st.button(f"{sec} ({avance:.0f}%)", key=f"sidebar_{sec}", type=("primary" if st.session_state.sector_activo == sec else "secondary")):
                st.session_state.sector_activo = sec; st.session_state.ultimo_cargo_sel = "Todos"; st.session_state.colaborador_activo = "Todos"; st.rerun()

# FILTRO ROL
st.sidebar.title("👮 Puestos")
df_roles = df[df['SECTOR'] == st.session_state.sector_activo] if st.session_state.sector_activo != "Todos" else df
roles = ["Todos"] + sorted(df_roles['CARGO'].unique().tolist()) if 'CARGO' in df_roles.columns else ["Todos"]
idx = roles.index(st.session_state.ultimo_cargo_sel) if st.session_state.ultimo_cargo_sel in roles else 0
sel_rol = st.sidebar.radio("Selecciona:", roles, index=idx)
if sel_rol != st.session_state.ultimo_cargo_sel:
    st.session_state.ultimo_cargo_sel = sel_rol; st.session_state.colaborador_activo = 'Todos'; st.rerun()

if st.sidebar.button("🔒 Salir"):
    st.session_state.acceso_concedido = False; st.rerun()

# --- DATOS FILTRADOS ---
df_main = df_roles[df_roles['CARGO'] == sel_rol] if sel_rol != "Todos" else df_roles

st.title(f"🎓 Gestión de Formación: {st.session_state.sector_activo} > {sel_rol}")
tab1, tab2, tab3 = st.tabs(["📊 Tablero de Control", "📅 Planificador & Gantt", "🗓️ Agenda de Cursos"])

# --- TAB 1: TABLERO ---
with tab1:
    if not df_main.empty:
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

        st.markdown(f"### 👤 Equipo - Avance en {st.session_state.nivel_seleccionado}")
        nombres = sorted(df_main['COLABORADOR'].unique())
        cols = st.columns(4)
        if cols[0].button(f"👥 Ver Todo ({len(nombres)})", type=("primary" if st.session_state.colaborador_activo == 'Todos' else "secondary")):
             st.session_state.colaborador_activo = 'Todos'; st.rerun()
        
        for i, nom in enumerate(nombres):
            df_indiv = df_main[df_main['COLABORADOR'] == nom]
            if st.session_state.nivel_seleccionado != 'Ambos':
                df_indiv = df_indiv[df_indiv['NIVEL'] == st.session_state.nivel_seleccionado]
            
            t_ind = len(df_indiv)
            ok_ind = len(df_indiv[df_indiv['ESTADO_NUM'] == 1])
            p_ind = (ok_ind / t_ind * 100) if t_ind > 0 else 0
            
            if p_ind == 100: emoji, logro = "🟢", "🏆🎈"
            elif p_ind < 50: emoji, logro = "🔴", ""
            else: emoji, logro = "🟠", ""
            
            tipo_btn = "primary" if st.session_state.colaborador_activo == nom else "secondary"
            texto_final = f"{emoji} {nom} {logro} ({p_ind:.0f}%)"
            
            if cols[(i+1)%4].button(texto_final, key=f"btn_{i}", type=tipo_btn):
                st.session_state.colaborador_activo = nom; st.rerun()
        
        st.divider()

        df_view = df_main[df_main['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_main
        df_view_calc = df_view if st.session_state.nivel_seleccionado == 'Ambos' else df_view[df_view['NIVEL'] == st.session_state.nivel_seleccionado]

        total = len(df_view_calc)
        ok = len(df_view_calc[df_view_calc['ESTADO_NUM']==1])
        porc = (ok/total*100) if total > 0 else 0
        color_msg = "green" if porc == 100 else "orange" if porc >= 50 else "red"
        
        if porc == 100 and st.session_state.colaborador_activo != 'Todos': st.balloons()

        st.markdown(f"<div style='background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid {color_msg};'><h4>Avance {st.session_state.nivel_seleccionado}: {porc:.1f}%</h4></div>", unsafe_allow_html=True)

        c1, c2 = st.columns([1, 2])
        with c1:
            fig = go.Figure(go.Indicator(mode="gauge+number", value=porc, gauge={'axis':{'range':[None,100]}, 'bar':{'color': color_msg}}))
            fig.update_layout(height=250, margin=dict(t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.info(f"Completado: **{ok}** de **{total}** cursos.")
            st.dataframe(df_view_calc[['COLABORADOR','CURSO','NIVEL','ESTADO_NUM']], use_container_width=True, hide_index=True)

# --- TAB 2: PLANIFICADOR ---
with tab2:
    fecha_fin = datetime(2026, 3, 20)
    fecha_hoy = datetime.now()
    dias_h = 0
    temp_d = fecha_hoy
    while temp_d <= fecha_fin:
        if temp_d.weekday() < 5: dias_h += 1
        temp_d += timedelta(days=1)
    
    semanas_r = max(1, math.ceil(dias_h / 5))
    st.subheader(f"📅 Planificación al 20/03/2026")
    
    df_pend = df_main[df_main['ESTADO_NUM'] == 0]
    if st.session_state.nivel_seleccionado != 'Ambos':
        df_pend = df_pend[df_pend['NIVEL'] == st.session_state.nivel_seleccionado]
    
    df_plan = df_pend[df_pend['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_pend

    if not df_plan.empty:
        ritmo = math.ceil(len(df_plan) / semanas_r)
        st.metric("Meta Semanal", f"{ritmo} cursos/semana")

        st.markdown("### 📊 Cronograma Visual (Gantt)")
        df_gantt = []
        cursos_l = df_plan[['COLABORADOR', 'CURSO', 'NIVEL']].values.tolist()
        for i, curso in enumerate(cursos_l):
            n_s = (i // ritmo)
            ini = fecha_hoy + timedelta(weeks=n_s)
            df_gantt.append(dict(Task=f"{curso[0][:15]}..", Start=ini.strftime('%Y-%m-%d'), Finish=(ini + timedelta(days=4)).strftime('%Y-%m-%d'), Resource=curso[2]))

        if df_gantt:
            fig_g = ff.create_gantt(df_gantt, index_col='Resource', show_colorbar=True, group_tasks=True, showgrid_x=True)
            st.plotly_chart(fig_g, use_container_width=True)
        
        for s in range(semanas_r):
            t_sem = cursos_l[s*ritmo : (s+1)*ritmo]
            if t_sem:
                with st.expander(f"Semana {s+1}"):
                    st.table(pd.DataFrame(t_sem, columns=['Colaborador', 'Curso', 'Nivel']))
    else:
        st.success("🎉 ¡Objetivo cumplido! Sin tareas pendientes.")

# --- TAB 3: CALENDARIO INTERACTIVO ---
with tab3:
    st.header("🗓️ Calendario de Cursos Planificados")
    
    if not df_planif_raw.empty and 'FECHA_DT' in df_planif_raw.columns:
        # 1. Preparar eventos para el calendario
        calendar_events = []
        df_cal = df_planif_raw.dropna(subset=['FECHA_DT'])
        
        for _, row in df_cal.iterrows():
            # Color: Verde si es presencial, Azul si es virtual
            mod = str(row.get('MODALIDAD', '')).upper()
            color = "#28a745" if "PRESENCIAL" in mod else "#3788d8"
            
            calendar_events.append({
                "title": f"👤 {row.get('COLABORADOR', 'S/N')} | 📚 {row.get('NOMBRE DEL CURSO', 'Curso')[:20]}",
                "start": row['FECHA_DT'].strftime('%Y-%m-%d'),
                "end": row['FECHA_DT'].strftime('%Y-%m-%d'),
                "backgroundColor": color,
                "borderColor": color,
                "extendedProps": {
                    "horario": row.get('HORARIO', 'No definido'),
                    "link": row.get('LINK', 'Sin link'),
                    "obs": row.get('OBS:', 'Sin observaciones')
                }
            })

        # 2. Opciones del Calendario
        calendar_options = {
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,listMonth",
            },
            "initialView": "dayGridMonth",
            "locale": "es",
        }

        # 3. Renderizar Calendario
        state = calendar(events=calendar_events, options=calendar_options, key="portal_calendar")

        # 4. Detalle en Sidebar al hacer clic
        if state.get("eventClick"):
            ev = state["eventClick"]["event"]
            st.sidebar.markdown("---")
            st.sidebar.subheader("🔍 Detalle del Curso")
            st.sidebar.write(f"**Curso:** {ev['title']}")
            st.sidebar.write(f"**Horario:** {ev['extendedProps']['horario']}")
            st.sidebar.write(f"**Link:** {ev['extendedProps']['link']}")
            st.sidebar.info(f"Nota: {ev['extendedProps']['obs']}")

        st.markdown("🟢 **Presencial** | 🔵 **Virtual** (Haz clic en un evento para ver detalles en la barra lateral)")
        
        with st.expander("Ver lista completa (Formato Tabla)"):
             st.dataframe(df_planif_raw.drop(columns=['FECHA_DT']), use_container_width=True, hide_index=True)
    else:
        st.error("⚠️ No se detectaron fechas válidas en la hoja de Planificación.")
