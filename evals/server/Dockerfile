FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY server/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt && \
    mkdir -p /data/cases /data/fixtures/manuscripts /data/rubrics && \
    useradd --uid 10001 --create-home evaluator
COPY translation_cases.py /app/evals/
COPY server/__init__.py server/__main__.py server/app.py server/models.py server/repository.py server/workspace.py /app/evals/server/
COPY server/static /app/evals/server/static
USER 10001:10001
EXPOSE 8765
CMD ["python", "-m", "evals.server", "--data-dir", "/data", "--host", "0.0.0.0", "--origin", "http://127.0.0.1:8765"]
