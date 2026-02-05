import streamlit as st
import pandas as pd
import math
import time
import asyncio
import sys
import re
import os
import subprocess

# --- PARCHE PARA WINDOWS ---
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except: pass

from playwright.sync_api import sync_playwright

# --- PARCHE PARA INSTALAR NAVEGADOR EN LA NUBE ---
# Esto comprueba si el navegador está instalado, si no, lo instala.
def install_playwright_browser():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        print("✅ Navegador Chromium instalado correctamente.")
    except Exception as e:
        print(f"⚠️ Error instalando navegador: {e}")

# Ejecutamos la instalación solo si estamos en Linux (Cloud)
if not sys.platform.startswith("win"):
    install_playwright_browser()

# ==========================================
# 🧠 DATOS (RANKINGS + ALIAS) - (Mismo código tuyo)
# ==========================================
RANKINGS_DB = {
     "top_50_clubes": [
        "Real Madrid", "Bayern Munich", "Inter Milan", "Liverpool FC", "Manchester City", "Paris Saint-Germain", 
        "Arsenal FC", "FC Barcelona", "Borussia Dortmund", "Bayer 04 Leverkusen", "Atlético de Madrid", "AS Roma", 
        "Chelsea FC", "SL Benfica", "Eintracht Frankfurt", "Atalanta BC", "Manchester United", "Tottenham Hotspur", 
        "Sporting CP", "Club Brugge KV", "PSV Eindhoven", "Feyenoord Rotterdam", "ACF Fiorentina", "Juventus FC", 
        "West Ham United", "FC Porto", "AC Milan", "Aston Villa", "LOSC Lille", "Real Betis Balompié", 
        "SSC Napoli", "Olympique Lyon", "RB Leipzig", "Rangers FC", "SS Lazio", "Villarreal CF", "Olympiacos", 
        "Ajax Amsterdam", "FK Bodø/Glimt", "Real Sociedad", "AZ Alkmaar", "Fenerbahce", "FC Copenhagen", 
        "Olympique Marseille", "AS Monaco", "SC Braga", "Shakhtar Donetsk", "Galatasaray", "Ferencvárosi TC", 
        "PAOK Thessaloniki"
    ],
    "top_25_clubes": [
        "Real Madrid", "Bayern Munich", "Inter Milan", "Liverpool FC", "Manchester City", "Paris Saint-Germain", 
        "Arsenal FC", "FC Barcelona", "Borussia Dortmund", "Bayer 04 Leverkusen", "Atlético de Madrid", "AS Roma", 
        "Chelsea FC", "SL Benfica", "Eintracht Frankfurt", "Atalanta BC", "Manchester United", "Tottenham Hotspur", 
        "Sporting CP", "Club Brugge KV", "PSV Eindhoven", "Feyenoord Rotterdam", "ACF Fiorentina", "Juventus FC", 
        "West Ham United"
    ],
    "top_50_selecciones": [
        "Spain", "Argentina", "France", "England", "Brazil", "Portugal", "Netherlands", "Morocco", "Belgium", 
        "Germany", "Croatia", "Senegal", "Italy", "Colombia", "United States", "Mexico", "Uruguay", "Switzerland", 
        "Japan", "Iran", "Denmark", "South Korea", "Ecuador", "Austria", "Turkiye", "Nigeria", "Australia", 
        "Algeria", "Canada", "Ukraine", "Egypt", "Norway", "Panama", "Poland", "Wales", "Russia", "Ivory Coast", 
        "Scotland", "Serbia", "Paraguay", "Hungary", "Sweden", "Czech Republic", "Slovakia", "Cameroon", "Greece", 
        "Tunisia", "Democratic Republic of the Congo", "Romania", "Venezuela"
    ]
}

