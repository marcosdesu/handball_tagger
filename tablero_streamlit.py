import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from scipy.ndimage import gaussian_filter
from streamlit_autorefresh import st_autorefresh
import time
from matplotlib.ticker import MaxNLocator

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Tablero Handball Live", layout="wide")
st.title("Análisis Táctico 🤾‍♀️")

IMAGEN_PORTERIA = 'NS_Goal_handball.png'
IMAGEN_CANCHA = 'NS_ui_Balonmano_BL_V_T.jpg'

# ==========================================
# 🚨 ENLACE DE TU GOOGLE SHEET 
# ==========================================
URL_USUARIO = "https://docs.google.com/spreadsheets/d/1PFpl8nYFD1-It3I5ArlY1rNPPDHnYARttgbH3bOZyQ0/edit?usp=sharing"

def obtener_url_csv(url):
    if "/edit" in url:
        return url.split("/edit")[0] + "/export?format=csv"
    elif "pubhtml" in url:
        return url.replace("pubhtml", "pub?output=csv")
    elif "/pub?" in url and "output=csv" not in url:
        return url + "&output=csv"
    return url

URL_OFICIAL = obtener_url_csv(URL_USUARIO)

# ==========================================
# 0. AUTO-REFRESCO
# ==========================================
st_autorefresh(interval=4000, limit=None, key="data_refresh")

# ==========================================
# 1. CONEXIÓN A DATOS 
# ==========================================
def load_data():
    try:
        conector = "&" if "?" in URL_OFICIAL else "?"
        url_nocache = f"{URL_OFICIAL}{conector}_t={int(time.time())}"
        df_temp = pd.read_csv(url_nocache)
        df_temp = df_temp.dropna(how='all')
        return df_temp
    except Exception as e:
        return pd.DataFrame(columns=['Partido', 'Tiempo', 'Periodo', 'Equipo', 'Jugador', 'Fase', 'Resultado', 'Detalle', 'Lado', 'Coord Lado', 'Zona', 'Coord Porteria'])

df_vivo = load_data()

# ==========================================
# 2. FILTROS EN BARRA LATERAL (Sin selector de partido)
# ==========================================
st.sidebar.header("Filtros del Partido")

if not df_vivo.empty:
    partidos_validos = df_vivo['Partido'].dropna().unique().tolist()
    partido_actual = partidos_validos[-1] if partidos_validos else "Sin Datos"
    
    lista_equipos = ['Todos'] + [str(x) for x in df_vivo['Equipo'].dropna().unique()]
    lista_fases = ['Todas'] + [str(x) for x in df_vivo['Fase'].dropna().unique()]
    lista_resultados = ['Todos'] + [str(x) for x in df_vivo['Resultado'].dropna().unique()]
    lista_lados = ['Todos'] + [str(x) for x in df_vivo['Lado'].dropna().unique()]
    jugadores_validos = [str(x) for x in df_vivo['Jugador'].dropna().unique() if str(x) not in ['nan', 'N/A', '']]
    lista_jugadores = ['Todos'] + sorted(jugadores_validos)
else:
    partido_actual = "Sin Datos"
    lista_equipos, lista_fases, lista_resultados, lista_lados, lista_jugadores = ['Todos'], ['Todas'], ['Todos'], ['Todos'], ['Todos']

st.sidebar.markdown(f"**🏆 Partido Actual:** {partido_actual}")
st.sidebar.divider()

equipo_sel = st.sidebar.selectbox("1. ¿Quién ataca?", lista_equipos)
jugador_sel = st.sidebar.selectbox("2. Scouting Individual (Jugador)", lista_jugadores)
fase_sel = st.sidebar.selectbox("3. Fase de Juego", lista_fases)
resultado_sel = st.sidebar.selectbox("4. ¿Qué pasó?", lista_resultados)
lado_sel = st.sidebar.selectbox("5. Lado de la Cancha", lista_lados)

df = df_vivo.copy()
if not df.empty and partido_actual != "Sin Datos":
    df = df[df['Partido'].astype(str) == partido_actual]
    if equipo_sel != 'Todos': df = df[df['Equipo'] == equipo_sel]
    if jugador_sel != 'Todos': df = df[df['Jugador'].astype(str) == jugador_sel]
    if fase_sel != 'Todas': df = df[df['Fase'] == fase_sel]
    if resultado_sel != 'Todos': df = df[df['Resultado'] == resultado_sel]
    if lado_sel != 'Todos': df = df[df['Lado'] == lado_sel]

