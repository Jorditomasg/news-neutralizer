# News Neutralizer

**News Neutralizer** es una plataforma diseñada para analizar artículos de noticias, detectar posibles sesgos, consolidar los hechos y generar resúmenes neutrales. El proyecto extrae información de diversas fuentes (DuckDuckGo Search, RSS, enlaces directos), la procesa y, mediante modelos de Inteligencia Artificial (locales o en la nube), presenta un artículo objetivizado y neutral.

---

## 🏗 Arquitectura y Tecnologías

El proyecto se divide en diferentes servicios mediante contenedores Docker, abarcando backend, frontend, base de datos y tareas asíncronas:

- **Frontend (`/frontend`)**: Next.js 15+ (React 19), Tailwind CSS v4, interactúa con el backend consumiendo su API REST.
- **Backend API (`/backend`)**: FastAPI interactuando de forma asíncrona.
- **Base de Datos (`db`)**: PostgreSQL con extensión `pgvector` para el almacenamiento vectorial y búsqueda de similitud entre artículos.
- **Controlador de Tareas y Caché (`redis` & `worker`)**: Cola de tareas asíncronas y programación estructurada de _scrapers_ usando Celery y Redis.
- **Inteligencia Artificial Local (`ollama`)**: Contenedor con Ollama integrado para la ejecución de LLMs en local de bajo coste, con opción de aceleración por GPU.

---

## 🚀 Requisitos Previos

- **Docker** y **Docker Compose** instalados en tu sistema.
- (Opcional, pero recomendado) Tarjeta de video con soporte NVIDIA si deseas utilizar Ollama con aceleración por GPU. En ese caso, debes asegurarte de tener el NVIDIA Container Toolkit configurado en Docker y descomentar/configurar la sección de despliegue (`deploy`) bajo el servicio OLLAMA en él `docker-compose.yml`.

---

## ⚙️ Instalación y Configuración Inicial

1. **Clona este repositorio** y navega hasta el directorio raíz:
   ```bash
   git clone <url-del-repositorio>
   cd news-neutralizer
   ```

2. **Configura el archivo de entorno (`.env`)**:
   En la raíz del proyecto, haz una copia de `.env.example` y llámala `.env`. Ajusta las variables si es necesario:
   ```bash
   cp .env.example .env
   ```
   *Nota: las contraseñas, URLs y otros credenciales deben ajustarse antes de usarse en un entorno de producción, como generar tu propia variable en `ENCRYPTION_KEY`.*

3. **Inicia los servicios**:
   Levanta la arquitectura completa utilizando `docker-compose`. Este comando construirá las imágenes del frontend, backend, el worker y descargará las necesarias de bases de datos/LLM.
   ```bash
   docker-compose up -d --build
   ```

   Una vez iniciados todos los contenedores (`frontend`, `api`, `worker`, `db`, `redis`, `ollama`), el sistema estará funcionando y accesible.

---

## 🌐 Servicios y Puertos Accesibles

Cuando el clúster local de Docker está corriendo, encontrarás los servicios disponibles en la máquina huésped:

- **Frontend Web**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Documentación API (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL**: Puerto `5432`
- **Redis**: Puerto `6379`
- **Ollama**: Puerto `11434`

---

## 🔍 Funciones Principales

- **Dashboard Integrado**: Puedes ver de un vistazo artículos procesados, pendientes, neutralizados, y hacer búsquedas de sesgo mediante la UI del Frontend.
- **Scraping Estructurado**: Extrae, limpia y normaliza información. Incluye tratamiento especial por origen y prevención del anti-scraping.
- **Detección de Sesgo**: Consolidación de hechos y mitigación de tendencias, evaluando y generando versiones sin sesgos orientados.
- **Seguridad**: Configuración encriptada en la base de datos de las claves (OpenAI, Anthropic, Gemini, o locales como Ollama).

---

## 👨‍💻 Comandos Útiles

- **Detener la aplicación y los servicios**:
  ```bash
  docker-compose down
  ```

- **Detener y limpiar los volúmenes** (Atención: esto borrará los datos de Postgres y modelos descargados de Ollama):
  ```bash
  docker-compose down -v
  ```

- **Ver logs de un servicio (p.ej. API)**:
  ```bash
  docker-compose logs -f api
  ```
