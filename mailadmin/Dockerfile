FROM python:3.12-slim
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart
WORKDIR /app
COPY app.py .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips","*"]