# ==========================================
# 3. ESTADÍSTICAS SUPERIORES
# ==========================================
st.markdown("### 📊 Rendimiento del Partido")
if not df.empty and 'Equipo' in df.columns:
    equipos_presentes = df['Equipo'].dropna().unique()
    for eq in equipos_presentes:
        st.markdown(f"**Estadísticas: {eq}**")
        df_eq = df[df['Equipo'] == eq]
        
        goles = len(df_eq[df_eq['Resultado'] == 'Gol'])
        paradas = len(df_eq[df_eq['Resultado'] == 'Parada'])
        fallos = len(df_eq[df_eq['Resultado'] == 'Fallo'])
        perdidas = len(df_eq[df_eq['Resultado'] == 'Perdida'])
        
        tiros_totales = goles + paradas + fallos
        efectividad = int(round((goles / tiros_totales * 100), 0)) if tiros_totales > 0 else 0
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Goles", goles)
        c2.metric("Efectividad", f"{efectividad}%")
        c3.metric("Tiros Totales", tiros_totales)
        c4.metric("Pérdidas", perdidas)
        c5.metric("Paradas (Rival)", paradas)
        c6.metric("Fallos", fallos)
        st.write("") 
else:
    st.info("Esperando datos para calcular métricas...")

st.divider()

# ==========================================
# 4. FUNCIONES DE DIBUJO
# ==========================================
def plot_cancha(df_filtrado):
    fig, ax = plt.subplots(figsize=(6, 8))
    fig.patch.set_facecolor('white') 
    try:
        img = mpimg.imread(IMAGEN_CANCHA)
        ax.imshow(img, extent=[0, 100, 100, 0])
    except:
        ax.set_facecolor('white')

    def extraer_coord(val, indice):
        try: return float(str(val).split(',')[indice])
        except: return np.nan
        
    df_cancha = pd.DataFrame()
    if not df_filtrado.empty and 'Coord Lado' in df_filtrado.columns:
        df_filtrado = df_filtrado.copy()
        df_filtrado['PX'] = df_filtrado['Coord Lado'].apply(lambda x: extraer_coord(x, 0))
        df_filtrado['PY'] = df_filtrado['Coord Lado'].apply(lambda x: extraer_coord(x, 1))
        df_cancha = df_filtrado.dropna(subset=['PX', 'PY'])

    if len(df_cancha) > 0:
        heatmap, xedges, yedges = np.histogram2d(df_cancha['PX'], df_cancha['PY'], bins=100, range=[[0, 100], [0, 100]])
        heatmap = heatmap.T
        heatmap_suave = gaussian_filter(heatmap, sigma=4)
        ax.imshow(heatmap_suave, extent=[0, 100, 100, 0], cmap='inferno', alpha=0.55)
        goles = df_cancha[df_cancha['Resultado'] == 'Gol']
        no_goles = df_cancha[df_cancha['Resultado'] != 'Gol']
        ax.scatter(no_goles['PX'], no_goles['PY'], c='white', marker='X', s=100, alpha=0.9, edgecolors='black')
        ax.scatter(goles['PX'], goles['PY'], c='#00e676', s=120, edgecolors='black', linewidth=1.5)

    ax.axis('off')
    return fig

