FROM python:3.11-slim

WORKDIR /app

# Copiamos sólo lo que necesitamos desde el repo al contenedor
COPY ac9_sport_api/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copiamos la aplicación
COPY ac9_sport_api /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Healthcheck opcional
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Arranque con el path de paquete correcto
CMD ["uvicorn", "ac9_sport_api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]