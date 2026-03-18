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
    
    /* Ajuste de altura automática para celdas del calendario */
    .fc .fc-daygrid-day-frame { min-height: 100px !important; }
    .fc-daygrid-event { white-space: normal !important; align-items: flex-start !important; }
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
        col_map = {'ROL': 'CARGO', 'NOMBRE': 'COLABORADOR', 'FORMACION': 'CURSO', 'CAPACITA': 'ESTADO_NUM'}
        for col in df.columns:
            if "SECTOR" in col: col_map[col] = 'SECTOR'
        df = df.rename(columns=col_map)
        df = df.loc[:, ~df.columns.duplicated()]
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=60)
def load_planificacion():
    try:
        df_p = pd.read_csv(URL_PLANIF)
        df_p.columns = df_p.columns.str.strip().str.upper()
        if 'FECHA' in df_p.columns:
            df_p['FECHA_DT'] = pd.to_datetime(df_p['FECHA'], dayfirst=True, errors='coerce')
        df_p = df_p.fillna("")
        return df_p
    except Exception: return pd.DataFrame()

df = load_data_general()
df_planif_raw = load_planificacion()

# --- VARIABLES DE ESTADO ---
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'
if 'nivel_seleccionado' not in st.session_state: st.session_state.nivel_seleccionado = 'Ambos'

# --- CONTENIDO ---
st.title(f"🎓 Gestión de Formación: {st.session_state.sector_activo}")
tab1, tab2, tab3 = st.tabs(["📊 Tablero de Control", "📅 Planificador & Gantt", "🗓️ Agenda de Cursos"])

# --- TAB 1 y 2 (Se mantienen igual) ---
with tab1: st.info("Panel de indicadores general")
with tab2: st.info("Proyección de cumplimiento")

# --- TAB 3: CALENDARIO MEJORADO ---
with tab3:
    # 2. REFERENCIAS ARRIBA
    st.markdown("### 🗓️ Agenda de Cursos Planificados")
    col_ref1, col_ref2, col_ref3 = st.columns([1, 1, 4])
    with col_ref1: st.markdown("🟢 **Presencial**")
    with col_ref2: st.markdown("🔵 **Virtual**")
    with col_ref3: st.markdown("🔴 **Feriado / Fin de Semana**")
    
    if not df_planif_raw.empty and 'FECHA_DT' in df_planif_raw.columns:
        calendar_events = []
        df_cal = df_planif_raw.dropna(subset=['FECHA_DT'])
        
        # 4. FERIADOS NACIONALES ARGENTINA 2026
        feriados_2026 = [
            '2026-01-01', '2026-02-16', '2026-02-17', '2026-03-24', '2026-04-02', 
            '2026-04-03', '2026-05-01', '2026-05-25', '2026-06-15', '2026-06-20', 
            '2026-07-09', '2026-08-17', '2026-10-12', '2026-11-23', '2026-12-08', '2026-12-25'
        ]
        
        for f in feriados_2026:
            calendar_events.append({
                "title": "🇦🇷 FERIADO",
                "start": f,
                "end": f,
                "display": "background",
                "backgroundColor": "#ffcccc", # Rojo clarito
            })

        for _, row in df_cal.iterrows():
            tipo = str(row.get('CURSO', '')).upper()
            color = "#28a745" if "PRESENCIAL" in tipo else "#3788d8"
            
            calendar_events.append({
                "title": f"{str(row.get('COLABORADOR', ''))[:15]} | {str(row.get('NOMBRE DEL CURSO', ''))[:20]}",
                "start": row['FECHA_DT'].strftime('%Y-%m-%d'),
                "end": row['FECHA_DT'].strftime('%Y-%m-%d'),
                "backgroundColor": color,
                "borderColor": color,
                "extendedProps": {
                    "horario": str(row.get('HORARIO', '')),
                    "link": str(row.get('LINK', '')),
                    "obs": str(row.get('OBS:', ''))
                }
            })

        calendar_options = {
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listMonth"},
            "initialView": "dayGridMonth",
            "locale": "es",
            # 1. AJUSTE DE ALTURA: 'auto' permite que la celda crezca según el contenido
            "height": "auto",
            "contentHeight": "auto",
            "expandRows": True,
            # 3. COLORES FINES DE SEMANA (Sábado=6, Domingo=0)
            "businessHours": {"daysOfWeek": [1, 2, 3, 4, 5]}, # Lun-Vie
            "selectMirror": True,
            "dayMaxEvents": False, # Muestra todos los eventos, no pone el "ver más"
        }

        # CSS personalizado para resaltar fines de semana y feriados
        custom_css = """
            .fc-day-sat, .fc-day-sun { background-color: #f2f2f2 !important; } /* 3. Gris claro celdas */
            .fc-day-sat a, .fc-day-sun a { color: red !important; } /* 3. Números en rojo */
        """
        st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)

        state = calendar(events=calendar_events, options=calendar_options, key="cal_agenda_v3")

        if state.get("eventClick"):
            ev = state["eventClick"]["event"]
            st.sidebar.markdown("---")
            st.sidebar.subheader("📋 Detalle del Evento")
            st.sidebar.write(f"**Curso:** {ev['title']}")
            st.sidebar.write(f"**Horario:** {ev['extendedProps']['horario']}")
            st.sidebar.write(f"**Link:** {ev['extendedProps']['link']}")
            if ev['extendedProps']['obs']: st.sidebar.warning(f"Nota: {ev['extendedProps']['obs']}")

    else:
        st.error("No se detectaron datos de fechas válidos en la hoja.")
