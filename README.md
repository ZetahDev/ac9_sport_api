# AC9 Sport API

API mínima en FastAPI para AC9 Sport (demo).

Características principales

- Endpoints para Categories, Subcategories y Products.
- ODM: Beanie (Motor + MongoDB Atlas).
- Autenticación administrativa simple mediante header `X-API-KEY`.
- Soporta subida de imágenes vía Base64 y `multipart/form-data` (guardado local como simulación S3).

Estado actual

- Proyecto creado en `ac9_sport_api/`.
- `app/main.py` inicializa Motor + Beanie usando la variable `MONGO_DB` como nombre de base de datos.
- Ejecutar el servidor desde la raíz del monorepo para que el paquete se importe correctamente.

Requisitos

- Python 3.11+ (o 3.10+).
- Acceso a MongoDB (Atlas o servidor propio).

Variables de entorno (archivo `ac9_sport_api/.env`)

Crea `ac9_sport_api/.env` con al menos:

```
API_KEY=tu_api_key_de_admin
MONGO_URI="mongodb+srv://usuario:password@cluster.mongodb.net/?retryWrites=true&w=majority"
MONGO_DB=ac9_sport
```

Notas:

- No dejes `<>` alrededor de la contraseña.
- `MONGO_DB` se usa para seleccionar la base de datos en la que se inicializan los modelos Beanie.

Instalación

Desde la raíz del repositorio (ej. `D:\Proyectos\Z\ac_store`):

```powershell
python -m pip install -r ac9_sport_api/requirements.txt
```

Ejecución en desarrollo

Ejecuta el servidor (desde la raíz del repo) con el path del paquete:

```powershell
uvicorn ac9_sport_api.app.main:app --reload --host 127.0.0.1 --port 8001
```

Endpoints útiles

- `GET /health` — estado de la API.
- `GET /categories` — lista mínima de categorías.
- `POST /categories` — crear categoría (requiere header `X-API-KEY`).
- `GET /products` — listar productos.
- `POST /products` — crear producto (acepta `multipart/form-data` y campos `images_base64`).

Autenticación administrativa

Enviar header `X-API-KEY` con el valor configurado en `.env` para endpoints que lo requieran.

Subida de imágenes

- Implementación actual: guardado en disco local dentro de `storage/` o similar (ver `app/core/s3.py`).
- Opcional: sustituir por un adaptador S3/Cloudinary en `app/core/s3.py` para producción.

Pruebas rápidas (smoke checks)

Desde otra terminal, cuando el servidor esté levantado:

```powershell
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/health').read().decode())"
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/categories').read().decode())"
```

Ejemplo `curl` para crear categoría (reemplaza `tu_api_key_de_admin`):

```bash
curl -X POST "http://127.0.0.1:8001/categories" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: tu_api_key_de_admin" \
  -d '{"name": "Ropa", "description": "Categoría ropa", "macroCategoryId": null}'
```

Despliegue / hosting

- Recomendado: Render, Railway o cualquier proveedor que soporte containers/servicios (Cloud Run, Fly.io).
- Recuerda configurar las variables de entorno en el panel del proveedor.

Notas para desarrolladores

- Si actualizas modelos Beanie, añade los documentos a `init_beanie(document_models=[...])` en `app/main.py`.
- Mantén las credenciales fuera del repositorio y en `.env` o el secreto del proveedor.

Contribuciones y siguientes pasos sugeridos

- Añadir tests (pytest) para endpoints principales.
- Añadir validación y esquemas Pydantic más estrictos si hace falta.
- Reemplazar almacenamiento local de imágenes por S3/Cloudinary en producción.

---

Archivo actualizado para reflejar la arquitectura actual (Beanie + MongoDB).
