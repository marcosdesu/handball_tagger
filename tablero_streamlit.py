import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.lines as mlines
import numpy as np
from scipy.ndimage import gaussian_filter
from streamlit_autorefresh import st_autorefresh
import time
from matplotlib.ticker import MaxNLocator

# 💡 Importaciones para el Generador de PDF
try:
    from fpdf import FPDF
    import tempfile
    import os
    FPDF_DISPONIBLE = True
except ImportError:
    FPDF_DISPONIBLE = False

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA Y MEMORIA
# ==========================================
st.set_page_config(page_title="Tablero Handball Live", layout="wide")
st.title("Análisis Táctico 🤾‍♀️")

IMAGEN_PORTERIA = 'NS_Goal_handball.png'
IMAGEN_CANCHA = 'NS_ui_Balonmano_BL_V_T.jpg'

# 💡 OPTIMIZACIÓN 1: Cargar imágenes una sola vez en RAM
@st.cache_data
def cargar_imagen(ruta):
    try:
        return mpimg.imread(ruta)
    except:
        return None

IMG_CANCHA = cargar_imagen(IMAGEN_CANCHA)
IMG_PORTERIA = cargar_imagen(IMAGEN_PORTERIA)

if 'freeze_toggle' not in st.session_state:
    st.session_state['freeze_toggle'] = True
estado_vivo = st.session_state['freeze_toggle']

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
# 0. AUTO-REFRESCO (OPTIMIZADO A 8 SEG)
# ==========================================
if estado_vivo:
    # 💡 OPTIMIZACIÓN 2: 8000 ms da tiempo para renderizar gráficas pesadas sin colapsar
    st_autorefresh(interval=8000, limit=None, key="data_refresh")

# ==========================================
# 1. CONEXIÓN A DATOS 
# ==========================================
@st.cache_data(ttl=5 if estado_vivo else 3600)
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
# 2. FILTROS EN BARRA LATERAL (ARRIBA)
# ==========================================
st.sidebar.header("Filtros del Partido")

if not df_vivo.empty:
    partidos_validos = df_vivo['Partido'].dropna().unique().tolist()
    partido_actual = partidos_validos[-1] if partidos_validos else "Sin Datos"
else:
    partido_actual = "Sin Datos"

st.sidebar.markdown(f"**🏆 Partido Actual:** {partido_actual}")
st.sidebar.divider()

if partido_actual != "Sin Datos":
    df_partido_actual = df_vivo[df_vivo['Partido'].astype(str) == partido_actual]
else:
    df_partido_actual = pd.DataFrame()

if not df_partido_actual.empty:
    lista_equipos = ['Todos'] + [str(x) for x in df_partido_actual['Equipo'].dropna().unique()]
    equipo_sel = st.sidebar.selectbox("1. ¿Quién ataca?", lista_equipos)
    
    if equipo_sel != 'Todos':
        df_para_jugadores = df_partido_actual[df_partido_actual['Equipo'] == equipo_sel]
    else:
        df_para_jugadores = df_partido_actual
        
    jugadores_validos = [str(x) for x in df_para_jugadores['Jugador'].dropna().unique() if str(x) not in ['nan', 'N/A', '']]
    jugadores_ordenados = sorted(jugadores_validos, key=lambda x: int(float(x)) if x.replace('.','',1).isdigit() else float('inf'))
    lista_jugadores = ['Todos'] + jugadores_ordenados
    
    jugador_sel = st.sidebar.selectbox("2. Scouting Individual", lista_jugadores)
    lista_fases = ['Todas'] + [str(x) for x in df_partido_actual['Fase'].dropna().unique()]
    fase_sel = st.sidebar.selectbox("3. Fase de Juego", lista_fases)
    lista_resultados = ['Todos'] + [str(x) for x in df_partido_actual['Resultado'].dropna().unique()]
    resultado_sel = st.sidebar.selectbox("4. ¿Qué pasó?", lista_resultados)
    lista_lados = ['Todos'] + [str(x) for x in df_partido_actual['Lado'].dropna().unique()]
    lado_sel = st.sidebar.selectbox("5. Lado de la Cancha", lista_lados)
else:
    equipo_sel, jugador_sel, fase_sel, resultado_sel, lado_sel = 'Todos', 'Todos', 'Todas', 'Todos', 'Todos'

df = df_partido_actual.copy()
if not df.empty:
    if equipo_sel != 'Todos': df = df[df['Equipo'] == equipo_sel]
    if jugador_sel != 'Todos': df = df[df['Jugador'].astype(str) == jugador_sel]
    if fase_sel != 'Todas': df = df[df['Fase'] == fase_sel]
    if resultado_sel != 'Todos': df = df[df['Resultado'] == resultado_sel]
    if lado_sel != 'Todos': df = df[df['Lado'] == lado_sel]

equipos_totales = df_partido_actual['Equipo'].dropna().unique() if not df_partido_actual.empty else []
equipo_local = equipos_totales[0] if len(equipos_totales) > 0 else 'Local'
equipo_visitante = equipos_totales[1] if len(equipos_totales) > 1 else None

