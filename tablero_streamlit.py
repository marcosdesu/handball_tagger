import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from scipy.ndimage import gaussian_filter
from streamlit_autorefresh import st_autorefresh
import time

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Tablero Handball Live", layout="wide")
st.title("Análisis Táctico y Torneo 🤾‍♀️")

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
# 0. AUTO-REFRESCO (Cada 4 segundos)
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
# 2. FILTROS INTERACTIVOS DINÁMICOS
# ==========================================
st.sidebar.header("Filtros Globales")

if not df_vivo.empty:
    partidos_validos = [str(x) for x in df_vivo['Partido'].dropna().unique() if str(x) not in ['nan', 'N/A', '']]
    lista_partidos = ['Todos (Histórico)'] + partidos_validos
    
    lista_equipos = ['Todos'] + [str(x) for x in df_vivo['Equipo'].dropna().unique()]
    lista_fases = ['Todas'] + [str(x) for x in df_vivo['Fase'].dropna().unique()]
    lista_resultados = ['Todos'] + [str(x) for x in df_vivo['Resultado'].dropna().unique()]
    lista_lados = ['Todos'] + [str(x) for x in df_vivo['Lado'].dropna().unique()]
    
    jugadores_validos = [str(x) for x in df_vivo['Jugador'].dropna().unique() if str(x) not in ['nan', 'N/A', '']]
    lista_jugadores = ['Todos'] + sorted(jugadores_validos)
else:
    lista_partidos, lista_equipos, lista_fases, lista_resultados, lista_lados, lista_jugadores = ['Todos (Histórico)'], ['Todos'], ['Todas'], ['Todos'], ['Todos'], ['Todos']

partido_sel = st.sidebar.selectbox("🏆 Seleccionar Partido", lista_partidos)
st.sidebar.divider()

equipo_sel = st.sidebar.selectbox("1. ¿Quién ataca?", lista_equipos)
jugador_sel = st.sidebar.selectbox("2. Scouting Individual (Jugador)", lista_jugadores)
fase_sel = st.sidebar.selectbox("3. Fase de Juego", lista_fases)
resultado_sel = st.sidebar.selectbox("4. ¿Qué pasó?", lista_resultados)
lado_sel = st.sidebar.selectbox("5. Lado de la Cancha", lista_lados)

df = df_vivo.copy()
if not df.empty:
    if partido_sel != 'Todos (Histórico)': df = df[df['Partido'].astype(str) == partido_sel]
    if equipo_sel != 'Todos': df = df[df['Equipo'] == equipo_sel]
    if jugador_sel != 'Todos': df = df[df['Jugador'].astype(str) == jugador_sel]
    if fase_sel != 'Todas': df = df[df['Fase'] == fase_sel]
    if resultado_sel != 'Todos': df = df[df['Resultado'] == resultado_sel]
    if lado_sel != 'Todos': df = df[df['Lado'] == lado_sel]

# ==========================================
# 3. MÉTRICAS SEPARADAS POR EQUIPO
# ==========================================
st.markdown("### 📊 Rendimiento por Equipo")

if not df.empty and 'Equipo' in df.columns:
    equipos_presentes = df['Equipo'].dropna().unique()
    
    for eq in equipos_presentes:
        st.markdown(f"**Estadísticas: {eq}**")
        df_eq = df[df['Equipo'] == eq]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Goles", len(df_eq[df_eq['Resultado'] == 'Gol']))
        c2.metric("Paradas (Tiros atajados)", len(df_eq[df_eq['Resultado'] == 'Parada']))
        c3.metric("Fallos", len(df_eq[df_eq['Resultado'] == 'Fallo']))
        c4.metric("Pérdidas", len(df_eq[df_eq['Resultado'] == 'Perdida']))
        st.write("") 
else:
    st.info("Esperando datos para calcular métricas...")

st.divider()

# ==========================================
# 4. FUNCIONES DE DIBUJO
# ==========================================
def plot_cancha(df_filtrado):
    fig, ax = plt.subplots(figsize=(6, 10))
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
    fig, ax = plt.subplots(figsize=(10, 5))
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

