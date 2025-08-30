FROM python:3.11-slim

WORKDIR /app

# Copiamos sólo lo que necesitamos desde el repo al contenedor
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
  pip install --no-cache-dir -r /app/requirements.txt

# Copiamos la aplicación (copia el contenido del repositorio al contenedor)
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Healthcheck opcional
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Arranque con el path de paquete correcto
# The application package is `app`, so use `app.main:app` as the uvicorn target.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]