# Propuesta de Arquitectura: Next-Gen Global News Neutralizer

Para construir un sistema de obtención y análisis de noticias que sea verdaderamente global, escalable y resistente a las políticas anti-scraping (como los muros de cookies y protecciones de Cloudflare), debemos abandonar la dependencia exclusiva de Google News RSS y diseñar un pipeline de datos robusto y multicapa.

---

## 1. Arquitectura de Obtención (Fuentes de Datos)

En lugar de depender de un solo punto de fallo (Google News), crearemos un **Motor de Búsqueda Federado** (Federated Search Engine) que consulte múltiples proveedores simultáneamente y fusione los resultados.

### A. APIs de Agregación de Noticias (La Vía Rápida y Limpia)
El uso de APIs especializadas nos da URLs finales limpias, texto pre-extraído en muchos casos, y metadatos estructurados, eliminando el 80% de los problemas de scraping.
*   **NewsAPI / GNews API / ContextualWeb**: Alternativas económicas y estables a Google News.
*   **EventRegistry / NewsCatcher**: APIs de nivel empresarial (ideales si el proyecto requiere escalabilidad masiva) que ofrecen búsqueda semántica y clustering nativo.
*   **DuckDuckGo News / Bing News Search API**: Proporcionan resultados muy amplios sin los agresivos muros de consentimiento de Google.

### B. Crawling Directo de Sitemaps (Para Noticias de Última Hora)
Para no depender de listas blancas (whitelists), pero asegurando calidad:
*   **Feed Discovery**: Al hacer una búsqueda, si encontramos un medio nuevo válido, descubrimos automáticamente su `/news-sitemap.xml` o `/rss` y lo cacheamos en una base de datos dinámica.
*   Esto nos permite construir nuestro propio índice de noticias hiper-recientes de cualquier dominio de forma automatizada.

---

## 2. Resolución de Redirecciones y Evasión Anti-Bot (Scraping)

Cuando tenemos la URL (ya sea de API o RSS), necesitamos el texto. Aquí aplicaremos un patrón robusto:

### A. URL Resolver Registry (Estrategia)
Una cadena de responsabilidad que procesa la URL antes de tocarla:
1.  **Unshorteners**: Resuelven `bit.ly`, `t.co`, etc., usando llamadas HTTP `HEAD` rápidas.
2.  **Platform Decoders**: Decodificadores matemáticos o lógicos para URLs ofuscadas (como el que intentamos con Google News).
3.  **Clean URL**: Se eliminan parámetros de tracking (`?utm_xyz`, `?oc=5`) para normalizar la URL antes de la caché o el scraping.

### B. The Scraping Arsenal (Estrategia Progresiva)
En lugar de fallar a la primera, el extractor intenta escalar su agresividad:
1.  **Nivel 1: HTTPX + Heurística (Lo más rápido)**. Usamos cabeceras rotatorias y cookies de consentimiento IAB (`euconsent-v2`) para burlar el 70% de los medios normales. Si obtenemos una página de "Confiando en tu privacidad..." (Consent Screen), pasamos al nivel 2.
2.  **Nivel 2: APIs de Scraping / Proxy Rotativo**. Usar servicios como ScraperAPI o ZenRows (que gestionan Puppeteer/Playwright de fondo) para resolver CAPTCHAs, Cloudflare y renderizar JavaScript.
3.  **Nivel 3: Headless Browser local (Playwright)**. Lanzar una instancia de navegador real en el backend, inyectar cookies y esperar a que el selector `<article>` esté presente.

### C. Validación de Contenido Temprana
Antes de gastar tokens de IA, validamos el texto extraído:
*   Si la relación `etiquetas HTML / texto` es muy alta, es posible que estemos en una página intermedia.
*   **Filtro de Bloqueos Duros**: Si el texto contiene frases como "Enable JavaScript", "Please wait while your request is being verified", o "Acepto las cookies", abortamos y lo marcamos como scraping fallido.

---

## 3. Similitud Semántica y Clustering (Filtrado de Ruido)

No basta con que la búsqueda devuelva 10 noticias; necesitamos que hablen *exactamente* del mismo evento, no solo del mismo tema general.

### A. Vector Embeddings (La Clave)
1.  **Generación de Embeddings**: Cuando obtenemos la "Noticia Original" (ya sea pegando la URL o eligiéndola), calculamos su vector semántico usando un modelo rápido y barato como `text-embedding-3-small` de OpenAI o un modelo local `all-MiniLM-L6-v2` vía HuggingFace.
2.  **Búsqueda Amplia**: Lanzamos una búsqueda genérica a nuestras fuentes (APIs) y obtenemos docenas de candidatos (solo los títulos y el primer párrafo).
3.  **Embeddings de Candidatos**: Calculamos los vectores de estos candidatos (muy rápdio, solo es un texto corto).
4.  **Cálculo de Similitud Coseno**: Comparamos el vector de la Noticia Original con los candidatos. Solo mantenemos las noticias cuya similitud coseno supere un umbral estricto (ej. > 0.85).

