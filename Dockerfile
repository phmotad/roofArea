# API Roof – FastAPI + U-Net (segmentação de telhados)
FROM python:3.12-slim

# Runtime libs: rasterio (libexpat), opencv/numpy (libgomp). Evita ImportError ao importar rasterio e cv2.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src src/
# Timeout longo para downloads grandes (PyTorch/CUDA wheels ~600MB+)
ENV PIP_DEFAULT_TIMEOUT=600
RUN pip install --no-cache-dir -e .

COPY alembic.ini .
COPY alembic alembic/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn roof_api.main:app --host 0.0.0.0 --port 8000"]