def plot_radiografia_perdidas(df_filtrado):
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#f8f9fa')
    
    if not df_filtrado.empty and 'Detalle' in df_filtrado.columns:
        df_perdidas = df_filtrado[df_filtrado['Resultado'] == 'Perdida']
        detalles_validos = df_perdidas['Detalle'].replace('N/A', np.nan).dropna()
        if not detalles_validos.empty:
            conteo = detalles_validos.value_counts()
            conteo.plot(kind='bar', color='#b71c1c', edgecolor='black', ax=ax)
            ax.set_title('Radiografía de Pérdidas', fontweight='bold', fontsize=12)
            ax.set_ylabel('Cantidad')
            ax.grid(axis='y', linestyle='--', alpha=0.7)
            plt.xticks(rotation=15, ha='right', fontsize=9)
            for p in ax.patches:
                ax.annotate(str(p.get_height()), (p.get_x() + p.get_width() / 2., p.get_height()),
                            ha='center', va='center', xytext=(0, 5), textcoords='offset points', fontweight='bold')
            return fig
            
    ax.text(0.5, 0.5, 'Sin datos registrados', ha='center', va='center', color='gray')
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
    else: color_loc, color_vis = 'red', 'blue'

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

    fig, (ax_marcador, ax_momentum) = plt.subplots(2, 1, figsize=(14, 6), gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
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

# ==========================================
# 5. RENDERIZADO DE GRÁFICAS EN PANTALLA
# ==========================================
col_izq, col_der, col_extra = st.columns([1.2, 1.5, 1])

with col_izq:
    st.markdown("### 📍 Origen de la Acción")
    fig_cancha = plot_cancha(df)
    st.pyplot(fig_cancha)

with col_der:
    st.markdown("### 🥅 Definición")
    fig_porteria = plot_porteria(df)
    st.pyplot(fig_porteria)

with col_extra:
    st.markdown("### 📉 Análisis Táctico")
    fig_perdidas = plot_radiografia_perdidas(df)
    st.pyplot(fig_perdidas)

st.divider()

# ==========================================
# 7. ZONA DINÁMICA: MOMENTUM vs HISTÓRICO
# ==========================================
if partido_sel == 'Todos (Histórico)':
    st.markdown("### 🏆 Clasificación General del Torneo (Estadísticas por Jugador)")
    st.info("Visualizando el acumulado de todos los partidos registrados.")
    
    # Filtrar solo acciones donde sí se identificó a un jugador
    df_stats = df[(df['Jugador'].notna()) & (df['Jugador'] != 'N/A') & (df['Jugador'] != '')]
    
    if not df_stats.empty:
        # Calcular Tiros Totales (Gol + Fallo + Parada)
        df_tiros = df_stats[df_stats['Resultado'].isin(['Gol', 'Fallo', 'Parada'])]
        tiros = df_tiros.groupby(['Equipo', 'Jugador']).size().reset_index(name='Tiros')
        
        # Calcular Goles
        goles = df_stats[df_stats['Resultado'] == 'Gol'].groupby(['Equipo', 'Jugador']).size().reset_index(name='Goles')
        
        # Calcular Pérdidas
        perdidas = df_stats[df_stats['Resultado'] == 'Perdida'].groupby(['Equipo', 'Jugador']).size().reset_index(name='Pérdidas')
        
        # Unir todas las métricas en una sola tabla (Outer join para no perder jugadores)
        stats = pd.merge(tiros, goles, on=['Equipo', 'Jugador'], how='outer').fillna(0)
        stats = pd.merge(stats, perdidas, on=['Equipo', 'Jugador'], how='outer').fillna(0)
        
        # Calcular Porcentaje de Efectividad
        stats['Efectividad (%)'] = np.where(stats['Tiros'] > 0, round((stats['Goles'] / stats['Tiros']) * 100, 1), 0)
        
        # Formatear números enteros
        stats['Goles'] = stats['Goles'].astype(int)
        stats['Tiros'] = stats['Tiros'].astype(int)
        stats['Pérdidas'] = stats['Pérdidas'].astype(int)
        
        # Ordenar a las mejores goleadoras primero, y desempatar por efectividad
        stats = stats.sort_values(by=['Goles', 'Efectividad (%)'], ascending=[False, False]).reset_index(drop=True)
        
        # Mostrar la tabla en Streamlit (Ocupando todo el ancho)
        st.dataframe(
            stats.style.background_gradient(subset=['Efectividad (%)'], cmap='Greens')
                       .background_gradient(subset=['Pérdidas'], cmap='Reds'),
            use_container_width=True
        )
    else:
        st.warning("No hay suficientes datos de jugadores para generar la clasificación.")

else:
    # SI HAY UN PARTIDO SELECCIONADO, MOSTRAMOS EL MOMENTUM NORMAL
    st.markdown(f"### 📈 Momentum del Partido: {partido_sel}")
    if not df.empty:
        fig_momentum = plot_momentum(df)
        st.pyplot(fig_momentum)
    else:
        st.info("Esperando datos para calcular el Momentum...")

# ==========================================
# 8. TABLA DE DATOS CRUDOS
# ==========================================
with st.expander("Ver Base de Datos Cruda"):
    st.dataframe(df)
