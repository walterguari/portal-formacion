import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Portal Formación", 
    page_icon="🎓", 
    layout="wide"
)

# 2. CONEXIÓN CON GOOGLE SHEETS
# Reemplaza esto si cambias de hoja
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID = "245378054" # ID de la pestaña "Avance de formacion"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60) # Actualiza cada 60 segundos
def cargar_datos():
    try:
        df = pd.read_csv(URL)
        # Limpiamos los nombres de las columnas (quitamos espacios y mayúsculas excesivas)
        df.columns = df.columns.str.strip().str.title()
        return df
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

# Cargar los datos
df = cargar_datos()

# 3. INTERFAZ PRINCIPAL
st.title("🎓 Tablero de Control: Avance de Formación")

if df.empty:
    st.warning("No se pudieron cargar datos. Revisa que la hoja de Google Sheets sea pública (Lectura).")
else:
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Filtros")
    
    # Intentamos detectar columnas clave automáticamente
    cols = df.columns.tolist()
    
    # Filtro 1: Posiblemente "Colaborador" o "Nombre"
    col_persona = next((c for c in cols if "NOMBRE" in c.upper() or "COLABORADOR" in c.upper()), cols[0])
    filtro_persona = st.sidebar.multiselect("Filtrar por Persona", df[col_persona].unique())
    
    # Filtro 2: Posiblemente "Cargo" o "Puesto"
    col_cargo = next((c for c in cols if "CARGO" in c.upper() or "PUESTO" in c.upper()), None)
    if col_cargo:
        filtro_cargo = st.sidebar.multiselect("Filtrar por Cargo", df[col_cargo].unique())
    
    # Filtro 3: Estado o Avance
    col_estado = next((c for c in cols if "ESTADO" in c.upper() or "AVANCE" in c.upper() or "STATUS" in c.upper()), None)
    if col_estado:
        filtro_estado = st.sidebar.multiselect("Filtrar por Estado", df[col_estado].unique())

    # --- APLICAR FILTROS ---
    df_filtrado = df.copy()
    if filtro_persona:
        df_filtrado = df_filtrado[df_filtrado[col_persona].isin(filtro_persona)]
    if col_cargo and filtro_cargo:
        df_filtrado = df_filtrado[df_filtrado[col_cargo].isin(filtro_cargo)]
    if col_estado and filtro_estado:
        df_filtrado = df_filtrado[df_filtrado[col_estado].isin(filtro_estado)]

    # --- KPI (INDICADORES) ---
    total_registros = len(df_filtrado)
    st.markdown("### 📊 Resumen General")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registros", total_registros)
    
    # Si tenemos columna de estado, mostramos métrica de completados
    if col_estado:
        # Buscamos palabras clave de éxito como "OK", "Realizado", "Completo", "100%"
        completados = df_filtrado[df_filtrado[col_estado].astype(str).str.contains("Realizado|OK|Completo|100", case=False, na=False)]
        qty_ok = len(completados)
        porcentaje = (qty_ok / total_registros * 100) if total_registros > 0 else 0
        c2.metric("✅ Completados", f"{qty_ok}")
        c3.metric("📈 % Avance", f"{porcentaje:.1f}%")
        st.progress(int(porcentaje))

    st.divider()

    # --- TABLA DE DATOS ---
    st.subheader("📋 Detalle de Cursos")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    # --- GRÁFICOS SIMPLES ---
    if col_estado:
        st.subheader("📊 Gráficos")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Gráfico de Torta por Estado
            conteo_estados = df_filtrado[col_estado].value_counts().reset_index()
            conteo_estados.columns = ['Estado', 'Cantidad']
            fig_pie = px.pie(conteo_estados, values='Cantidad', names='Estado', title="Distribución por Estado", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_g2:
            # Gráfico de Barras por Cargo (si existe)
            if col_cargo:
                conteo_cargo = df_filtrado.groupby(col_cargo)[col_estado].count().reset_index()
                conteo_cargo.columns = ['Cargo', 'Cantidad']
                fig_bar = px.bar(conteo_cargo, x='Cargo', y='Cantidad', title="Cursos por Cargo")
                st.plotly_chart(fig_bar, use_container_width=True)
