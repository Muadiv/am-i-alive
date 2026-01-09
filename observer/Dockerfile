FROM python:3.11-slim

WORKDIR /app

# Install curl and build deps for psutil
RUN apt-get update && apt-get install -y curl gcc python3-dev && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/data /app/vault /app/memories

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
