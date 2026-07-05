FROM python:3.10-slim
LABEL authors="Ata Can"

WORKDIR /app

# Install system dependencies (if any) - no extra packages needed for this project
RUN apt-get update \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better cache utilization
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY main.py .
COPY src/ ./src/

# Create a non-root user and switch to it for security
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# Zeabur will set PORT env var dynamically, default to 5000 as fallback
ENV PORT=5000

EXPOSE 5000

CMD ["python", "main.py"]