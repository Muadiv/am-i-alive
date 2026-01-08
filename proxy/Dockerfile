FROM python:3.11-slim

WORKDIR /app

# Install mitmproxy
RUN pip install --no-cache-dir mitmproxy==10.2.2

# Copy scripts
COPY . .

# Create directories
RUN mkdir -p /app/vault /app/logs

EXPOSE 8888

CMD ["mitmdump", "-s", "/app/intercept.py", "--listen-host", "0.0.0.0", "--listen-port", "8888", "--set", "block_global=false"]
