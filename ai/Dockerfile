FROM python:3.11-slim

WORKDIR /app

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