ALIAS_MAP = {
    "Man City": "Manchester City", "Man Utd": "Manchester United", "Man. Utd": "Manchester United",
    "PSG": "Paris Saint-Germain", "Paris SG": "Paris Saint-Germain",
    "Atlético": "Atlético de Madrid", "Atletico Madrid": "Atlético de Madrid",
    "Inter": "Inter Milan", "Internazionale": "Inter Milan", "Milan": "AC Milan",
    "B. Dortmund": "Borussia Dortmund", "Dortmund": "Borussia Dortmund",
    "Bayern": "Bayern Munich", "Leverkusen": "Bayer 04 Leverkusen", "B. Leverkusen": "Bayer 04 Leverkusen",
    "R. Madrid": "Real Madrid", "Barça": "FC Barcelona", "Barcelona": "FC Barcelona",
    "Spurs": "Tottenham Hotspur", "Tottenham": "Tottenham Hotspur",
    "Sporting": "Sporting CP", "Benfica": "SL Benfica", "Porto": "FC Porto",
    "Ajax": "Ajax Amsterdam", "PSV": "PSV Eindhoven", "Feyenoord": "Feyenoord Rotterdam",
    "Marseille": "Olympique Marseille", "Lyon": "Olympique Lyon", "Monaco": "AS Monaco",
    "Lille": "LOSC Lille", "Napoli": "SSC Napoli", "Roma": "AS Roma", "Lazio": "SS Lazio",
    "Juventus": "Juventus FC", "Atalanta": "Atalanta BC", "Fiorentina": "ACF Fiorentina",
    "Chelsea": "Chelsea FC", "Liverpool": "Liverpool FC", "Arsenal": "Arsenal FC",
    "West Ham": "West Ham United", "Aston Villa": "Aston Villa",
    "Betis": "Real Betis Balompié", "Real Betis": "Real Betis Balompié",
    "Real Sociedad": "Real Sociedad",
    "Neth.": "Netherlands", "Holland": "Netherlands", "Ger.": "Germany", "Eng.": "England",
    "Fra.": "France", "Arg.": "Argentina", "Bra.": "Brazil", "Por.": "Portugal",
    "Spa.": "Spain", "Ita.": "Italy", "Austria": "Austria", "Poland": "Poland"
}

SEASONS = ["2023", "2024", "2025"] 

# ==========================================
# ⚙️ FUNCIONES DE UTILIDAD
# ==========================================

def normalizar_nombre(nombre):
    if not nombre: return ""
    n = re.sub(r'\s*\(.*?\)', '', nombre).strip()
    return ALIAS_MAP.get(n, n)

def es_rival_top(rival_partido, lista_top):
    if not lista_top or not rival_partido: return False
    nombre_clean = normalizar_nombre(rival_partido).lower()
    for top_team in lista_top:
        target = top_team.lower()
        if nombre_clean == target: return True
        if len(target) > 6 and target in nombre_clean: return True
    return False

class StatsContainer:
    def __init__(self):
        self.minutos = 0; self.goles = 0; self.asistencias = 0; self.penaltis = 0; self.partidos_reales = 0
    def agregar_detalle(self, m, g, a):
        self.minutos += m; self.goles += g; self.asistencias += a; self.partidos_reales += 1
    def set_penaltis(self, p): self.penaltis = p 
    def sumar_otro_contenedor(self, otro):
        self.minutos += otro.minutos; self.goles += otro.goles
        self.asistencias += otro.asistencias; self.penaltis += otro.penaltis; self.partidos_reales += otro.partidos_reales

def limpiar_numero(t): return int(t.strip().replace("-", "0")) if t and t.strip() not in ["", "-"] else 0
def limpiar_minutos(t): return int(t.replace("'", "").replace(".", "").strip()) if t else 0
def limpiar_penaltis_resumen(t):
    if not t or t.strip() in ["-", ""]: return 0
    try: return int(t.strip().split("/")[0].strip())
    except: return 0