### B. Ventana Temporal Estricta
La similitud semántica puede fallar si el evento se llama igual ("Atentado en Madrid"). Debemos cruzar la similitud vectorial con un límite de desviación de tiempo estricto (ej. +/- 36 horas respecto a la fecha de la noticia original).

---

## 4. Estrategia de Crecimiento sin Whitelists (Escalabilidad)

Para evitar mantener una lista manual de miles de medios (`elmundo.es`, `elpais.com`, etc.), implementaremos un sistema de **Scoring y Descubrimiento Dinámico de Dominios**:

1.  **Domain Tracker DB**: Una tabla que almacena cada dominio nuevo descubierto durante las búsquedas.
2.  **Background Trust Analysis**: Celery Worker que toma dominios nuevos y usa una IA rápida (ej. GPT-4o-mini o Claude 3.5 Haiku) para evaluarlo: *"¿Es esto un medio de comunicación legítimo, un blog personal, o un sitio de spam? ¿Cuál es su sesgo editorial histórico (si es conocido)?"*
3.  **Trust Score**: Al dominio se le asigna una puntuación de confianza (0-100). En el análisis final de Sesgo, los artículos de dominios con muy bajo Trust Score se ponderan menos o se marcan con una advertencia `[UNVERIFIED_SOURCE]`.

---

## 5. Pipeline de Extracción y Análisis en Producción (Step-by-Step)

Así funcionará el nuevo sistema de extremo a extremo cuando un usuario introduce una búsqueda o URL:

### Fase 1: Recolección y Resolución (Federada)
1.  **Federated Search**: Celery lanza tareas en paralelo a:
    *   **NewsAPI / GNews API** (Búsqueda global limpia).
    *   **Bing News Search API** (Excelente cobertura local e internacional).
    *   **Fallback RSS Engine** (Para URLs directas descubiertas).
2.  **URL Resolver Registry**: Todas las URLs crudas obtenidas (pueden ser 30-50) pasan por la tubería de resolución (`google_news_resolver -> bitly_resolver -> generic_unshortener`) para limpiar parámetros de tracking y exponer la URL canónica final.

### Fase 2: Extracción con Evasión Anti-Bot (Scraping)
1.  **Nivel 1 (HTTPX + Cookies)**: Descarga concurrente rápida (`asyncio.gather`) usando cabeceras de navegador modernas y cookies de consentimiento IAB (`euconsent-v2`, `CONSENT`).
2.  **Bloqueo Detectado**: Si el HTML retornado tiene menos de 500 palabras o contiene flags ("Please verify you are human", "Accept Cookies"), la URL se re-encola para el Nivel 2.
3.  **Nivel 2 (Proxy / Headless)**: Un worker de Celery dedicado usa Playwright/ZenRows para renderizar la página evadiendo Cloudflare/Datadome y extrae el `<article>` limpio.

### Fase 3: Filtrado Semántico (La verdadera Magia)
Tener 40 artículos no sirve si 20 hablan del mismo tema pero otro evento diferente (ej. "Elecciones 2019" vs "Elecciones 2023").
1.  **Vectorización Rápida**: Se usan modelos de embedding locales muy rápidos (ej. HuggingFace `all-MiniLM-L6-v2` vía `sentence-transformers` en un microservicio de Python o el servicio de OpenAI si hay presupuesto) para vectorizar los Títulos + Párrafo 1 de los 40 artículos descargados.
2.  **DBSCAN Clustering**: Se aplica el algoritmo de clustering [DBSCAN](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html) (Density-Based Spatial Clustering of Applications with Noise) sobre los vectores usando una distancia del coseno muy estricta (ej. > 0.88).
3.  **Selección del Cluster**:
    *   Si el usuario introdujo una **URL Original**, se selecciona el cluster que contiene a ese vector original.
    *   Si el usuario hizo una **Búsqueda Manual**, se selecciona el cluster más denso (el que tiene más artículos agrupados) asumiendo que es la noticia de última hora principal.
4.  **Poda Textual (Context Window Management)**: Del cluster seleccionado (ej. 8 artículos perfectamente alineados temáticamente), conservamos los 5 con mejor *Trust Score* y podamos su texto a los primeros 3000 tokens relevantes para no desbordar a la IA principal (Ollama).

### Fase 4: Análisis Neutral y Bias Scoring
Los artículos del cluster refinado se envían al LLM estructurado (prompting de roles) como se hace actualmente, garantizando que todos los artículos que recibe la IA hablan exactamente del mismo evento sin "alucinaciones" cruzadas.
