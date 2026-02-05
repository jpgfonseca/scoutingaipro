# Technical Specification: Scouting AI Pro (Deep Dive)

## 1. Introducción y Objetivo
El objetivo del sistema es generar un **Índice de Rendimiento (Score)** que normalice la producción ofensiva de un jugador, eliminando el ruido estadístico de los "minutos de la basura" y penalizando la dependencia excesiva de los penaltis.

El sistema prioriza la **calidad sobre la cantidad**, diferenciando si los goles fueron anotados contra rivales de élite (Real Madrid, City, Brasil, etc.) o contra rivales menores.

---

## 2. Lógica de Obtención de Datos (Scraping)

### 2.1 Motor de Extracción
* **Herramienta:** Microsoft Playwright (Sync API).
* **Target:** `transfermarkt.com`.
* **Estrategia:**
    1.  Búsqueda del jugador vía query string.
    2.  Extracción del `ID` único del jugador.
    3.  Iteración sobre las temporadas: `2023`, `2024`, `2025`.
    4.  Filtrado de filas: Se ignoran amistosos de clubes y ligas juveniles.

### 2.2 Clasificación de Competiciones
Cada partido extraído se clasifica en una de tres "Cubetas" (Buckets) mediante análisis de RegEx en la URL del torneo:

| Cubeta (Bucket) | Competiciones Incluidas (Keywords) |
| :--- | :--- |
| **EUROPA** | Champions League, Europa League, Conference League, Super Cup, Mundial de Clubes. |
| **SELECCION** | Mundial, Eurocopa, Copa América, Nations League, Clasificatorias, Amistosos Internacionales. |
| **LIGA/GEN** | Premier League, LaLiga, Bundesliga, Serie A, Ligue 1 y Copas Nacionales. |

---

## 3. Algoritmo de Puntuación (The Core Math)

El cálculo del `Score` no es una simple suma. Se aplican cuatro fases de transformación matemática.

### Fase 1: Normalización de Tiempo de Juego ($PC$)
No se usan los "Partidos Jugados" oficiales, se calcula el concepto de **Partidos Completos ($PC$)**.

$$PC = \text{round}\left( \min \left( \text{Apps}, \frac{\text{Minutos Totales}}{80} \right) \right)$$

* **Nota:** Se divide por 80 (y no 90) para ser ligeramente flexible con las sustituciones.
* **Límite:** El $PC$ nunca puede ser mayor que la cantidad de apariciones reales (`Apps`).

### Fase 2: Ajuste de Penaltis (Penalty Dampening)
Para evitar que lanzadores de penaltis inflen su score sin aportar en juego abierto, se aplica un "Cap" (Límite) de penaltis válidos.

1.  **Límite Permitido ($MaxPen$):** Se permiten 2 penaltis por cada 1000 minutos jugados.
    $$MaxPen = \lfloor \frac{\text{Minutos}}{1000} \rfloor \times 2$$
2.  **Penaltis Válidos ($PenVal$):**
    $$PenVal = \min(\text{Penaltis Anotados}, MaxPen)$$
3.  **Goles Ajustados ($G_{adj}$):**
    $$G_{adj} = (Goles_{Totales} - Penaltis_{Totales}) + PenVal$$

*Efecto: Si un jugador marca 10 penaltis en 1000 minutos, solo se le cuentan 2. Los otros 8 se descartan.*

### Fase 3: Score de Producción Base
Se calcula el promedio de contribución por "Partido Completo" ($PC$).

1.  **Promedio Goles:** $AvgG = G_{adj} / PC$
2.  **Promedio Asistencias:** $AvgA = Asistencias / PC$
3.  **Score del Bucket:**
    $$Score_{Bucket} = AvgG + \frac{AvgA}{2}$$

*Nota: Una asistencia vale exactamente la mitad que un gol.*

### Fase 4: Ponderación Global (Weighted Aggregation)
El Score Final es una suma ponderada de las tres cubetas.

**Pesos Iniciales:**
* $W_{Europa} = 40\%$ ($0.40$)
* $W_{Seleccion} = 25\%$ ($0.25$)
* $W_{Liga} = 35\%$ ($0.35$)

**Lógica de Fusión Dinámica (Fallback):**
Si un jugador tiene una muestra estadística irrelevante en una cubeta ($PC < 12$), esa cubeta se "vacía" y sus números (minutos, goles) se suman a la cubeta de LIGA para no distorsionar el promedio.

* *Ejemplo:* Si `PC_Europa < 12`:
    1.  Los goles/minutos de Europa se suman a Liga.
    2.  $W_{Europa}$ pasa a $0$.
    3.  $W_{Liga}$ absorbe el peso restante.

**Fórmula Final:**
$$Score_{Global} = (Score_{Liga} \cdot W_{Liga}) + (Score_{Eur} \cdot W_{Eur}) + (Score_{Sel} \cdot W_{Sel})$$

---

## 4. Métricas de Élite (Contexto del Rival)

Paralelamente al Score Global, se calculan dos métricas independientes que **filtran** los partidos. Solo se procesan goles/asistencias si el rival está en las bases de datos estáticas (`RANKINGS_DB`).

### 4.1 Definición de Conjuntos
* **Top 50 Clubes:** Lista fija (Real Madrid, Bayern, etc.) basada en coeficiente UEFA/ELO reciente.
* **Top 25 Clubes:** Subconjunto de la élite absoluta (aprox. Cuartos de final de Champions).
* **Top Selecciones:** Top 32 y Top 16 ranking FIFA.

### 4.2 Métricas Resultantes
* **Elite Extended Score:** Rendimiento calculado usando SOLO partidos contra Top 50 Clubes o Top 32 Selecciones.
* **Elite Top Score:** Rendimiento calculado usando SOLO partidos contra Top 25 Clubes o Top 16 Selecciones.

*Si el `Elite Top Score` es mayor que el `Score Global`, indica un jugador "Big Game Player" (rinde más contra mejores rivales).*

---

## 5. Especificaciones de Infraestructura

### 5.1 Entorno de Ejecución (Environment)
El código detecta automáticamente el sistema operativo (`sys.platform`):
* **Windows (Local):** Ejecuta `headless=False` (Navegador visible) y usa `asyncio.WindowsProactorEventLoopPolicy`.
* **Linux (Cloud):** Ejecuta `headless=True`, instala dependencias apt-get (`packages.txt`) e instala Chromium automáticamente al inicio.

### 5.2 Estilos (Theming Specification)
Para garantizar consistencia visual en móviles y escritorio:
* **Configuración (`.streamlit/config.toml`):**
    * `base="dark"` (Forzado mandatorio).
    * `primaryColor="#4b0082"` (Indigo).
    * `backgroundColor="#0F0C29"` (Deep Night).
* **CSS Inyectado:** Se utiliza para degradados complejos (`linear-gradient`) que `config.toml` no soporta nativamente.

---

## 6. Estructura de Datos de Salida (CSV)

El archivo plano resultante aplanará la estructura jerárquica:

| Campo | Descripción |
| :--- | :--- |
| `Score_Global` | La métrica principal ponderada. |
| `Avg_G_Pond` | Promedio de goles ajustados ponderado. |
| `Global_LIGA_pc` | Partidos completos jugados en Liga. |
| `Global_EUROPA_score` | Score específico en competiciones europeas. |
| `EliteTop_Score` | Score filtrado solo contra los mejores 25 equipos del mundo. |
| `EliteTop_G` | Promedio de goles contra Top 25. |