def plot_porteria(df_filtrado):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor('white') 
    try:
        img = mpimg.imread(IMAGEN_PORTERIA)
        ax.imshow(img, extent=[0, 100, 100, 0])
    except:
        ax.set_facecolor('white')

    df_tiros = pd.DataFrame()
    if not df_filtrado.empty and 'Coord Porteria' in df_filtrado.columns:
        df_tiros = df_filtrado[df_filtrado['Coord Porteria'].notna() & (df_filtrado['Coord Porteria'] != '')].copy()
    
    if len(df_tiros) > 0:
        df_tiros['PX'] = df_tiros['Coord Porteria'].apply(lambda x: float(str(x).split(',')[0]) if ',' in str(x) else np.nan)
        df_tiros['PY'] = df_tiros['Coord Porteria'].apply(lambda x: float(str(x).split(',')[1]) if ',' in str(x) else np.nan)
        df_tiros = df_tiros.dropna(subset=['PX', 'PY'])
        goles = df_tiros[df_tiros['Resultado'] == 'Gol']
        paradas = df_tiros[df_tiros['Resultado'] == 'Parada']
        tiros_heatmap = df_tiros[df_tiros['Resultado'].isin(['Gol', 'Parada'])]

        if len(tiros_heatmap) > 0:
            heatmap, xedges, yedges = np.histogram2d(tiros_heatmap['PX'], tiros_heatmap['PY'], bins=100, range=[[0, 100], [0, 100]])
            heatmap = heatmap.T
            heatmap_suave = gaussian_filter(heatmap, sigma=5)
            if np.max(heatmap_suave) > 0: heatmap_suave = heatmap_suave / np.max(heatmap_suave)
            heatmap_suave[heatmap_suave < 0.05] = np.nan
            ax.imshow(heatmap_suave, extent=[0, 100, 100, 0], cmap='inferno', alpha=0.65)

        if len(paradas) > 0:
            ax.scatter(paradas['PX'], paradas['PY'], c='white', marker='X', s=100, alpha=0.9, edgecolors='black')
        if len(goles) > 0:
            ax.scatter(goles['PX'], goles['PY'], c='#00e676', s=120, edgecolors='black', linewidth=1.5)

    ax.set_xlim(0, 100)
    ax.set_ylim(100, 0)
    ax.axis('off')
    return fig