stats_locales = {'goles':0, 'efect':0, 'tiros':0, 'perd':0, 'paradas':0, 'fallos':0}

# ==========================================
# 3. ESTADÍSTICAS SUPERIORES
# ==========================================
st.markdown("### 📊 Rendimiento del Partido")
if not df.empty and 'Equipo' in df.columns:
    equipos_filtrados = df['Equipo'].dropna().unique()
    for eq in equipos_filtrados:
        st.markdown(f"**Estadísticas: {eq}**")
        df_eq = df[df['Equipo'] == eq]
        
        goles = len(df_eq[df_eq['Resultado'] == 'Gol'])
        paradas = len(df_eq[df_eq['Resultado'] == 'Parada'])
        fallos = len(df_eq[df_eq['Resultado'] == 'Fallo'])
        perdidas = len(df_eq[df_eq['Resultado'] == 'Perdida'])
        
        tiros_totales = goles + paradas + fallos
        efectividad = int(round((goles / tiros_totales * 100), 0)) if tiros_totales > 0 else 0
        
        if eq == equipo_local:
            stats_locales = {'goles':goles, 'efect':efectividad, 'tiros':tiros_totales, 'perd':perdidas, 'paradas':paradas, 'fallos':fallos}
        
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
    if IMG_CANCHA is not None: ax.imshow(IMG_CANCHA, extent=[0, 100, 100, 0])
    else: ax.set_facecolor('white')
    
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
        paradas = df_cancha[df_cancha['Resultado'] == 'Parada']
        fallos = df_cancha[df_cancha['Resultado'] == 'Fallo']
        perdidas = df_cancha[df_cancha['Resultado'] == 'Perdida']
        
        if len(fallos) > 0: ax.scatter(fallos['PX'], fallos['PY'], c='white', marker='X', s=90, alpha=0.9, edgecolors='black')
        if len(perdidas) > 0: ax.scatter(perdidas['PX'], perdidas['PY'], c='#d32f2f', marker='D', s=80, alpha=0.9, edgecolors='black')
        if len(paradas) > 0: ax.scatter(paradas['PX'], paradas['PY'], c='#ff9800', marker='^', s=100, alpha=0.9, edgecolors='black')
        if len(goles) > 0: ax.scatter(goles['PX'], goles['PY'], c='#00e676', marker='o', s=120, edgecolors='black', linewidth=1.5)
    
    leyenda = [
        mlines.Line2D([], [], color='w', marker='o', markerfacecolor='#00e676', markeredgecolor='black', markersize=9, markeredgewidth=1.5, label='Gol'),
        mlines.Line2D([], [], color='w', marker='^', markerfacecolor='#ff9800', markeredgecolor='black', markersize=9, label='Parada'),
        mlines.Line2D([], [], color='w', marker='X', markerfacecolor='white', markeredgecolor='black', markersize=9, label='Fallo'),
        mlines.Line2D([], [], color='w', marker='D', markerfacecolor='#d32f2f', markeredgecolor='black', markersize=8, label='Pérdida')
    ]
    ax.legend(handles=leyenda, loc='lower right', fontsize=8, title='Simbología', title_fontsize=9, framealpha=0.8, edgecolor='black')
    ax.axis('off')
    return fig

