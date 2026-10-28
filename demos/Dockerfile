FROM python:3.12-slim
RUN pip install --no-cache-dir 'mcp>=1.29,<2'
RUN useradd --uid 10001 --create-home lab
USER lab
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOOLLENS_LAB_ISOLATED=1 TOOLLENS_DOCUMENTS=/lab/documents
ENTRYPOINT ["python", "/app/server.py"]
