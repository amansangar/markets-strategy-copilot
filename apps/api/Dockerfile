FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace/apps/api

COPY apps/api/pyproject.toml .
COPY apps/api/app ./app
COPY data /workspace/data

RUN python -m pip install --upgrade pip && \
    python -m pip install -e .

ENV PROJECT_ROOT=/workspace \
    DATA_DIR=/workspace/data \
    ARTEFACTS_DIR=/workspace/artefacts

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
