import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px # <-- Librería moderna para el Gantt (Reemplaza a figure_factory)
from datetime import datetime, timedelta
import math
from streamlit_calendar import calendar
import google.generativeai as genai

# --- CONFIGURACIÓN DE IA (SECRETS) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Falta la GEMINI_API_KEY en los Secrets de Streamlit.")

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS ---
st.markdown("""
<style>
    div.stButton > button {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%; 
        border-radius: 8px; 
        font-weight: bold; 
        margin-bottom: 5px; 
        min-height: 55px; 
        height: auto; 
        white-space: pre-wrap; 
        line-height: 1.2;
    }
    
    [data-testid="stSidebar"] div.stButton > button {
        min-height: 45px;
        font-size: 0.75rem !important;
        padding: 5px !important;
    }

    [data-testid="stSidebar"] img {display: block; margin: 0 auto 20px auto;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4CAF50; }
    .fc .fc-daygrid-day-frame { min-height: 120px !important; }
    .fc-daygrid-event { white-space: normal !important; align-items: flex-start !important; font-size: 0.8em !important; cursor: pointer !important; }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if 'acceso_concedido' not in st.session_state:
    st.session_state.acceso_concedido = False

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
        for c in df.columns:
            if c in ["TIPO DE CAPACITACIÓN", "TIPO DE CAPACITACION"]: col_map[c] = 'TIPO_CAPACITACION'
            elif c == "MARCA": col_map[c] = 'MARCA'
            elif c == "SECTOR": col_map[c] = 'SECTOR'
            elif c == "CARGO": col_map[c] = 'CARGO'
            elif c in ["CÓDIGO", "CODIGO"]: col_map[c] = 'CODIGO'
            elif c == "NOMBRE DEL COLABORADOR": col_map[c] = 'COLABORADOR'
            elif c == "FORMACION": col_map[c] = 'CURSO'
            elif c == "TIPO DE CURSO": col_map[c] = 'TIPO_CURSO'
            elif c == "NIVELES": col_map[c] = 'NIVEL'
            elif c == "CAPACITACIONES": col_map[c] = 'ESTADO_NUM'
            elif c == "ESTADO DE CAPACITACIONES": col_map[c] = 'ESTADO_TEXTO'
        
        df = df.rename(columns=col_map)
        df = df.loc[:, ~df.columns.duplicated()]
        
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        else:
            df['ESTADO_NUM'] = 0

        cols_limpieza = ['SECTOR', 'CARGO', 'COLABORADOR', 'NIVEL', 'MARCA', 'TIPO_CURSO', 'TIPO_CAPACITACION', 'CODIGO']
        for c in cols_limpieza:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.upper()
                
        return df
    except Exception as e:
        st.error(f"Error en Datos Generales: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_planificacion():
    try:
        df_p = pd.read_csv(URL_PLANIF)
        df_p.columns = df_p.columns.str.strip().str.upper()
        
        # Mapeo super robusto para los encabezados de la Planificación
        col_curso = next((c for c in df_p.columns if "TÍTULO" in c or "TITULO" in c), None)
        col_fecha_ini = next((c for c in df_p.columns if "COMIENZO" in c), None)
        col_fecha_fin = next((c for c in df_p.columns if "FINALIZACIÓN" in c or "FINALIZACION" in c), None)
        
        col_ape = next((c for c in df_p.columns if "APELLIDOS" in c), None)
        col_nom = next((c for c in df_p.columns if "NOMBRE" in c and "USUARIO" in c), None)
        
        # Unir apellidos y nombres
        if col_ape and col_nom:
            df_p['COLABORADOR'] = df_p[col_ape].astype(str).str.strip() + " " + df_p[col_nom].astype(str).str.strip()
        elif col_nom:
            df_p['COLABORADOR'] = df_p[col_nom].astype(str).str.strip()
        elif col_ape:
            df_p['COLABORADOR'] = df_p[col_ape].astype(str).str.strip()
        else:
            df_p['COLABORADOR'] = "S/D"

        df_p['NOMBRE_DEL_CURSO'] = df_p[col_curso] if col_curso else "Curso no especificado"
        
        # Parseo de fechas (formato esperado día/mes/año hora:min)
        if col_fecha_ini:
            df_p['FECHA_DT'] = pd.to_datetime(df_p[col_fecha_ini], dayfirst=True, errors='coerce')
        if col_fecha_fin:
            df_p['FECHA_FIN_DT'] = pd.to_datetime(df_p[col_fecha_fin], dayfirst=True, errors='coerce')

        return df_p
    except Exception as e:
        st.error(f"Error en Planificación (Agenda): {e}")
        return pd.DataFrame()

df_raw = load_data_general()
df_planif_raw = load_planificacion()

if df_raw.empty or 'SECTOR' not in df_raw.columns:
    st.error("⚠️ Error de formato en la hoja de cálculo general.")
    st.stop()

# --- ESTADO DE SESIÓN ---
if 'marca_activa' not in st.session_state: st.session_state.marca_activa = "TODAS"
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'tipo_cap_activo' not in st.session_state: st.session_state.tipo_cap_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'
if 'nivel_seleccionado' not in st.session_state: st.session_state.nivel_seleccionado = 'Ambos'

# --- BARRA LATERAL ---
st.sidebar.title("🏷️ Filtros Principales")

marcas = ["TODAS"] + sorted([m for m in df_raw['MARCA'].unique() if str(m) != "NAN"]) if 'MARCA' in df_raw.columns else ["TODAS"]
sel_marca = st.sidebar.selectbox("Seleccionar Marca:", marcas, index=marcas.index(st.session_state.marca_activa) if st.session_state.marca_activa in marcas else 0)

if sel_marca != st.session_state.marca_activa:
    st.session_state.update({"marca_activa": sel_marca, "sector_activo": "Todos", "tipo_cap_activo": "Todos", "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos"})
    st.rerun()

df = df_raw.copy()
if st.session_state.marca_activa != "TODAS":
    df = df[df['MARCA'] == st.session_state.marca_activa]

st.sidebar.divider()
st.sidebar.title("🏢 Sectores")
if st.sidebar.button("VER TODO", type=("primary" if st.session_state.sector_activo == "Todos" else "secondary")):
    st.session_state.update({"sector_activo": "Todos", "tipo_cap_activo": "Todos", "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos"})
    st.rerun()

for sec in sorted(df['SECTOR'].unique()):
    df_s = df[df['SECTOR'] == sec]
    total_sec = len(df_s)
    realizados = (df_s['ESTADO_NUM'] == 1).sum() if 'ESTADO_NUM' in df_s.columns else 0
    avance = (realizados / total_sec * 100) if total_sec > 0 else 0
    
    color_sidebar = "#ef5350" if avance < 50 else "#ffa726" if avance < 90 else "#66bb6a"
    
    if 'TIPO_CAPACITACION' in df_s.columns:
        df_obl = df_s[df_s['TIPO_CAPACITACION'] == 'OBLIGATORIO']
        df_opt = df_s[df_s['TIPO_CAPACITACION'] != 'OBLIGATORIO']
        
        tot_obl = len(df_obl)
        av_obl = ((df_obl['ESTADO_NUM'] == 1).sum() / tot_obl * 100) if tot_obl > 0 else 0
        
        tot_opt = len(df_opt)
        av_opt = ((df_opt['ESTADO_NUM'] == 1).sum() / tot_opt * 100) if tot_opt > 0 else 0
        
        c_dot, c_sec, c_obl, c_opt = st.sidebar.columns([0.5, 3.5, 2.5, 2.5])
        
        c_dot.markdown(f"<div style='margin-top:15px; width:12px; height:12px; background-color:{color_sidebar}; border-radius:50%;'></div>", unsafe_allow_html=True)
        
        if c_sec.button(f"{sec}\n({avance:.0f}%)", key=f"sidebar_{sec}", type=("primary" if st.session_state.sector_activo == sec and st.session_state.tipo_cap_activo == "Todos" else "secondary")):
            st.session_state.update({"sector_activo": sec, "tipo_cap_activo": "Todos", "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos"})
            st.rerun()
            
        tipo_obl_activo = (st.session_state.sector_activo == sec and st.session_state.tipo_cap_activo == "OBLIGATORIO")
        if c_obl.button(f"Oblig.\n{av_obl:.0f}%", key=f"btn_obl_{sec}", type="primary" if tipo_obl_activo else "secondary"):
            st.session_state.update({"sector_activo": sec, "tipo_cap_activo": "OBLIGATORIO", "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos"})
            st.rerun()
            
        tipo_opt_activo = (st.session_state.sector_activo == sec and st.session_state.tipo_cap_activo == "NO OBLIGATORIO")
        if c_opt.button(f"No Obl.\n{av_opt:.0f}%", key=f"btn_opt_{sec}", type="primary" if tipo_opt_activo else "secondary"):
            st.session_state.update({"sector_activo": sec, "tipo_cap_activo": "NO OBLIGATORIO", "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos"})
            st.rerun()
    else:
        c_dot, c_sec = st.sidebar.columns([1, 9])
        c_dot.markdown(f"<div style='margin-top:15px; width:12px; height:12px; background-color:{color_sidebar}; border-radius:50%;'></div>", unsafe_allow_html=True)
        if c_sec.button(f"{sec}\n({avance:.0f}%)", key=f"sidebar_{sec}", type=("primary" if st.session_state.sector_activo == sec else "secondary")):
            st.session_state.update({"sector_activo": sec, "tipo_cap_activo": "Todos", "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos"})
            st.rerun()

# --- LÓGICA DE FILTRADO ---
df_roles = df[df['SECTOR'] == st.session_state.sector_activo] if st.session_state.sector_activo != "Todos" else df

if 'TIPO_CAPACITACION' in df_roles.columns:
    if st.session_state.tipo_cap_activo == "OBLIGATORIO":
        df_roles = df_roles[df_roles['TIPO_CAPACITACION'] == 'OBLIGATORIO']
    elif st.session_state.tipo_cap_activo == "NO OBLIGATORIO":
        df_roles = df_roles[df_roles['TIPO_CAPACITACION'] != 'OBLIGATORIO']

st.sidebar.title("👮 Puestos")
roles = ["Todos"] + sorted(df_roles['CARGO'].unique().tolist()) if 'CARGO' in df_roles.columns else ["Todos"]
sel_rol = st.sidebar.selectbox("Seleccionar puesto:", roles, index=roles.index(st.session_state.ultimo_cargo_sel) if st.session_state.ultimo_cargo_sel in roles else 0)

if sel_rol != st.session_state.ultimo_cargo_sel:
    st.session_state.ultimo_cargo_sel = sel_rol
    st.session_state.colaborador_activo = 'Todos'
    st.rerun()

if st.sidebar.button("🔒 Salir"):
    st.session_state.acceso_concedido = False
    st.rerun()

df_main = df_roles[df_roles['CARGO'] == sel_rol] if sel_rol != "Todos" else df_roles

txt_tipo = f" > {st.session_state.tipo_cap_activo}" if st.session_state.tipo_cap_activo != "Todos" else ""
st.title(f"🎓 Gestión de Formación: {st.session_state.marca_activa} > {st.session_state.sector_activo}{txt_tipo}")

tab1, tab2, tab3 = st.tabs(["📊 Tablero de Control", "📅 Planificador & Gantt", "🗓️ Agenda Interactiva"])

with tab1:
    if not df_main.empty:
        st.write("### ⚖️ Nivel de Formación")
        niveles = ["Ambos", "NIVEL 1", "NIVEL 2"]
        sel_nivel = st.selectbox("Ver indicadores de:", niveles, index=niveles.index(st.session_state.nivel_seleccionado))
        if sel_nivel != st.session_state.nivel_seleccionado:
            st.session_state.nivel_seleccionado = sel_nivel
            st.rerun()

        st.divider()

        if st.session_state.nivel_seleccionado != 'Ambos':
            df_con_nivel = df_main[df_main['NIVEL'] == st.session_state.nivel_seleccionado]
        else:
            df_con_nivel = df_main

        nombres = sorted(df_con_nivel['COLABORADOR'].unique())
        cols = st.columns(4)
        
        if cols[0].button(f"👥 Ver Todo ({len(nombres)})", type=("primary" if st.session_state.colaborador_activo == 'Todos' else "secondary")):
             st.session_state.colaborador_activo = 'Todos'
             st.rerun()
        
        for i, nom in enumerate(nombres):
            df_indiv = df_con_nivel[df_con_nivel['COLABORADOR'] == nom]
            t_ind = len(df_indiv)
            ok_ind = (df_indiv['ESTADO_NUM'] == 1).sum() if 'ESTADO_NUM' in df_indiv.columns else 0
            p_ind = (ok_ind / t_ind * 100) if t_ind > 0 else 0
            emoji = "🟢" if p_ind == 100 else "🔴" if p_ind < 50 else "🟠"
            
            cod = ""
            if 'CODIGO' in df_indiv.columns and not df_indiv['CODIGO'].empty:
                val = df_indiv['CODIGO'].iloc[0]
                if pd.notna(val) and val != 'NAN':
                    cod = f"\nCód: {val}"
            
            label_boton = f"{emoji} {nom} ({p_ind:.0f}%){cod}"
            
            if cols[(i+1)%4].button(label_boton, key=f"btn_{i}", type=("primary" if st.session_state.colaborador_activo == nom else "secondary")):
                st.session_state.colaborador_activo = nom
                st.rerun()
        
        st.divider()
        
        if st.session_state.colaborador_activo != 'Todos' and st.session_state.colaborador_activo not in nombres:
            st.session_state.colaborador_activo = 'Todos'
            st.rerun()

        df_view = df_con_nivel[df_con_nivel['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_con_nivel
        
        total = len(df_view)
        ok = (df_view['ESTADO_NUM'] == 1).sum() if 'ESTADO_NUM' in df_view.columns else 0
        porc = (ok / total * 100) if total > 0 else 0
        
        codigo_copiable = ""
        if st.session_state.colaborador_activo != 'Todos':
            if 'CODIGO' in df_view.columns and not df_view['CODIGO'].empty:
                val = df_view['CODIGO'].iloc[0]
                if pd.notna(val) and val != 'NAN' and val != "":
                    codigo_copiable = f" &nbsp;|&nbsp; 📋 <b>Código:</b> <code style='font-size: 1.1em; color: #d32f2f; background-color: #ffebee; padding: 2px 6px; border-radius: 4px;'>{val}</code>"
        
        st.markdown(f"<div style='background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid {'green' if porc==100 else 'orange' if porc>=50 else 'red'};'><h4>Avance {st.session_state.nivel_seleccionado}: {porc:.1f}% ({st.session_state.colaborador_activo}){codigo_copiable}</h4></div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            fig = go.Figure(go.Indicator(mode="gauge+number", value=porc, gauge={'axis':{'range':[None,100]}, 'bar':{'color': 'green' if porc==100 else 'orange'}}))
            fig.update_layout(height=250, margin=dict(t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.info(f"Completado: **{ok}** de **{total}** registros.")
            
            cols_tabla = ['CODIGO', 'TIPO_CAPACITACION', 'MARCA', 'COLABORADOR', 'CURSO', 'TIPO_CURSO', 'ESTADO_TEXTO', 'NIVEL']
            cols_visibles = [c for c in cols_tabla if c in df_view.columns]
            st.dataframe(df_view[cols_visibles], use_container_width=True, hide_index=True)

        if st.session_state.colaborador_activo != 'Todos' and "GEMINI_API_KEY" in st.secrets:
            with st.expander("🤖 Análisis Inteligente de Formación"):
                if st.button("Generar Recomendación con IA"):
                    with st.spinner("Analizando cumplimiento..."):
                        pendientes = df_view[df_view['ESTADO_NUM'] == 0]['CURSO'].tolist()
                        status_text = "al 100%" if porc == 100 else f"al {porc:.1f}%"
                        
                        prompt = f"""
                        Eres un experto en Capacitación Automotriz de Autolux/Cenoa.
                        Analiza al colaborador {st.session_state.colaborador_activo} de la marca {st.session_state.marca_activa}.
                        Estado: {status_text}.
                        Pendientes: {', '.join(pendientes) if pendientes else 'Ninguno'}.
                        Tarea: Resumen de 3 líneas motivador y técnico sobre prioridades 2026.
                        """
                        try:
                            respuesta = model.generate_content(prompt)
                            st.info(respuesta.text)
                        except Exception as e:
                            st.error("Error al conectar con Gemini.")

with tab2:
    fecha_fin = datetime(2026, 12, 20)
    fecha_hoy = datetime.now()
    dias_restantes = (fecha_fin - fecha_hoy).days
    
    st.subheader(f"📅 Planificador (Meta: {fecha_fin.strftime('%d/%m/%Y')})")
    
    if dias_restantes > 0:
        dias_h = sum(1 for i in range(dias_restantes + 1) if (fecha_hoy + timedelta(i)).weekday() < 5)
        semanas_r = max(1, math.ceil(dias_h / 5))
        df_pend = df_main[df_main['ESTADO_NUM'] == 0]
        df_plan = df_pend[df_pend['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_pend
        
        if not df_plan.empty:
            ritmo = math.ceil(len(df_plan) / semanas_r)
            st.metric("Meta Semanal Requerida", f"{ritmo} curso(s) por semana", f"Quedan {semanas_r} semanas hábiles")
            
            df_gantt = []
            for i, row in enumerate(df_plan.itertuples()):
                n_s = (i // ritmo)
                ini = fecha_hoy + timedelta(weeks=n_s)
                fin = ini + timedelta(days=4)
                
                colab_str = str(getattr(row, 'COLABORADOR', 'S/D'))[:15]
                nivel_str = str(getattr(row, 'NIVEL', 'N/A'))
                
                df_gantt.append(dict(Task=colab_str, Start=ini.strftime('%Y-%m-%d'), Finish=fin.strftime('%Y-%m-%d'), Resource=nivel_str))
                
            if df_gantt:
                df_g = pd.DataFrame(df_gantt)
                # ¡AQUÍ ESTÁ LA SOLUCIÓN DEL ERROR! Usamos plotly.express (px) 
                fig_g = px.timeline(df_g, x_start="Start", x_end="Finish", y="Task", color="Resource")
                fig_g.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_g, use_container_width=True)
        else:
            st.success("🎉 ¡Objetivo cumplido! No hay cursos pendientes.")
    else:
        st.warning("⚠️ Fecha límite superada.")

with tab3:
    st.subheader("🗓️ Agenda de Cursos Interactiva")
    
    if df_planif_raw.empty:
        st.warning("⚠️ No hay datos en Planificación. Verifica que el archivo de Sheets tenga las columnas correctas.")
    elif 'FECHA_DT' not in df_planif_raw.columns:
        st.error("❌ No se encontraron fechas válidas en la Planificación.")
    else:
        df_cal = df_planif_raw[df_planif_raw['FECHA_DT'].notna()].copy()
        
        nombres_planif = ["Todos"] + sorted([str(x) for x in df_cal['COLABORADOR'].unique() if str(x) != "nan" and str(x) != "S/D"])
        busqueda = st.selectbox("🔍 Filtrar agenda por colaborador:", nombres_planif)
        
        if busqueda != "Todos":
            df_cal = df_cal[df_cal['COLABORADOR'] == busqueda]
            
        calendar_events = []
        for _, row in df_cal.iterrows():
            try:
                nombre_curso = str(row.get('NOMBRE_DEL_CURSO', 'Curso'))
                colab = str(row.get('COLABORADOR', 'S/D'))
                
                # Para el color de presencial vs virtual
                tipo_info = nombre_curso.upper()
                color = "#28a745" if "PRESENCIAL" in tipo_info else "#3788d8"
                
                fecha_inicio_iso = row['FECHA_DT'].isoformat()
                hora_texto = row['FECHA_DT'].strftime('%H:%M')
                
                event = {
                    "title": f"{colab[:15]} | {nombre_curso[:25]}",
                    "start": fecha_inicio_iso,
                    "backgroundColor": color,
                    "allDay": False,
                    "extendedProps": {
                        "curso": nombre_curso,
                        "obs": "Registrado en Planificación"
                    }
                }
                
                if 'FECHA_FIN_DT' in row and pd.notna(row['FECHA_FIN_DT']):
                    event["end"] = row['FECHA_FIN_DT'].isoformat()
                    hora_texto += f" - {row['FECHA_FIN_DT'].strftime('%H:%M')}"
                
                event["extendedProps"]["horario"] = hora_texto
                
                calendar_events.append(event)
            except Exception as loop_e:
                continue

        cal_key = f"calendar_{st.session_state.marca_activa}_{busqueda}_{len(calendar_events)}"
        state = calendar(events=calendar_events, options={"locale": "es", "height": 600, "timeZone": "local"}, key=cal_key)
        
        if state.get("eventClick"):
            ev = state["eventClick"]["event"]
            st.markdown("---")
            st.info(f"📌 **Curso:** {ev['extendedProps']['curso']}")
            st.write(f"⌚ **Horario:** {ev['extendedProps']['horario']}")
            st.write(f"📝 **Obs:** {ev['extendedProps']['obs']}")
