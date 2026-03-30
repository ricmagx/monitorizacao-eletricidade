FROM python:3.11-slim
WORKDIR /app
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt
# Instalar Chromium para playwright (necessario para tiagofelicia.pt — COMP-01)
RUN playwright install chromium --with-deps
COPY . .
RUN chmod +x entrypoint.sh
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["./entrypoint.sh"]
