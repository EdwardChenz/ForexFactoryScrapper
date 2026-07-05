FROM python:3.10-slim
LABEL authors="Ata Can"

WORKDIR /app

# Install system dependencies (if any)
RUN apt-get update \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better cache utilization
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.tencent.com/pypi/simple/ -r requirements.txt

# Copy the entire project
COPY main.py .
COPY src/ ./src/

# CloudBase Run will inject PORT env var, default to 80
ENV PORT=80

EXPOSE 80

CMD ["python", "main.py"]