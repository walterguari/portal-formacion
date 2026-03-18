import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import math
from streamlit_calendar import calendar  # Requiere: pip install streamlit-calendar

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 8px; font-weight: bold; margin-bottom: 5px; height: 45px;}
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px 4px 0 0; }
    .stTabs [aria-selected="true"] { border-bottom: 2px solid #4CAF50; }
    /* Ajuste para que el calendario se vea bien en modo oscuro/claro */
    .fc-event { cursor: pointer; }
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
        col_map = {c: 'SECTOR' for c in df.columns if "SECTOR" in c}
        col_map.update({c: 'CARGO' for c in df.columns if "ROL" in c})
        col_map.update({c: 'COLABORADOR' for c in df.columns if "NOMBRE" in c or "COLABORADOR" in c})
        col_map.update({c: 'CURSO' for c in df.columns if "FORMACION" in c})
        col_map.update({c: 'NIVEL' for c in df.columns if "NIVEL" in c})
        col_map.update({c: 'ESTADO_NUM' for c in df.columns if "CAPACITA" in c})
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
        # Convertir FECHA a datetime para el calendario
        if 'FECHA' in df_p.columns:
            df_p['FECHA_DT'] = pd.to_datetime(df_p['FECHA'], dayfirst=True, errors='coerce')
        return df_p
    except Exception: return pd.DataFrame()

df = load_data_general()
df_planif_raw = load_planificacion()

# --- BARRA LATERAL (Simplificada para el ejemplo) ---
st.sidebar.title("🏢 Navegación")
if st.sidebar.button("🔒 Salir"):
    st.session_state.acceso_concedido = False
    st.rerun()

# --- TABS PRINCIPALES ---
st.title("🎓 Portal de Formación Cenoa 2026")
tab1, tab2, tab3 = st.tabs(["📊 Tablero de Control", "📅 Planificador & Gantt", "🗓️ Calendario de Agenda"])

with tab1:
    st.info("Visualiza aquí el avance general de los sectores.")
    # (Aquí iría tu lógica de indicadores previa)

with tab2:
    st.info("Proyección de cumplimiento al 20/03/2026.")
    # (Aquí iría tu lógica de Gantt previa)

# --- TAB 3: CALENDARIO INTERACTIVO ---
with tab3:
    st.header("🗓️ Calendario de Cursos Planificados")
    
    if not df_planif_raw.empty and 'FECHA_DT' in df_planif_raw.columns:
        # 1. Preparar eventos para el calendario
        calendar_events = []
        for _, row in df_planif_raw.dropna(subset=['FECHA_DT']).iterrows():
            # Definir color según modalidad
            color = "#3788d8" if "VIRTUAL" in str(row.get('CURSO', '')).upper() else "#28a745"
            
            event = {
                "title": f"{row.get('COLABORADOR', 'Sin nombre')} - {row.get('NOMBRE DEL CURSO', 'Curso')[:20]}...",
                "start": row['FECHA_DT'].strftime('%Y-%m-%d'),
                "end": row['FECHA_DT'].strftime('%Y-%m-%d'),
                "resourceId": row.get('HORARIO', 'Todo el día'),
                "backgroundColor": color,
                "extendedProps": {
                    "colaborador": row.get('COLABORADOR', ''),
                    "horario": row.get('HORARIO', ''),
                    "link": row.get('LINK', 'No disponible'),
                    "obs": row.get('OBS:', '')
                }
            }
            calendar_events.append(event)

        # 2. Configuración del Calendario
        calendar_options = {
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,listWeek",
            },
            "initialView": "dayGridMonth",
            "locale": "es",
            "selectable": True,
        }

        # 3. Mostrar Calendario
        state = calendar(events=calendar_events, options=calendar_options, key="formacion_calendar")

        # 4. Mostrar detalles al hacer clic (opcional)
        if "eventClick" in state:
            event_data = state["eventClick"]["event"]
            st.sidebar.markdown("---")
            st.sidebar.subheader("🔍 Detalle del Curso")
            st.sidebar.write(f"**Colaborador:** {event_data['extendedProps']['colaborador']}")
            st.sidebar.write(f"**Horario:** {event_data['extendedProps']['horario']}")
            st.sidebar.write(f"**Link:** {event_data['extendedProps']['link']}")
            st.sidebar.info(f"Nota: {event_data['extendedProps']['obs']}")

        # 5. Leyenda y Tabla debajo
        st.markdown("**Referencia de colores:** 🔵 Virtual | 🟢 Presencial")
        with st.expander("Ver lista completa (Formato Tabla)"):
            st.dataframe(df_planif_raw.drop(columns=['FECHA_DT']), use_container_width=True, hide_index=True)
    else:
        st.error("No se encontraron fechas válidas en la hoja de planificación.")
