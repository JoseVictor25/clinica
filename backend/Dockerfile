FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system django \
    && useradd --system --gid django --create-home django

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker/entrypoint.sh /usr/local/bin/clinica-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/clinica-entrypoint \
    && chmod +x /usr/local/bin/clinica-entrypoint \
    && chown -R django:django /app

ENTRYPOINT ["/usr/local/bin/clinica-entrypoint"]

FROM base AS development
USER django
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS production
USER django
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
