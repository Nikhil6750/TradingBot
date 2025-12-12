# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# libpq-dev and gcc are often needed for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (from project root context)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (from project root context -> /app)
COPY backend/ .

# Expose port (FastAPI default)
EXPOSE 8000

# Command to run the application
# Assumes server.py is the entry point and uses uvicorn
CMD ["python", "server.py"]