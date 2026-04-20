import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import math
from streamlit_calendar import calendar
import google.generativeai as genai
from fpdf import FPDF

# --- CLASE PARA DISEÑO DE REPORTE PDF ---
class PDFReport(FPDF):
    def header(self):
        # Fondo azul oscuro para el encabezado corporativo de AUTOCIEL
        self.set_fill_color(0, 51, 102)
        self.rect(0, 0, 210, 35, 'F')
        self.set_font("Arial", 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, "AUTOCIEL - REPORTE DE FORMACION 2026", ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()} | Portal Formacion AUTOCIEL", align='C')

def generar_pdf_binario(colab, avance, analisis, df_plan):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    
    # Seccion: Datos del Colaborador
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Colaborador: {colab}", ln=True)
    pdf.cell(0, 10, f"Nivel de Avance Total: {avance}%", ln=True)
    pdf.ln(5)
    
    # Seccion: Analisis IA (con limpieza de caracteres para FPDF)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, " Recomendacion Estrategica (IA Gemini):", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    analisis_limpio = analisis.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, analisis_limpio)
    pdf.ln(5)
    
    # Seccion: Tabla de Planificacion
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, " Proximas Capacitaciones Programadas en AUTOCIEL:", ln=True)
    
    # Encabezados de tabla
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(100, 7, "Curso", 1, 0, 'C', True)
    pdf.cell(40, 7, "Fecha", 1, 0, 'C', True)
    pdf.cell(40, 7, "Horario", 1, 1, 'C', True)
    
    # Contenido de la tabla
    pdf.set_font("Arial", '', 8)
    if not df_plan.empty:
        for _, fila in df_plan.iterrows():
            pdf.cell(100, 7, str(fila.get('NOMBRE DEL CURSO', ''))[:55], 1)
            pdf.cell(40, 7, str(fila.get('FECHA', '')), 1, 0, 'C')
            pdf.cell(40, 7, str(fila.get('HORARIO', '')), 1, 1, 'C')
    else:
        pdf.cell(180, 7, "No hay cursos registrados en la planificacion actual.", 1, 1, 'C')
        
    return pdf.output()

# --- CONFIGURACIÓN DE IA (SECRETS) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Falta la GEMINI_API_KEY en los Secrets de Streamlit.")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Formación AUTOCIEL 2026", layout="wide", page_icon="🎓")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 8px; font-weight: bold; margin-bottom: 5px; height: 45px;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px 4px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if 'acceso_concedido' not in st.session_state:
    st.session_state.acceso_concedido = False

def mostrar_login():
    st.markdown("<h2 style='text-align: center;'>🔒 Portal Privado AUTOCIEL</h2>", unsafe_allow_html=True)
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
        for c in df.columns:
            if "SECTOR" in c: col_map[c] = 'SECTOR'
            elif "ROL" in c or "CARGO" in c: col_map[c] = 'CARGO'
            elif "NOMBRE" in c or "COLABORADOR" in c: col_map[c] = 'COLABORADOR'
            elif "FORMACION" in c or "CURSO" in c: col_map[c] = 'CURSO'
            elif "CAPACITA" in c or "ESTADO" in c: col_map[c] = 'ESTADO_NUM'
            elif "NIVEL" in c: col_map[c] = 'NIVEL'
        df = df.rename(columns=col_map)
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        for c in ['SECTOR', 'CARGO', 'COLABORADOR', 'NIVEL']:
            if c in df.columns: df[c] = df[c].astype(str).str.strip().str.upper()
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def load_planificacion():
    try:
        df_p = pd.read_csv(URL_PLANIF)
        df_p.columns = df_p.columns.str.strip().str.upper()
        if 'FECHA' in df_p.columns:
            df_p['FECHA_DT'] = pd.to_datetime(df_p['FECHA'], dayfirst=True, errors='coerce')
        return df_p.fillna("")
    except: return pd.DataFrame()

df = load_data_general()
df_planif_raw = load_planificacion()

# --- NAVEGACIÓN ---
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'