def plot_porteria(df_filtrado):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor('white') 
    if IMG_PORTERIA is not None: ax.imshow(IMG_PORTERIA, extent=[0, 100, 100, 0])
    else: ax.set_facecolor('white')
    
    df_tiros = pd.DataFrame()
    if not df_filtrado.empty and 'Coord Porteria' in df_filtrado.columns:
        df_tiros = df_filtrado[df_filtrado['Coord Porteria'].notna() & (df_filtrado['Coord Porteria'] != '')].copy()
        
    if len(df_tiros) > 0:
        df_tiros['PX'] = df_tiros['Coord Porteria'].apply(lambda x: float(str(x).split(',')[0]) if ',' in str(x) else np.nan)
        df_tiros['PY'] = df_tiros['Coord Porteria'].apply(lambda x: float(str(x).split(',')[1]) if ',' in str(x) else np.nan)
        df_tiros = df_tiros.dropna(subset=['PX', 'PY'])
        
        goles = df_tiros[df_tiros['Resultado'] == 'Gol']
        paradas = df_tiros[df_tiros['Resultado'] == 'Parada']
        fallos = df_tiros[df_tiros['Resultado'] == 'Fallo']
        
        tiros_heatmap = df_tiros[df_tiros['Resultado'].isin(['Gol', 'Parada'])]
        if len(tiros_heatmap) > 0:
            heatmap, xedges, yedges = np.histogram2d(tiros_heatmap['PX'], tiros_heatmap['PY'], bins=100, range=[[0, 100], [0, 100]])
            heatmap = heatmap.T
            heatmap_suave = gaussian_filter(heatmap, sigma=5)
            if np.max(heatmap_suave) > 0: heatmap_suave = heatmap_suave / np.max(heatmap_suave)
            heatmap_suave[heatmap_suave < 0.05] = np.nan
            ax.imshow(heatmap_suave, extent=[0, 100, 100, 0], cmap='inferno', alpha=0.65)
            
        if len(fallos) > 0: ax.scatter(fallos['PX'], fallos['PY'], c='white', marker='X', s=90, alpha=0.9, edgecolors='black')
        if len(paradas) > 0: ax.scatter(paradas['PX'], paradas['PY'], c='#ff9800', marker='^', s=100, alpha=0.9, edgecolors='black')
        if len(goles) > 0: ax.scatter(goles['PX'], goles['PY'], c='#00e676', marker='o', s=120, edgecolors='black', linewidth=1.5)
    
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
    
    t_eventos, score_loc, score_vis, momentum = [0], [0], [0], [0]
    marcador_L, marcador_V, racha_L, racha_V = 0, 0, 0, 0

    color_loc = '#00e676' if 'MEX' in equipo_local.upper() or 'CITRON' in equipo_local.upper() else '#1565c0'
    color_vis = '#d32f2f'

    for _, row in goles_df.iterrows():
        t = row['match_min']
        eq = str(row['Equipo']).strip()
        if eq == equipo_local: marcador_L += 1; racha_L += 1; racha_V = 0
        elif eq == equipo_visitante: marcador_V += 1; racha_V += 1; racha_L = 0

        if racha_L >= 2: mom_val = racha_L
        elif racha_V >= 2: mom_val = -racha_V
        else: mom_val = 0

        t_eventos.append(t); score_loc.append(marcador_L); score_vis.append(marcador_V); momentum.append(mom_val)

    minuto_actual = df_mom['match_min'].max() if not df_mom.empty else 0
    t_eventos.append(minuto_actual); score_loc.append(marcador_L); score_vis.append(marcador_V); momentum.append(momentum[-1])

    t_arr = np.array(t_eventos); mom_arr = np.array(momentum)
    mom_positivo = np.where(mom_arr > 0, mom_arr, 0); mom_negativo = np.where(mom_arr < 0, mom_arr, 0)

    fig, (ax_marcador, ax_momentum) = plt.subplots(2, 1, figsize=(14, 5), gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
    fig.patch.set_facecolor('white') 
    
    ax_marcador.step(t_arr, score_loc, where='post', color=color_loc, linewidth=3, label=equipo_local)
    ax_marcador.step(t_arr, score_vis, where='post', color=color_vis, linewidth=3, label=equipo_visitante if equipo_visitante else 'Visitante')
    ax_marcador.axvline(x=30, color='black', linestyle='--', alpha=0.5) 
    ax_marcador.set_ylabel('Goles', fontsize=10, fontweight='bold')
    ax_marcador.grid(True, linestyle='--', alpha=0.4); ax_marcador.legend(fontsize=10, loc='upper left')

    ax_momentum.fill_between(t_arr, 0, mom_positivo, step='post', facecolor=color_loc, alpha=0.7)
    ax_momentum.fill_between(t_arr, 0, mom_negativo, step='post', facecolor=color_vis, alpha=0.7)
    ax_momentum.axvline(x=30, color='black', linestyle='--', alpha=0.5); ax_momentum.axhline(y=0, color='black', linewidth=1, alpha=0.8)
    ax_momentum.set_xlabel('Tiempo de Juego (Minutos)', fontsize=10, fontweight='bold')
    ax_momentum.set_ylabel('Momentum', fontsize=10, fontweight='bold')
    ax_momentum.grid(True, axis='x', linestyle='--', alpha=0.4)
    
    max_mom = max(abs(mom_arr.min()), abs(mom_arr.max()), 2) + 1
    ax_momentum.set_ylim(-max_mom, max_mom); ax_momentum.set_yticks([]) 
    eje_x_max = max(60, minuto_actual)
    ax_marcador.set_xlim(0, eje_x_max)
    ax_marcador.set_xticks(np.arange(0, eje_x_max + 5, 5))
    
    fig.tight_layout() 
    return fig

def plot_radar_avanzado(df_partido, df_historico, eq_local, eq_vis, modo):
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#f8f9fa')

    if df_partido.empty or eq_local not in df_partido['Equipo'].values:
        ax.text(0.5, 0.5, f'Sin datos suficientes', ha='center', va='center', color='gray')
        ax.axis('off')
        return fig

    categorias = ['Efectividad\n(Tiro)', 'Solidez\n(Portería)', 'Seguridad\n(Balón)', 'Disciplina\n(Táctica)', 'Efectividad\n(Transición)']
    angulos = np.linspace(0, 2 * np.pi, len(categorias), endpoint=False).tolist()
    angulos += angulos[:1]

    def get_metrics(df_team, df_rival):
        g = len(df_team[df_team['Resultado'] == 'Gol'])
        t = len(df_team[df_team['Resultado'].isin(['Gol', 'Fallo', 'Parada'])])
        efect = (g / t * 100) if t > 0 else 0
        p_riv = len(df_rival[df_rival['Resultado'] == 'Parada'])
        t_riv = len(df_rival[df_rival['Resultado'].isin(['Gol', 'Fallo', 'Parada'])])
        solidez = (p_riv / t_riv * 100) if t_riv > 0 else 0 
        perd = len(df_team[df_team['Resultado'] == 'Perdida'])
        pos = t + perd
        seguridad = (t / pos * 100) if pos > 0 else 0
        sanc = len(df_team[df_team['Resultado'] == 'Sancion'])
        disciplina = max(0, 100 - (sanc * 10))
        df_trans = df_team[df_team['Fase'].astype(str).str.contains('Transicion', case=False, na=False)]
        g_trans = len(df_trans[df_trans['Resultado'] == 'Gol'])
        acc_trans = len(df_trans)
        transicion = (g_trans / acc_trans * 100) if acc_trans > 0 else 0
        vals = [efect, solidez, seguridad, disciplina, transicion]
        vals += vals[:1]
        return vals

    color_loc = '#00e676' if 'MEX' in eq_local.upper() or 'CITRON' in eq_local.upper() else '#1565c0'
    color_vis = '#d32f2f'

    df_loc_actual = df_partido[df_partido['Equipo'] == eq_local]
    df_vis_actual = df_partido[df_partido['Equipo'] == eq_vis] if eq_vis else pd.DataFrame()
    vals_loc_actual = get_metrics(df_loc_actual, df_vis_actual)

    if modo == "El Rival de Hoy":
        vals_vis_actual = get_metrics(df_vis_actual, df_loc_actual)
        ax.plot(angulos, vals_loc_actual, color=color_loc, linewidth=2.5, label=str(eq_local))
        ax.fill(angulos, vals_loc_actual, color=color_loc, alpha=0.3)
        if eq_vis:
            ax.plot(angulos, vals_vis_actual, color=color_vis, linewidth=2, label=str(eq_vis))
            ax.fill(angulos, vals_vis_actual, color=color_vis, alpha=0.2)
        ax.set_title(f'Rendimiento: {eq_local} vs {eq_vis}', fontweight='bold', pad=20)
    else:
        partidos_local = df_historico[df_historico['Equipo'] == eq_local]['Partido'].unique()
        df_hist_loc = df_historico[(df_historico['Partido'].isin(partidos_local)) & (df_historico['Equipo'] == eq_local)]
        df_hist_riv = df_historico[(df_historico['Partido'].isin(partidos_local)) & (df_historico['Equipo'] != eq_local)]
        vals_loc_hist = get_metrics(df_hist_loc, df_hist_riv)
        
        ax.plot(angulos, vals_loc_hist, color='#9e9e9e', linewidth=2, linestyle='--', label='Promedio Histórico')
        ax.fill(angulos, vals_loc_hist, color='#9e9e9e', alpha=0.2)
        ax.plot(angulos, vals_loc_actual, color=color_loc, linewidth=2.5, label=f'{eq_local} (Hoy)')
        ax.fill(angulos, vals_loc_actual, color=color_loc, alpha=0.4)
        ax.set_title(f'Desempeño de {eq_local} vs Su Historia', fontweight='bold', pad=20)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100%'], color="grey", size=8)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angulos[:-1]), categorias, fontsize=10, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), fontsize=9)
    return fig

def plot_tendencia_cansancio(df_partido, df_historico, eq_local, modo):
    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#f8f9fa')
    
    if df_partido.empty or eq_local not in df_partido['Equipo'].values:
        ax.text(0.5, 0.5, f'Sin datos suficientes', ha='center', va='center', color='gray')
        ax.axis('off')
        return fig
        
    def get_minuto(row):
        try:
            partes = str(row['Tiempo']).split(':')
            if len(partes) == 3: m = int(partes[1])
            elif len(partes) == 2: m = int(partes[0])
            else: return 0
            if str(row['Periodo']).strip().upper() == '2T': m += 30
            return m
        except: return 0
        
    df_hoy = df_partido[df_partido['Equipo'] == eq_local].copy()
    df_hoy['Minuto'] = df_hoy.apply(get_minuto, axis=1)
    bins = [0, 10, 20, 30, 40, 50, 60, 100]
    labels = ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60', '60+']
    df_hoy['Tramo'] = pd.cut(df_hoy['Minuto'], bins=bins, labels=labels, right=False)
    
    goles_hoy = df_hoy[df_hoy['Resultado'] == 'Gol'].groupby('Tramo', observed=False).size()
    perdidas_hoy = df_hoy[df_hoy['Resultado'] == 'Perdida'].groupby('Tramo', observed=False).size()
    df_plot_hoy = pd.DataFrame({'Goles': goles_hoy, 'Pérdidas': perdidas_hoy}).reindex(labels[:6]).fillna(0)
    
    x = np.arange(len(df_plot_hoy.index))
    width = 0.35
    color_gol = '#00e676' if 'MEX' in eq_local.upper() or 'CITRON' in eq_local.upper() else '#1565c0'
    
    ax.bar(x - width/2, df_plot_hoy['Goles'], width, label='Goles (Hoy)', color=color_gol, edgecolor='black')
    ax.bar(x + width/2, df_plot_hoy['Pérdidas'], width, label='Pérdidas (Hoy)', color='#d32f2f', edgecolor='black')
    
    if modo == "Nuestra Historia":
        partidos_local = df_historico[df_historico['Equipo'] == eq_local]['Partido'].unique()
        divisor = len(partidos_local) if len(partidos_local) > 0 else 1
        df_hist = df_historico[(df_historico['Partido'].isin(partidos_local)) & (df_historico['Equipo'] == eq_local)].copy()
        
        if not df_hist.empty:
            df_hist['Minuto'] = df_hist.apply(get_minuto, axis=1)
            df_hist['Tramo'] = pd.cut(df_hist['Minuto'], bins=bins, labels=labels, right=False)
            goles_hist = (df_hist[df_hist['Resultado'] == 'Gol'].groupby('Tramo', observed=False).size() / divisor)
            perdidas_hist = (df_hist[df_hist['Resultado'] == 'Perdida'].groupby('Tramo', observed=False).size() / divisor)
            
            df_plot_hist = pd.DataFrame({'Goles': goles_hist, 'Pérdidas': perdidas_hist}).reindex(labels[:6]).fillna(0)
            
            ax.plot(x - width/2, df_plot_hist['Goles'], color='black', marker='o', linestyle='dashed', linewidth=2, label='Promedio Hist. Goles')
            ax.plot(x + width/2, df_plot_hist['Pérdidas'], color='black', marker='X', linestyle='dashed', linewidth=2, label='Promedio Hist. Pérdidas')
            titulo = f'Evolución: Hoy vs Promedio Histórico ({eq_local})'
        else:
            titulo = f'Fatiga Táctica: {eq_local} (Hoy)'
    else:
        titulo = f'Fatiga Táctica: {eq_local} (Hoy)'
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    ax.set_title(titulo, fontweight='bold', fontsize=12)
    ax.set_xlabel('Minutos de Juego', fontsize=10)
    ax.set_ylabel('Cantidad', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(df_plot_hoy.index, fontsize=9)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2)
    plt.subplots_adjust(bottom=0.25)
    return fig

# Generamos figuras de UI
fig_cancha = plot_cancha(df)
fig_porteria = plot_porteria(df)
fig_momentum = plot_momentum(df) if not df.empty else None

# ==========================================
# LAYOUT PRINCIPAL (UI FRONT-END)
# ==========================================
st.markdown("### 📍 Nivel 1: El Espacio (Origen y Destino)")
col_cancha, col_porteria = st.columns(2) 
with col_cancha: 
    st.pyplot(fig_cancha)
    plt.close(fig_cancha) # 💡 OPTIMIZACIÓN 3: Limpiar memoria RAM inmediatamente
with col_porteria: 
    st.pyplot(fig_porteria)
    plt.close(fig_porteria)

st.markdown("### 📈 Nivel 2: El Flujo del Partido")
if fig_momentum: 
    st.pyplot(fig_momentum)
    plt.close(fig_momentum)
else: 
    st.info("Esperando datos para calcular el Momentum...")
st.divider()

st.markdown("### 🧠 Nivel 3: Toma de Decisiones y Evolución Táctica")
modo_analisis = st.radio("🔍 Perspectiva de Análisis:", ["El Rival de Hoy", "Nuestra Historia"], horizontal=True)

fig_radar = plot_radar_avanzado(df, df_vivo, equipo_local, equipo_visitante, modo_analisis)
fig_evolucion = plot_tendencia_cansancio(df, df_vivo, equipo_local, modo_analisis)

col_rad, col_ev = st.columns(2)
with col_rad: 
    st.pyplot(fig_radar)
    plt.close(fig_radar)
with col_ev: 
    st.pyplot(fig_evolucion)
    plt.close(fig_evolucion)
st.divider()

st.markdown("### 📋 Nivel 4: Rendimiento Individual Detallado")
vista_tabla = st.radio("Filtro de Tabla:", ["Partido Actual", "Promedio Histórico"], horizontal=True)

if vista_tabla == "Partido Actual":
    df_base = df
else:
    df_base = df_vivo[df_vivo['Equipo'] == equipo_local].copy()

df_jugadores = df_base[(df_base['Jugador'].notna()) & (df_base['Jugador'] != 'N/A') & (df_base['Jugador'] != '')].copy()

if not df_jugadores.empty:
    df_jugadores['Jugador'] = df_jugadores['Jugador'].astype(str)
    
    goles = df_jugadores[df_jugadores['Resultado'] == 'Gol'].groupby(['Equipo', 'Jugador']).size().reset_index(name='Goles')
    fallos = df_jugadores[df_jugadores['Resultado'] == 'Fallo'].groupby(['Equipo', 'Jugador']).size().reset_index(name='Fallos')
    atajados = df_jugadores[df_jugadores['Resultado'] == 'Parada'].groupby(['Equipo', 'Jugador']).size().reset_index(name='Atajados')
    perdidas = df_jugadores[df_jugadores['Resultado'] == 'Perdida'].groupby(['Equipo', 'Jugador']).size().reset_index(name='Pérdidas')
    
    amarillas = df_jugadores[df_jugadores['Detalle'].astype(str).str.contains('Amarilla', case=False, na=False)].groupby(['Equipo', 'Jugador']).size().reset_index(name='TA')
    dos_min = df_jugadores[df_jugadores['Detalle'].astype(str).str.contains('2 Min', case=False, na=False)].groupby(['Equipo', 'Jugador']).size().reset_index(name='2M')
    rojas = df_jugadores[df_jugadores['Detalle'].astype(str).str.contains('Roja', case=False, na=False)].groupby(['Equipo', 'Jugador']).size().reset_index(name='TR')
    
    stats = pd.merge(goles, fallos, on=['Equipo', 'Jugador'], how='outer').fillna(0)
    stats = pd.merge(stats, atajados, on=['Equipo', 'Jugador'], how='outer').fillna(0)
    stats = pd.merge(stats, perdidas, on=['Equipo', 'Jugador'], how='outer').fillna(0)
    stats = pd.merge(stats, amarillas, on=['Equipo', 'Jugador'], how='outer').fillna(0)
    stats = pd.merge(stats, dos_min, on=['Equipo', 'Jugador'], how='outer').fillna(0)
    stats = pd.merge(stats, rojas, on=['Equipo', 'Jugador'], how='outer').fillna(0)
    
    stats['Tiros'] = stats['Goles'] + stats['Fallos'] + stats['Atajados']
    
    columnas_numericas = ['Goles', 'Fallos', 'Atajados', 'Tiros', 'Pérdidas', 'TA', '2M', 'TR']
    
    if vista_tabla == "Partido Actual":
        stats[columnas_numericas] = stats[columnas_numericas].astype(int)
        format_dict = {col: '{:.0f}' for col in columnas_numericas}
    else:
        total_partidos = df_base['Partido'].nunique()
        if total_partidos > 0: stats[columnas_numericas] = stats[columnas_numericas] / total_partidos
        format_dict = {col: '{:.1f}' for col in columnas_numericas}
            
    stats['Efectividad (%)'] = np.where(stats['Tiros'] > 0, (stats['Goles'] / stats['Tiros']) * 100, 0.0)
    format_dict['Efectividad (%)'] = '{:.1f}'
    
    stats['Jugador'] = stats['Jugador'].apply(lambda x: x.split('.')[0] if x.endswith('.0') else x)
    
    orden_cols = ['Equipo', 'Jugador', 'Goles', 'Fallos', 'Atajados', 'Tiros', 'Efectividad (%)', 'Pérdidas', 'TA', '2M', 'TR']
    stats = stats[orden_cols].sort_values(by=['Equipo', 'Goles', 'Efectividad (%)'], ascending=[False, False, False]).reset_index(drop=True)
    
    st.dataframe(
        stats.style.format(format_dict)
                   .background_gradient(subset=['Efectividad (%)'], cmap='Greens')
                   .background_gradient(subset=['Pérdidas', 'TA', '2M', 'TR'], cmap='Reds'), 
        use_container_width=True
    )
else:
    st.info("Esperando datos individuales...")
    
with st.expander("Ver Base de Datos Cruda"): st.dataframe(df)

# ==========================================
# MOTOR GENERADOR DE PDF MULTI-EQUIPO
# ==========================================
def crear_pdf_reporte(partido_nom, eq_local, eq_vis, df_partido, df_historico):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generar gráficas frescas solo para el PDF para asegurar que no interfieran con la memoria de UI
        df_loc = df_partido[df_partido['Equipo'] == eq_local]
        fig_c_loc = plot_cancha(df_loc)
        fig_p_loc = plot_porteria(df_loc)
        p_c_loc = os.path.join(tmpdir, "c_loc.png")
        p_p_loc = os.path.join(tmpdir, "p_loc.png")
        fig_c_loc.savefig(p_c_loc, bbox_inches='tight', facecolor='white', dpi=150)
        fig_p_loc.savefig(p_p_loc, bbox_inches='tight', facecolor='white', dpi=150)
        plt.close(fig_c_loc); plt.close(fig_p_loc)
        
        df_vis = df_partido[df_partido['Equipo'] == eq_vis] if eq_vis else pd.DataFrame()
        if not df_vis.empty:
            fig_c_vis = plot_cancha(df_vis)
            fig_p_vis = plot_porteria(df_vis)
            p_c_vis = os.path.join(tmpdir, "c_vis.png")
            p_p_vis = os.path.join(tmpdir, "p_vis.png")
            fig_c_vis.savefig(p_c_vis, bbox_inches='tight', facecolor='white', dpi=150)
            fig_p_vis.savefig(p_p_vis, bbox_inches='tight', facecolor='white', dpi=150)
            plt.close(fig_c_vis); plt.close(fig_p_vis)
            
        fig_mom_pdf = plot_momentum(df_partido) if not df_partido.empty else None
        fig_rad_pdf = plot_radar_avanzado(df_partido, df_historico, eq_local, eq_vis, "Nuestra Historia")
        fig_evo_pdf = plot_tendencia_cansancio(df_partido, df_historico, eq_local, "Nuestra Historia")
        
        p_mom = os.path.join(tmpdir, "mom.png")
        p_rad = os.path.join(tmpdir, "rad.png")
        p_evo = os.path.join(tmpdir, "evo.png")
        if fig_mom_pdf: fig_mom_pdf.savefig(p_mom, bbox_inches='tight', facecolor='white', dpi=150)
        if fig_rad_pdf: fig_rad_pdf.savefig(p_rad, bbox_inches='tight', facecolor='white', dpi=150)
        if fig_evo_pdf: fig_evo_pdf.savefig(p_evo, bbox_inches='tight', facecolor='white', dpi=150)
        plt.close(fig_mom_pdf); plt.close(fig_rad_pdf); plt.close(fig_evo_pdf)

        def construir_hojas_equipo(team_name, df_team, p_cancha, p_porteria, is_local):
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"REPORTE TACTICO: {partido_nom}", ln=True, align='C')
            pdf.set_font("Arial", "", 12)
            tipo = "LOCAL" if is_local else "VISITANTE"
            pdf.cell(0, 10, f"Equipo {tipo}: {team_name}", ln=True, align='C')
            pdf.ln(5)
            
            g_team = len(df_team[df_team['Resultado'] == 'Gol'])
            p_team = len(df_team[df_team['Resultado'] == 'Parada'])
            f_team = len(df_team[df_team['Resultado'] == 'Fallo'])
            l_team = len(df_team[df_team['Resultado'] == 'Perdida'])
            t_team = g_team + p_team + f_team
            e_team = int(round((g_team / t_team * 100), 0)) if t_team > 0 else 0
            
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Estadisticas Colectivas", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.cell(0, 8, f"Goles: {g_team}  |  Efectividad: {e_team}%  |  Tiros Totales: {t_team}", ln=True)
            pdf.cell(0, 8, f"Perdidas: {l_team}  |  Fallos: {f_team}  |  Paradas del Rival: {p_team}", ln=True)
            pdf.ln(8)
            
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Rendimiento Individual Detallado", ln=True)
            pdf.ln(2)
            
            df_jug = df_team[(df_team['Jugador'].notna()) & (df_team['Jugador'] != 'N/A') & (df_team['Jugador'] != '')].copy()
            if not df_jug.empty:
                df_jug['Jugador'] = df_jug['Jugador'].astype(str)
                t_gol = df_jug[df_jug['Resultado'] == 'Gol'].groupby('Jugador').size().reset_index(name='Gol')
                t_fal = df_jug[df_jug['Resultado'] == 'Fallo'].groupby('Jugador').size().reset_index(name='Fal')
                t_atj = df_jug[df_jug['Resultado'] == 'Parada'].groupby('Jugador').size().reset_index(name='Atj')
                t_per = df_jug[df_jug['Resultado'] == 'Perdida'].groupby('Jugador').size().reset_index(name='Perd')
                t_ta = df_jug[df_jug['Detalle'].astype(str).str.contains('Amarilla', case=False, na=False)].groupby('Jugador').size().reset_index(name='TA')
                t_2m = df_jug[df_jug['Detalle'].astype(str).str.contains('2 Min', case=False, na=False)].groupby('Jugador').size().reset_index(name='2M')
                t_tr = df_jug[df_jug['Detalle'].astype(str).str.contains('Roja', case=False, na=False)].groupby('Jugador').size().reset_index(name='TR')
                
                pdf_stats = pd.merge(t_gol, t_fal, on='Jugador', how='outer').fillna(0)
                pdf_stats = pd.merge(pdf_stats, t_atj, on='Jugador', how='outer').fillna(0)
                pdf_stats = pd.merge(pdf_stats, t_per, on='Jugador', how='outer').fillna(0)
                pdf_stats = pd.merge(pdf_stats, t_ta, on='Jugador', how='outer').fillna(0)
                pdf_stats = pd.merge(pdf_stats, t_2m, on='Jugador', how='outer').fillna(0)
                pdf_stats = pd.merge(pdf_stats, t_tr, on='Jugador', how='outer').fillna(0)
                
                pdf_stats['Tir'] = pdf_stats['Gol'] + pdf_stats['Fal'] + pdf_stats['Atj']
                cols_int = ['Gol', 'Fal', 'Atj', 'Tir', 'Perd', 'TA', '2M', 'TR']
                pdf_stats[cols_int] = pdf_stats[cols_int].astype(int)
                pdf_stats['Efect%'] = np.where(pdf_stats['Tir'] > 0, (pdf_stats['Gol'] / pdf_stats['Tir']) * 100, 0.0)
                pdf_stats['Jugador'] = pdf_stats['Jugador'].apply(lambda x: x.split('.')[0] if x.endswith('.0') else x)
                pdf_stats = pdf_stats.sort_values(by=['Gol', 'Efect%'], ascending=[False, False]).reset_index(drop=True)
                
                pdf.set_font("Arial", "B", 8)
                col_widths = [40, 16, 16, 16, 16, 16, 16, 16, 16, 20]
                headers = ['Deportista', 'Gol', 'Fal', 'Atj', 'Tir', 'Perd', 'TA', '2M', 'TR', 'Efect%']
                for i, h in enumerate(headers):
                    pdf.cell(col_widths[i], 8, h, border=1, align='C')
                pdf.ln()
                
                pdf.set_font("Arial", "", 8)
                for _, row in pdf_stats.iterrows():
                    pdf.cell(col_widths[0], 8, str(row['Jugador'])[:20], border=1, align='C')
                    pdf.cell(col_widths[1], 8, str(row['Gol']), border=1, align='C')
                    pdf.cell(col_widths[2], 8, str(row['Fal']), border=1, align='C')
                    pdf.cell(col_widths[3], 8, str(row['Atj']), border=1, align='C')
                    pdf.cell(col_widths[4], 8, str(row['Tir']), border=1, align='C')
                    pdf.cell(col_widths[5], 8, str(row['Perd']), border=1, align='C')
                    pdf.cell(col_widths[6], 8, str(row['TA']), border=1, align='C')
                    pdf.cell(col_widths[7], 8, str(row['2M']), border=1, align='C')
                    pdf.cell(col_widths[8], 8, str(row['TR']), border=1, align='C')
                    pdf.cell(col_widths[9], 8, f"{row['Efect%']:.1f}%", border=1, align='C')
                    pdf.ln()
            else:
                pdf.set_font("Arial", "I", 10)
                pdf.cell(0, 10, "Sin datos de atletas registrados.", ln=True)

            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"Mapas Espaciales: {team_name}", ln=True)
            pdf.image(p_cancha, x=10, y=30, w=90)
            pdf.image(p_porteria, x=105, y=30, w=90)

        construir_hojas_equipo(eq_local, df_loc, p_c_loc, p_p_loc, True)
        if not df_vis.empty and eq_vis:
            construir_hojas_equipo(eq_vis, df_vis, p_c_vis, p_p_vis, False)

        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "ANALISIS COLECTIVO Y EVOLUCION", ln=True, align='C')
        pdf.ln(5)
        
        curr_y = pdf.get_y()
        if fig_mom_pdf:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "1. Flujo del Partido (Momentum)", ln=True)
            img_y = pdf.get_y()
            pdf.image(p_mom, x=10, y=img_y, w=190)
            curr_y = img_y + 75 
            
        pdf.set_y(curr_y)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "2. Toma de Decisiones y Fatiga Tactica", ln=True)
        img_y_2 = pdf.get_y()
        if fig_rad_pdf: pdf.image(p_rad, x=10, y=img_y_2, w=90)
        if fig_evo_pdf: pdf.image(p_evo, x=105, y=img_y_2, w=90)

        pdf_path = os.path.join(tmpdir, "reporte.pdf")
        pdf.output(pdf_path)
        with open(pdf_path, "rb") as f: return f.read()