def plot_momentum(df_all):
    df_mom = df_all.copy()
    def convertir_a_minutos(row):
        try:
            partes = str(row['Tiempo']).split(':')
            if len(partes) == 3: h, m, s = int(partes[0]), int(partes[1]), float(partes[2])
            elif len(partes) == 2: h, m, s = 0, int(partes[0]), float(partes[1])
            else: return 0
            minutos = h * 60 + m + s / 60
            if str(row['Periodo']).strip().upper() == '2T': minutos += 30
            return minutos
        except: return 0

    df_mom['match_min'] = df_mom.apply(convertir_a_minutos, axis=1)
    goles_df = df_mom[df_mom['Resultado'].astype(str).str.strip().str.lower() == 'gol'].sort_values('match_min')
    
    equipos = df_mom['Equipo'].dropna().unique()
    equipo_local = equipos[0] if len(equipos) > 0 else 'Equipo 1'
    equipo_visitante = equipos[1] if len(equipos) > 1 else 'Equipo 2'

    loc_upper = str(equipo_local).strip().upper()
    vis_upper = str(equipo_visitante).strip().upper()
    if 'MEX' in loc_upper or 'MÉX' in loc_upper: color_loc, color_vis = '#006847', 'blue'
    elif 'MEX' in vis_upper or 'MÉX' in vis_upper: color_loc, color_vis = 'blue', '#006847'
    else: color_loc, color_vis = '#1565c0', '#c62828'

    t_eventos, score_loc, score_vis, momentum = [0], [0], [0], [0]
    marcador_L, marcador_V, racha_L, racha_V = 0, 0, 0, 0

    for _, row in goles_df.iterrows():
        t = row['match_min']
        eq = str(row['Equipo']).strip()
        if eq == equipo_local: marcador_L += 1; racha_L += 1; racha_V = 0
        elif eq == equipo_visitante: marcador_V += 1; racha_V += 1; racha_L = 0

        if racha_L >= 2: mom_val = racha_L
        elif racha_V >= 2: mom_val = -racha_V
        else: mom_val = 0

        t_eventos.append(t); score_loc.append(marcador_L)
        score_vis.append(marcador_V); momentum.append(mom_val)

    minuto_actual = df_mom['match_min'].max() if not df_mom.empty else 0
    t_eventos.append(minuto_actual); score_loc.append(marcador_L)
    score_vis.append(marcador_V); momentum.append(momentum[-1])

    t_arr = np.array(t_eventos)
    mom_arr = np.array(momentum)
    mom_positivo = np.where(mom_arr > 0, mom_arr, 0)
    mom_negativo = np.where(mom_arr < 0, mom_arr, 0)

    fig, (ax_marcador, ax_momentum) = plt.subplots(2, 1, figsize=(14, 5), gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
    fig.patch.set_facecolor('white') 
    fig.subplots_adjust(hspace=0.05)

    ax_marcador.step(t_arr, score_loc, where='post', color=color_loc, linewidth=3, label=equipo_local)
    ax_marcador.step(t_arr, score_vis, where='post', color=color_vis, linewidth=3, label=equipo_visitante)
    ax_marcador.axvline(x=30, color='black', linestyle='--', alpha=0.5) 
    ax_marcador.set_ylabel('Goles', fontsize=10, fontweight='bold')
    ax_marcador.grid(True, linestyle='--', alpha=0.4)
    ax_marcador.legend(fontsize=10, loc='upper left')

    ax_momentum.fill_between(t_arr, 0, mom_positivo, step='post', facecolor=color_loc, alpha=0.7)
    ax_momentum.fill_between(t_arr, 0, mom_negativo, step='post', facecolor=color_vis, alpha=0.7)
    ax_momentum.axvline(x=30, color='black', linestyle='--', alpha=0.5)
    ax_momentum.axhline(y=0, color='black', linewidth=1, alpha=0.8)
    ax_momentum.set_xlabel('Tiempo de Juego (Minutos)', fontsize=10, fontweight='bold')
    ax_momentum.set_ylabel('Momentum', fontsize=10, fontweight='bold')
    ax_momentum.grid(True, axis='x', linestyle='--', alpha=0.4)
    
    max_mom = max(abs(mom_arr.min()), abs(mom_arr.max()), 2) + 1
    ax_momentum.set_ylim(-max_mom, max_mom)
    ax_momentum.set_yticks([]) 
    eje_x_max = max(60, minuto_actual)
    ax_marcador.set_xlim(0, eje_x_max)
    ax_marcador.set_xticks(np.arange(0, eje_x_max + 5, 5))
    return fig

def plot_radiografia_errores(df_filtrado):
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#f8f9fa')
    
    if not df_filtrado.empty and 'Detalle' in df_filtrado.columns:
        df_errores = df_filtrado[df_filtrado['Resultado'].isin(['Perdida', 'Fallo', 'Sancion'])]
        detalles = df_errores['Detalle'].replace(['N/A', ''], np.nan).dropna()
        
        if not detalles.empty:
            conteo = detalles.value_counts().head(5).sort_values()
            conteo.plot(kind='barh', color='#b71c1c', edgecolor='black', ax=ax)
            ax.set_title('Top 5: Causas de Posesión Fallida', fontweight='bold', fontsize=12)
            ax.set_xlabel('Frecuencia', fontsize=9)
            ax.grid(axis='x', linestyle='--', alpha=0.7)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            return fig
            
    ax.text(0.5, 0.5, 'Sin datos de errores registrados', ha='center', va='center', color='gray')
    ax.axis('off')
    return fig

def plot_tendencia_cansancio(df_filtrado):
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#f8f9fa')
    
    if df_filtrado.empty:
        ax.text(0.5, 0.5, 'Sin datos registrados', ha='center', va='center', color='gray')
        ax.axis('off')
        return fig
        
    df_temp = df_filtrado.copy()
    def get_minuto(row):
        try:
            partes = str(row['Tiempo']).split(':')
            if len(partes) == 3: m = int(partes[1])
            elif len(partes) == 2: m = int(partes[0])
            else: return 0
            if str(row['Periodo']).strip().upper() == '2T': m += 30
            return m
        except: return 0
        
    df_temp['Minuto'] = df_temp.apply(get_minuto, axis=1)
    
    bins = [0, 10, 20, 30, 40, 50, 60, 100]
    labels = ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60', '60+']
    df_temp['Tramo'] = pd.cut(df_temp['Minuto'], bins=bins, labels=labels, right=False)
    
    goles = df_temp[df_temp['Resultado'] == 'Gol'].groupby('Tramo').size()
    perdidas = df_temp[df_temp['Resultado'] == 'Perdida'].groupby('Tramo').size()
    
    df_plot = pd.DataFrame({'Goles': goles, 'Pérdidas': perdidas}).fillna(0)
    df_plot = df_plot.reindex(labels[:6]).fillna(0) 
    
    x = np.arange(len(df_plot.index))
    width = 0.35
    
    ax.bar(x - width/2, df_plot['Goles'], width, label='Goles', color='#00e676', edgecolor='black')
    ax.bar(x + width/2, df_plot['Pérdidas'], width, label='Pérdidas', color='#b71c1c', edgecolor='black')
    
    ax.set_title('Evolución del Partido (Goles vs Pérdidas)', fontweight='bold', fontsize=12)
    ax.set_xlabel('Minutos de Juego', fontsize=10)
    ax.set_ylabel('Cantidad', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(df_plot.index, fontsize=9)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.legend(fontsize=9)
    
    return fig


# ==========================================
# 5. LAYOUT: NIVEL 1 y 2
# ==========================================
st.markdown("### 📍 Nivel 1: El Espacio (Origen y Destino)")
col_cancha, col_porteria = st.columns(2) 

with col_cancha:
    fig_cancha = plot_cancha(df)
    st.pyplot(fig_cancha)

with col_porteria:
    fig_porteria = plot_porteria(df)
    st.pyplot(fig_porteria)

st.markdown("### 📈 Nivel 2: El Flujo del Partido")
if not df.empty:
    fig_momentum = plot_momentum(df)
    st.pyplot(fig_momentum)
else:
    st.info("Esperando datos para calcular el Momentum...")

st.divider()

# ==========================================
# 6. LAYOUT: NIVEL 3 (Errores y Evolución)
# ==========================================
st.markdown("### 🧠 Nivel 3: Toma de Decisiones y Fases del Juego")
col_err, col_ev = st.columns(2)

with col_err:
    fig_errores = plot_radiografia_errores(df)
    st.pyplot(fig_errores)

with col_ev:
    fig_evolucion = plot_tendencia_cansancio(df)
    st.pyplot(fig_evolucion)

st.divider()

# ==========================================
# 7. LAYOUT: NIVEL 4 (Tabla Interactiva al fondo)
# ==========================================
st.markdown("### 📋 Nivel 4: Rendimiento Individual (Jugadoras)")
vista_tabla = st.radio("Filtro de Tabla:", ["Partido Actual", "Promedio Histórico"], horizontal=True)

df_base = df if vista_tabla == "Partido Actual" else df_vivo
df_jugadores = df_base[(df_base['Jugador'].notna()) & (df_base['Jugador'] != 'N/A') & (df_base['Jugador'] != '')].copy()

if not df_jugadores.empty:
    df_jugadores['Jugador'] = df_jugadores['Jugador'].astype(str)
    
    goles = df_jugadores[df_jugadores['Resultado'] == 'Gol'].groupby('Jugador').size().reset_index(name='Goles')
    tiros = df_jugadores[df_jugadores['Resultado'].isin(['Gol', 'Fallo', 'Parada'])].groupby('Jugador').size().reset_index(name='Tiros')
    perdidas = df_jugadores[df_jugadores['Resultado'] == 'Perdida'].groupby('Jugador').size().reset_index(name='Pérdidas')
    sanciones = df_jugadores[df_jugadores['Resultado'] == 'Sancion'].groupby('Jugador').size().reset_index(name='Sanciones')
    
    stats = pd.merge(goles, tiros, on='Jugador', how='outer').fillna(0)
    stats = pd.merge(stats, perdidas, on='Jugador', how='outer').fillna(0)
    stats = pd.merge(stats, sanciones, on='Jugador', how='outer').fillna(0)
    
    if vista_tabla == "Partido Actual":
        stats[['Goles', 'Tiros', 'Pérdidas', 'Sanciones']] = stats[['Goles', 'Tiros', 'Pérdidas', 'Sanciones']].astype(int)
    elif vista_tabla == "Promedio Histórico":
        total_partidos = df_vivo['Partido'].nunique()
        if total_partidos > 0:
            stats[['Goles', 'Tiros', 'Pérdidas', 'Sanciones']] = stats[['Goles', 'Tiros', 'Pérdidas', 'Sanciones']] / total_partidos
            stats = stats.round(1)
            
    stats['Efectividad (%)'] = np.where(stats['Tiros'] > 0, round((stats['Goles'] / stats['Tiros']) * 100, 1), 0.0)
    
    stats['Jugador'] = stats['Jugador'].apply(lambda x: x.split('.')[0] if x.endswith('.0') else x)
    
    stats = stats.sort_values(by=['Goles', 'Efectividad (%)'], ascending=[False, False]).reset_index(drop=True)
    
    st.dataframe(
        stats.style.background_gradient(subset=['Efectividad (%)'], cmap='Greens')
                   .background_gradient(subset=['Pérdidas', 'Sanciones'], cmap='Reds'),
        use_container_width=True
    )
else:
    st.info("Esperando datos de jugadoras...")

# ==========================================
# 8. TABLA DE DATOS CRUDOS
# ==========================================
with st.expander("Ver Base de Datos Cruda"):
    st.dataframe(df)
