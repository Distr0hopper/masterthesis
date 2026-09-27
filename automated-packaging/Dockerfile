# Packaging service image - NOT the R wrapper image (that's Dockerfile.sdk / build-sdk.sh)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY moveapps_cwl_packager ./moveapps_cwl_packager
RUN pip install --no-cache-dir ".[service]"

RUN useradd --create-home --uid 1000 packager
USER packager

EXPOSE 8000
CMD ["uvicorn", "moveapps_cwl_packager.service:app", "--host", "0.0.0.0", "--port", "8000"]