# ==========================================
# SECCIÓN FINAL: CONTROLES DE LA BARRA LATERAL
# ==========================================
st.sidebar.divider()
st.sidebar.markdown("### 🕹️ Control del Tablero")

st.sidebar.toggle("🟢 Conexión En Vivo", key="freeze_toggle", help="Apágalo para detener el refresco y exportar el reporte.")

if estado_vivo:
    st.sidebar.info("Actualizando datos cada 8 segundos.")
else:
    st.sidebar.warning("🔴 Tablero Congelado")

st.sidebar.markdown("### 📥 Exportar Análisis")

if FPDF_DISPONIBLE and partido_actual != "Sin Datos" and not df.empty:
    if not estado_vivo:
        if st.sidebar.button("⚙️ Preparar Reporte PDF"):
            with st.sidebar.status("Construyendo reporte táctico..."):
                pdf_data = crear_pdf_reporte(partido_actual, equipo_local, equipo_visitante, df_partido_actual, df_vivo)
                st.session_state['pdf_listo'] = pdf_data
                
        if 'pdf_listo' in st.session_state:
            st.sidebar.download_button(label="⬇️ Descargar PDF Ahora", data=st.session_state['pdf_listo'], file_name=f"Reporte_{partido_actual}.pdf", mime="application/pdf")
    else:
        st.sidebar.info("Para exportar, pausa el tablero arriba (🟢 -> 🔴 Tablero Congelado).")