def calcular_metricas_finales(stats: StatsContainer):
    if stats.partidos_reales == 0 or stats.minutos == 0: return 0,0,0,0,0,0,0
    pc_rounded = int(min(stats.partidos_reales, stats.minutos / 80.0) + 0.5)
    if pc_rounded == 0 and stats.minutos > 0: pc_rounded = 1
    max_pen = math.floor(stats.minutos / 1000) * 2
    pen_validos = min(stats.penaltis, max_pen)
    goles_ajustados = (stats.goles - stats.penaltis) + pen_validos
    avg_g = goles_ajustados / pc_rounded if pc_rounded > 0 else 0
    avg_a = stats.asistencias / pc_rounded if pc_rounded > 0 else 0
    return pc_rounded, stats.goles, goles_ajustados, stats.asistencias, avg_g, avg_a, avg_g + (avg_a / 2.0)

def clasificar_competicion(texto_o_url):
    t = texto_o_url.lower()
    if any(kw in t for kw in ["uefa-champions-league", "champions league", "uefa-europa-league", "europa league", "uefa-conference-league", "conference league", "uefa-super-cup", "super cup", "fifa club world cup", "fifa-club-world-cup", "club world cup"]): return "EUROPA"
    if any(kw in t for kw in ["international-friendlies", "international friendlies", "uefa-nations-league", "nations league", "world-cup", "world cup", "european-qualifiers", "european qualifiers", "uefa-euro", "uefa euro", "copa-america", "copa américa"]): return "SELECCION"
    if any(kw in t for kw in ["laliga", "ligue-1", "ligue 1", "premier-league", "premier league", "bundesliga", "serie-a", "serie a"]): return "LIGA"
    return "IGNORADO"

def leer_penaltis_resumen(page):
    penaltis = {"LIGA": 0, "EUROPA": 0, "SELECCION": 0}
    try:
        tabla = page.locator("table.items").first
        if not tabla.is_visible(): return penaltis
        for fila in tabla.locator("tbody tr").all():
            tds = fila.locator("td").all()
            if len(tds) < 12: continue
            try:
                link = tds[1].locator("a").first
                txt = (link.get_attribute("href") + " " + link.inner_text()) if link.count() > 0 else tds[1].inner_text()
                tipo = clasificar_competicion(txt)
                if tipo != "IGNORADO": penaltis[tipo] += limpiar_penaltis_resumen(tds[11].inner_text())
            except: continue
    except: pass
    return penaltis

def clasificar_por_headline(fila):
    try:
        box = fila.evaluate_handle("row => row.closest('.box')")
        if not box: return "IGNORADO"
        headline_a = box.as_element().query_selector(".content-box-headline a")
        if not headline_a: return "IGNORADO"
        href = headline_a.get_attribute("href").lower()
        return clasificar_competicion(href)
    except: return "IGNORADO"

def obtener_nombre_rival_css(fila):
    try:
        rival_el = fila.locator(".no-border-links.hauptlink").first
        if rival_el.count() > 0:
            return rival_el.inner_text().strip()
        return None
    except: return None

def destruir_popup_cookies(page):
    try: page.evaluate("document.querySelectorAll('[id^=sp_message], iframe[title*=Consent], div.fc-consent-root').forEach(e => e.remove())"); time.sleep(0.5)
    except: pass

def navegar_seguro(page, url, intentos=3):
    for i in range(intentos):
        try:
            page.goto(url, timeout=45000, wait_until="load")
            return True
        except: time.sleep(3)
    return False

# ==========================================
# 🕵️ LOGICA SCRAPING
# ==========================================

