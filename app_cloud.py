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
        if not headline_a: