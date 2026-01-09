FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for psutil
RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/workspace /app/memories

# The AI's sandbox
WORKDIR /app/workspace

# Force unbuffered output for Docker logs
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "/app/brain.py"]
