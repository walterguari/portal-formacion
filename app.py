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
import io

# --- CONFIGURACIÓN DE IA (SECRETS) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Falta la GEMINI_API_KEY en los Secrets de Streamlit.")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 8px; font-weight: bold; margin-bottom: 5px; height: 45px;}
    [data-testid="stSidebar"] img {display: block; margin: 0 auto 20px auto;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---
def generar_pdf_formacion(colaborador, sector, avance, pendientes, analisis_ia):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Reporte de Formación 2026", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Colaborador: {colaborador}", ln=True, align='C')
    pdf.ln(10)
    
    # Datos de progreso
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, " Estado Actual", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Sector: {sector}", ln=True)
    pdf.cell(0, 8, f"Porcentaje de cumplimiento: {avance}%", ln=True)
    pdf.ln(5)
    
    # Pendientes
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " Cursos Pendientes:", ln=True)
    pdf.set_font("Arial", '', 10)
    if pendientes:
        for curso in pendientes:
            pdf.cell(0, 7, f"- {curso}", ln=True)
    else:
        pdf.cell(0, 7, "¡Felicidades! No hay cursos pendientes.", ln=True)
    pdf.ln(10)
    
    # Análisis IA
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 10, " Recomendación del Mentor IA (Gemini):", ln=True, fill=True)
    pdf.set_font("Arial", 'I', 11)
    # Reemplazar caracteres no latin-1 para evitar errores en FPDF
    clean_text = analisis_ia.replace('’', "'").replace('–', '-').encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, clean_text)
    
    return pdf.output(dest='S')

# --- LOGIN ---
if 'acceso_concedido' not in st.session_state:
    st.session_state.acceso_concedido = False

if not st.session_state.acceso_concedido:
    st.markdown("<h2 style='text-align: center;'>🔒 Portal Privado</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        clave = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary"):
            if clave == "CENOA2026":
                st.session_state.acceso_concedido = True
                st.rerun()
            else:
                st.error("🚫 Clave incorrecta.")
    st.stop()

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID_GENERAL = "245378054"
GID_PLANIF = "829571230"

URL_GENERAL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_GENERAL}"
URL_PLANIF = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PLANIF}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL_GENERAL)
        df.columns = df.columns.str.strip().str.upper()
        col_map = {'SECTOR':'SECTOR', 'CARGO':'CARGO', 'ROL':'CARGO', 'COLABORADOR':'COLABORADOR', 'NOMBRE':'COLABORADOR', 'CURSO':'CURSO', 'FORMACION':'CURSO', 'NIVEL':'NIVEL'}
        # Renombrado dinámico
        for c in df.columns:
            for k, v in col_map.items():
                if k in c: df.rename(columns={c: v}, inplace=True)
        
        if 'ESTADO_NUM' not in df.columns:
            # Buscar columna de estado/capacitado
            for c in df.columns:
                if 'CAPACITA' in c or 'ESTADO' in c:
                    df['ESTADO_NUM'] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
        
        df = df.loc[:, ~df.columns.duplicated()]
        for c in ['SECTOR', 'CARGO', 'COLABORADOR', 'NIVEL']:
            if c in df.columns: df[c] = df[c].astype(str).str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_planif():
    try:
        df_p = pd.read_csv(URL_PLANIF)
        df_p.columns = df_p.columns.str.strip().str.upper()
        if 'FECHA' in df_p.columns:
            df_p['FECHA_DT'] = pd.to_datetime(df_p['FECHA'], dayfirst=True, errors='coerce')
        return df_p.fillna("")
    except: return pd.DataFrame()

df = load_data()
df_planif_raw = load_planif()

# --- ESTADO DE SESIÓN ---
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'
if 'analisis_ia_cache' not in st.session_state: st.session_state.analisis_ia_cache = ""

# --- BARRA LATERAL ---
st.sidebar.title("🏢 Navegación")
if st.sidebar.button("VER TODO", type=("primary" if st.session_state.sector_activo == "Todos" else "secondary")):
    st.session_state.update({"sector_activo": "Todos", "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos", "analisis_ia_cache": ""})
    st.rerun()

for sec in sorted(df['SECTOR'].unique()):
    if st.sidebar.button(sec, type=("primary" if st.session_state.sector_activo == sec else "secondary")):
        st.session_state.update({"sector_activo": sec, "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos", "analisis_ia_cache": ""})
        st.rerun()

# --- FILTRADO ---
df_roles = df[df['SECTOR'] == st.session_state.sector_activo] if st.session_state.sector_activo != "Todos" else df
roles = ["Todos"] + sorted(df_roles['CARGO'].unique().tolist())
sel_rol = st.sidebar.selectbox("Filtrar Puesto:", roles, index=roles.index(st.session_state.ultimo_cargo_sel) if st.session_state.ultimo_cargo_sel in roles else 0)

if sel_rol != st.session_state.ultimo_cargo_sel:
    st.session_state.ultimo_cargo_sel = sel_rol
    st.session_state.colaborador_activo = 'Todos'
    st.session_state.analisis_ia_cache = ""
    st.rerun()