st.sidebar.title("🏢 AUTOCIEL")
if st.sidebar.button("VER TODO EL CONCESIONARIO", type=("primary" if st.session_state.sector_activo == "Todos" else "secondary")):
    st.session_state.update({"sector_activo": "Todos", "colaborador_activo": "Todos"})
    st.rerun()

for sec in sorted(df['SECTOR'].unique()):
    if st.sidebar.button(sec, key=f"side_{sec}", type=("primary" if st.session_state.sector_activo == sec else "secondary")):
        st.session_state.update({"sector_activo": sec, "colaborador_activo": "Todos"})
        st.rerun()

# --- INTERFAZ ---
st.title(f"🎓 Gestión de Formación AUTOCIEL: {st.session_state.sector_activo}")
tab1, tab2, tab3 = st.tabs(["📊 Tablero de Control", "📅 Planificador & Gantt", "🗓️ Agenda"])

with tab1:
    df_main = df[df['SECTOR'] == st.session_state.sector_activo] if st.session_state.sector_activo != "Todos" else df
    
    if not df_main.empty:
        nombres = sorted(df_main['COLABORADOR'].unique())
        cols = st.columns(4)
        for i, nom in enumerate(nombres):
            if cols[i%4].button(nom, key=f"btn_{nom}", type=("primary" if st.session_state.colaborador_activo == nom else "secondary")):
                st.session_state.colaborador_activo = nom
                st.rerun()

        st.divider()
        df_view = df_main[df_main['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_main
        total = len(df_view)
        ok = (df_view['ESTADO_NUM'] == 1).sum() if 'ESTADO_NUM' in df_view.columns else 0
        porc = (ok / total * 100) if total > 0 else 0
        
        st.metric(f"Cumplimiento de {st.session_state.colaborador_activo}", f"{porc:.1f}%")
        st.dataframe(df_view[['CURSO','ESTADO_NUM']], use_container_width=True, hide_index=True)

        if st.session_state.colaborador_activo != 'Todos' and "GEMINI_API_KEY" in st.secrets:
            with st.expander("🤖 Mentor de Formación IA - AUTOCIEL"):
                if st.button("Generar Plan Estratégico"):
                    with st.spinner("Gemini analizando cumplimiento para AUTOCIEL..."):
                        pendientes = df_view[df_view['ESTADO_NUM'] == 0]['CURSO'].tolist()
                        prompt = f"Eres el Director de Capacitación de AUTOCIEL. Analiza a {st.session_state.colaborador_activo} ({porc}% de avance). Pendientes: {pendientes}. Da una recomendación motivadora de 3 líneas."
                        
                        try:
                            respuesta = model.generate_content(prompt)
                            st.info(respuesta.text)
                            
                            df_plan_colab = df_planif_raw[df_planif_raw['COLABORADOR'] == st.session_state.colaborador_activo]
                            pdf_bytes = generar_pdf_binario(st.session_state.colaborador_activo, round(porc, 1), respuesta.text, df_plan_colab)
                            
                            st.download_button(
                                label="📥 DESCARGAR REPORTE AUTOCIEL (PDF)",
                                data=bytes(pdf_bytes),
                                file_name=f"Reporte_AUTOCIEL_{st.session_state.colaborador_activo}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        except: st.error("Error al conectar con la IA.")

with tab2:
    st.write("Visualización de cumplimiento en el tiempo para la meta 2026.")
    # (El resto del código de Gantt se mantiene igual)

with tab3:
    if not df_planif_raw.empty:
        df_cal = df_planif_raw.dropna(subset=['FECHA_DT']).copy()
        if st.session_state.colaborador_activo != "Todos":
            df_cal = df_cal[df_cal['COLABORADOR'] == st.session_state.colaborador_activo]
        
        events = [{"title": str(r.get('NOMBRE DEL CURSO', ''))[:20], "start": r['FECHA_DT'].strftime('%Y-%m-%d'), "backgroundColor": "#3788d8"} for _, r in df_cal.iterrows()]
        calendar(events=events, options={"locale": "es", "height": 600}, key="calendar_autociel")
