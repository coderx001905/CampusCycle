FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

RUN groupadd --system --gid 10001 campuscycle \
    && useradd --system --uid 10001 --gid campuscycle --home-dir /nonexistent campuscycle \
    && mkdir -p /data \
    && chown campuscycle:campuscycle /data

COPY --chown=campuscycle:campuscycle app ./app
COPY --chown=campuscycle:campuscycle alembic.ini ./alembic.ini
COPY --chown=campuscycle:campuscycle migrations ./migrations
COPY --chown=campuscycle:campuscycle entrypoint.sh ./entrypoint.sh
RUN sed -i 's/\r$//' ./entrypoint.sh && chmod +x ./entrypoint.sh

USER 10001:10001

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