df_main = df_roles[df_roles['CARGO'] == sel_rol] if sel_rol != "Todos" else df_roles

# --- TABS ---
st.title(f"🎓 {st.session_state.sector_activo} / {sel_rol}")
tab1, tab2, tab3 = st.tabs(["📊 Indicadores", "📅 Gantt", "🗓️ Agenda"])

with tab1:
    if not df_main.empty:
        # Selector de Colaboradores
        nombres = sorted(df_main['COLABORADOR'].unique())
        cols = st.columns(4)
        if cols[0].button("👥 TODOS", type=("primary" if st.session_state.colaborador_activo == 'Todos' else "secondary")):
            st.session_state.colaborador_activo = 'Todos'
            st.session_state.analisis_ia_cache = ""
            st.rerun()
            
        for i, nom in enumerate(nombres):
            if cols[(i+1)%4].button(nom, key=f"btn_{nom}", type=("primary" if st.session_state.colaborador_activo == nom else "secondary")):
                st.session_state.colaborador_activo = nom
                st.session_state.analisis_ia_cache = ""
                st.rerun()

        st.divider()
        
        # Datos visualizados
        df_view = df_main[df_main['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_main
        total = len(df_view)
        ok = (df_view['ESTADO_NUM'] == 1).sum() if 'ESTADO_NUM' in df_view.columns else 0
        porc = (ok / total * 100) if total > 0 else 0
        
        c1, c2 = st.columns([1, 2])
        with c1:
            fig = go.Figure(go.Indicator(mode="gauge+number", value=porc, gauge={'axis':{'range':[None,100]}, 'bar':{'color': "green" if porc==100 else "orange"}}))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.subheader(f"Resumen: {st.session_state.colaborador_activo}")
            st.write(f"Cursos completados: {ok} de {total}")
            st.dataframe(df_view[['CURSO', 'NIVEL', 'ESTADO_NUM']], hide_index=True, use_container_width=True)

        # SECCIÓN IA Y PDF
        if st.session_state.colaborador_activo != 'Todos':
            with st.expander("🤖 Mentor de Formación IA"):
                if st.button("Generar Plan Estratégico con Gemini"):
                    with st.spinner("Analizando perfil técnico..."):
                        pendientes_list = df_view[df_view['ESTADO_NUM'] == 0]['CURSO'].tolist()
                        prompt = f"Eres experto en capacitación automotriz. El colaborador {st.session_state.colaborador_activo} tiene un avance del {porc}% en {st.session_state.sector_activo}. Pendientes: {pendientes_list}. Da una recomendación técnica y motivadora de 3 líneas para el estándar 2026."
                        try:
                            res = model.generate_content(prompt)
                            st.session_state.analisis_ia_cache = res.text
                        except: st.error("Error de conexión con IA.")
                
                if st.session_state.analisis_ia_cache:
                    st.info(st.session_state.analisis_ia_cache)
                    
                    # Generación de PDF
                    pdf_data = generar_pdf_formacion(
                        st.session_state.colaborador_activo,
                        st.session_state.sector_activo,
                        round(porc, 1),
                        df_view[df_view['ESTADO_NUM'] == 0]['CURSO'].tolist(),
                        st.session_state.analisis_ia_cache
                    )
                    
                    st.download_button(
                        label="📥 Descargar Reporte PDF",
                        data=pdf_data,
                        file_name=f"Reporte_{st.session_state.colaborador_activo}.pdf",
                        mime="application/pdf"
                    )

with tab2:
    # Lógica de Gantt (simplificada)
    fecha_fin = datetime(2026, 3, 20)
    dias_r = (fecha_fin - datetime.now()).days
    if dias_r > 0:
        df_p = df_main[df_main['ESTADO_NUM'] == 0]
        if not df_p.empty:
            df_g = []
            for i, row in enumerate(df_p.head(20).itertuples()): # Limitar a 20 para visualización
                df_g.append(dict(Task=row.COLABORADOR[:10], Start=(datetime.now() + timedelta(days=i*2)).strftime('%Y-%m-%d'), Finish=(datetime.now() + timedelta(days=(i*2)+2)).strftime('%Y-%m-%d'), Resource=row.CARGO))
            fig_g = ff.create_gantt(df_g, index_col='Resource', show_colorbar=True, group_tasks=True)
            st.plotly_chart(fig_g, use_container_width=True)
    else: st.warning("Fecha límite alcanzada.")

with tab3:
    if not df_planif_raw.empty and 'FECHA_DT' in df_planif_raw.columns:
        df_cal = df_planif_raw.dropna(subset=['FECHA_DT'])
        eventos = []
        for _, r in df_cal.iterrows():
            eventos.append({"title": f"{r['COLABORADOR'][:10]} | {r.get('NOMBRE DEL CURSO', 'Curso')[:15]}", "start": r['FECHA_DT'].strftime('%Y-%m-%d'), "backgroundColor": "#3788d8"})
        calendar(events=eventos, options={"locale": "es", "height": 600})
    else: st.info("No hay eventos programados en la hoja de Planificación.")