def analizar_jugador(page, jugador):
    cubos = {"LIGA": StatsContainer(), "EUROPA": StatsContainer(), "SELECCION": StatsContainer()}
    c_ext = {"LIGA": StatsContainer(), "EUROPA": StatsContainer(), "SELECCION": StatsContainer()}
    c_top = {"LIGA": StatsContainer(), "EUROPA": StatsContainer(), "SELECCION": StatsContainer()}
    audit_log = []

    top50c = RANKINGS_DB["top_50_clubes"]
    top25c = RANKINGS_DB["top_25_clubes"]
    top50s = RANKINGS_DB["top_50_selecciones"]
    top32s = top50s[:32]; top16s = top50s[:16]

    # Búsqueda
    if not navegar_seguro(page, f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={jugador.replace(' ', '+')}"): return None
    destruir_popup_cookies(page)
    try:
        perfil = page.locator("table.items td.hauptlink a").first
        if perfil.count() == 0: return None
        url_base = perfil.get_attribute("href").replace("profil", "leistungsdaten")
    except: return None

    # Loop Temporadas
    for temp in SEASONS:
        if not navegar_seguro(page, f"https://www.transfermarkt.com{url_base}/plus/1?saison={temp}"): continue
        destruir_popup_cookies(page)
        try:
            p_temp = leer_penaltis_resumen(page)
            for b, v in p_temp.items(): cubos[b].set_penaltis(cubos[b].penaltis + v)
            
            divs = page.locator("div.responsive-table").all()
            for div in divs:
                tabla = div.locator("table").first
                if "appearances" in tabla.locator("thead").inner_text().lower(): continue
                for fila in tabla.locator("tbody tr").all():
                    if "bg_blau" in (fila.get_attribute("class") or ""): continue
                    tds = fila.locator("td").all()
                    if len(tds) < 16: continue
                    
                    tipo = clasificar_por_headline(fila)
                    if tipo == "IGNORADO": continue
                    
                    m = limpiar_minutos(tds[-1].inner_text())
                    if m > 0:
                        g = limpiar_numero(tds[8].inner_text())
                        a = limpiar_numero(tds[9].inner_text())
                        
                        cubos[tipo].agregar_detalle(m, g, a)
                        
                        rival = obtener_nombre_rival_css(fila)
                        if rival:
                            r_norm = normalizar_nombre(rival)
                            is_ext = False; is_top = False
                            
                            if (tipo in ["LIGA", "EUROPA"] and es_rival_top(r_norm, top50c)) or \
                               (tipo == "SELECCION" and es_rival_top(r_norm, top32s)):
                                c_ext[tipo].agregar_detalle(m, g, a)
                                is_ext = True
                            
                            if (tipo in ["LIGA", "EUROPA"] and es_rival_top(r_norm, top25c)) or \
                               (tipo == "SELECCION" and es_rival_top(r_norm, top16s)):
                                c_top[tipo].agregar_detalle(m, g, a)
                                is_top = True
                            
                            audit_log.append({
                                "JUGADOR": jugador,
                                "Temp": temp, "Comp": tipo, 
                                "Rival": rival, "Norm": r_norm, 
                                "Elite?": "YES" if is_ext else "NO", 
                                "Top?": "YES" if is_top else "NO",
                                "Min": m, "G": g, "A": a
                            })
        except: continue

    # Cálculos
    def proc(s, w):
        d = calcular_metricas_finales(s)
        return {"pc":d[0], "avg_g":d[4], "avg_a":d[5], "score":d[6], "w":w}

    pc_e_t,_,_,_,_,_,_ = calcular_metricas_finales(cubos["EUROPA"])
    pc_s_t,_,_,_,_,_,_ = calcular_metricas_finales(cubos["SELECCION"])
    
    stats_gen = StatsContainer(); stats_gen.sumar_otro_contenedor(cubos["LIGA"])
    w_e = 0.40; w_s = 0.25
    if pc_e_t < 12: stats_gen.sumar_otro_contenedor(cubos["EUROPA"]); cubos["EUROPA"]=StatsContainer(); w_e=0
    if pc_s_t < 10: stats_gen.sumar_otro_contenedor(cubos["SELECCION"]); cubos["SELECCION"]=StatsContainer(); w_s=0
    w_g = 1.0 - (w_e + w_s)
    
    d_gen = proc(stats_gen, w_g); d_eur = proc(cubos["EUROPA"], w_e); d_sel = proc(cubos["SELECCION"], w_s)
    score_f = (d_gen["score"]*w_g) + (d_eur["score"]*w_e) + (d_sel["score"]*w_s)
    
    avg_g_pond = (d_gen["avg_g"]*w_g) + (d_eur["avg_g"]*w_e) + (d_sel["avg_g"]*w_s)
    avg_a_pond = (d_gen["avg_a"]*w_g) + (d_eur["avg_a"]*w_e) + (d_sel["avg_a"]*w_s)

    def tot_e(cd):
        t = StatsContainer()
        for b in ["LIGA", "EUROPA", "SELECCION"]: t.sumar_otro_contenedor(cd[b])
        return proc(t, 1.0)
    
    d_ext_tot = tot_e(c_ext)
    d_top_tot = tot_e(c_top)

    return {
        "Nombre": jugador,
        "Score_Global": score_f,
        "Avg_G_Pond": avg_g_pond,
        "Avg_A_Pond": avg_a_pond,
        
        "EliteExt_Score": d_ext_tot["score"],
        "EliteExt_G": d_ext_tot["avg_g"],
        "EliteExt_A": d_ext_tot["avg_a"],
        
        "EliteTop_Score": d_top_tot["score"],
        "EliteTop_G": d_top_tot["avg_g"],
        "EliteTop_A": d_top_tot["avg_a"],
        
        "Audit_Log": audit_log,
        
        "Detalle_Global": {"LIGA": d_gen, "EUROPA": d_eur, "SELECCION": d_sel},
        "Detalle_Ext": {k: proc(v, 0) for k,v in c_ext.items()},
        "Detalle_Top": {k: proc(v, 0) for k,v in c_top.items()},
    }

# ==========================================
# 💾 GESTIÓN DE CSV
# ==========================================

def aplanar_resultados(resultados):
    flat_data = []
    for r in resultados:
        row = {
            "Nombre": r["Nombre"],
            "Score_Global": r["Score_Global"], "Avg_G_Pond": r["Avg_G_Pond"], "Avg_A_Pond": r["Avg_A_Pond"],
            "EliteExt_Score": r["EliteExt_Score"], "EliteExt_G": r["EliteExt_G"], "EliteExt_A": r["EliteExt_A"],
            "EliteTop_Score": r["EliteTop_Score"], "EliteTop_G": r["EliteTop_G"], "EliteTop_A": r["EliteTop_A"]
        }
        for cat_name, cat_dict in [("Global", r["Detalle_Global"]), ("Ext", r["Detalle_Ext"]), ("Top", r["Detalle_Top"])]:
            for comp, metrics in cat_dict.items():
                prefix = f"{cat_name}_{comp}"
                row[f"{prefix}_pc"] = metrics["pc"]
                row[f"{prefix}_g"] = metrics["avg_g"]
                row[f"{prefix}_a"] = metrics["avg_a"]
                row[f"{prefix}_score"] = metrics["score"]
                row[f"{prefix}_w"] = metrics.get("w", 0)
        flat_data.append(row)
    return pd.DataFrame(flat_data)

def reconstruir_estructura(df_flat):
    reconstructed = []
    for _, row in df_flat.iterrows():
        item = {
            "Nombre": row["Nombre"],
            "Score_Global": row["Score_Global"], "Avg_G_Pond": row["Avg_G_Pond"], "Avg_A_Pond": row["Avg_A_Pond"],
            "EliteExt_Score": row["EliteExt_Score"], "EliteExt_G": row["EliteExt_G"], "EliteExt_A": row["EliteExt_A"],
            "EliteTop_Score": row["EliteTop_Score"], "EliteTop_G": row["EliteTop_G"], "EliteTop_A": row["EliteTop_A"],
            "Audit_Log": []
        }
        for cat_name, target_key in [("Global", "Detalle_Global"), ("Ext", "Detalle_Ext"), ("Top", "Detalle_Top")]:
            item[target_key] = {}
            for comp in ["LIGA", "EUROPA", "SELECCION"]:
                prefix = f"{cat_name}_{comp}"
                if f"{prefix}_pc" in row:
                    item[target_key][comp] = {
                        "pc": row[f"{prefix}_pc"],
                        "avg_g": row[f"{prefix}_g"],
                        "avg_a": row[f"{prefix}_a"],
                        "score": row[f"{prefix}_score"],
                        "w": row.get(f"{prefix}_w", 0)
                    }
        reconstructed.append(item)
    return reconstructed

# ==========================================
# 🖥️ INTERFAZ GRÁFICA
# ==========================================
st.set_page_config(page_title="Scouting AI Pro", layout="wide", page_icon="⚡")
st.markdown("""
<style>
    .stApp { background: linear-gradient(to bottom right, #0F0C29, #302B63, #24243E); color: #E0E0E0; }
    div[data-testid="stExpander"] { background-color: rgba(20, 20, 35, 0.6); border: 1px solid #4b0082; }
    .stDataFrame { border: 1px solid #5a5a90; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Scouting AI Pro (Ranking Master)")

with st.sidebar:
    st.header("⚙️ Panel de Control")
    modo = st.radio("Modo:", ["📂 VISUALIZAR OFFLINE", "🕵️ SCRAPING EN VIVO"], index=1)
    
    uploaded_file = None
    lista_scraping = []
    
    if modo == "📂 VISUALIZAR OFFLINE":
        st.info("Carga tu CSV para ver el Ranking General y fichas detalladas.")
        uploaded_file = st.file_uploader("Sube resultados.csv", type=["csv"])
        
    elif modo == "🕵️ SCRAPING EN VIVO":
        st.info("⚠️ El Scraping puede ser lento en la nube gratuita.")
        submodo = st.radio("Fuente:", ["Un Jugador", "Lista CSV"])
        if submodo == "Un Jugador":
            n = st.text_input("Nombre:")
            if n: lista_scraping = [n]
        else:
            up_input = st.file_uploader("Sube input.csv", type=["csv"])
            if up_input: lista_scraping = pd.read_csv(up_input)["JUGADOR"].astype(str).tolist()
        
        btn_run = st.button("🚀 Iniciar Scraping", type="primary")

def crear_tabla_detalle(datos_dict, titulo, score_total, goles_total, asist_total):
    st.markdown(f"### {titulo}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Score Total", f"{score_total:.3f}")
    c2.metric("Goles/P", f"{goles_total:.2f}")
    c3.metric("Asist/P", f"{asist_total:.2f}")
    
    data = []
    for k, v in datos_dict.items():
        peso = v.get("w", 0)
        data.append({
            "Competición": k, 
            "Partidos": v["pc"], "Goles/P": v["avg_g"], "Asist/P": v["avg_a"], "Score": v["score"],
            "Peso": f"{peso*100:.0f}%" if peso > 0 else "-"
        })
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def render_item(data):
    with st.expander(f"⚽ {data['Nombre']} | Score: {data['Score_Global']:.3f}", expanded=False):
        t1, t2, t3, t4 = st.tabs(["Global", "Élite Extendida", "Élite Top", "🕵️ AUDITORÍA"])
        with t1:
            crear_tabla_detalle(data["Detalle_Global"], "Rendimiento Global Ponderado", 
                                data["Score_Global"], data["Avg_G_Pond"], data["Avg_A_Pond"])
        with t2:
            crear_tabla_detalle(data["Detalle_Ext"], "Élite Extendida (Top 50 / Top 32)", 
                                data["EliteExt_Score"], data["EliteExt_G"], data["EliteExt_A"])
        with t3:
            crear_tabla_detalle(data["Detalle_Top"], "Élite Top (Top 25 / Top 16)", 
                                data["EliteTop_Score"], data["EliteTop_G"], data["EliteTop_A"])
        with t4:
            if data["Audit_Log"]:
                st.dataframe(pd.DataFrame(data["Audit_Log"]), use_container_width=True)
            else:
                st.info("Log detallado no disponible en modo Offline.")

# --- CONTROLADOR ---
if modo == "📂 VISUALIZAR OFFLINE" and uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file)
        datos_reconstruidos = reconstruir_estructura(df_raw)
        st.success(f"Cargados {len(datos_reconstruidos)} jugadores.")
        
        st.markdown("## 🏆 Ranking General de Jugadores")
        st.markdown("Haz clic en los encabezados para ordenar.")
        
        df_ranking = df_raw[[
            'Nombre', 
            'Score_Global', 'Avg_G_Pond', 'Avg_A_Pond',
            'EliteExt_Score', 'EliteExt_G', 'EliteExt_A',
            'EliteTop_Score', 'EliteTop_G', 'EliteTop_A'
        ]].copy()
        
        df_ranking.columns = [
            "Jugador", 
            "Score Global", "Goles Global", "Asist Global",
            "Score Ext", "Goles Ext", "Asist Ext",
            "Score Top", "Goles Top", "Asist Top"
        ]
        
        st.dataframe(
            df_ranking, 
            use_container_width=True,
            column_config={
                "Score Global": st.column_config.NumberColumn(format="%.3f"),
                "Score Ext": st.column_config.NumberColumn(format="%.3f"),
                "Score Top": st.column_config.NumberColumn(format="%.3f"),
                "Goles Global": st.column_config.NumberColumn(format="%.2f"),
                "Asist Global": st.column_config.NumberColumn(format="%.2f"),
                "Goles Ext": st.column_config.NumberColumn(format="%.2f"),
                "Asist Ext": st.column_config.NumberColumn(format="%.2f"),
                "Goles Top": st.column_config.NumberColumn(format="%.2f"),
                "Asist Top": st.column_config.NumberColumn(format="%.2f"),
            }
        )
        
        st.divider()
        st.markdown("## 📋 Detalle Individual")
        for item in datos_reconstruidos:
            render_item(item)
            
    except Exception as e: st.error(f"Error leyendo CSV: {e}")

elif modo == "🕵️ SCRAPING EN VIVO" and btn_run and lista_scraping:
    status = st.status("🔍 Iniciando Scraping...", expanded=True)
    pbar = status.progress(0)
    resultados = []
    full_audit_log = []
    
    with sync_playwright() as p:
        # --- CRÍTICO: HEADLESS TRUE PARA LA NUBE ---
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Simulamos ser un navegador real para evitar bloqueo simple
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})

        for i, jug in enumerate(lista_scraping):
            status.write(f"Procesando: **{jug}**")
            try:
                data = analizar_jugador(page, jug)
                if data:
                    resultados.append(data)
                    full_audit_log.extend(data["Audit_Log"])
                    render_item(data)
                else:
                    status.warning(f"No encontrado: {jug}")
            except Exception as e: st.error(f"Error {jug}: {e}")
            pbar.progress((i+1)/len(lista_scraping))
        
        browser.close()
        status.update(label="Completado", state="complete")
        
    if resultados:
        df_resumen = aplanar_resultados(resultados)
        st.download_button("💾 Guardar Resultados (Para Dashboard)", 
                           df_resumen.to_csv(index=False).encode("utf-8"), "resultados_scouting.csv")
        
        if full_audit_log:
            df_audit = pd.DataFrame(full_audit_log)
            st.download_button("🐞 Guardar Auditoría Detallada", 
                               df_audit.to_csv(index=False).encode("utf-8"), "auditoria_partidos.csv")