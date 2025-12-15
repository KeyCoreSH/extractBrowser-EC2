# Use Python 3.10 which has excellent compatibility with PyMuPDF wheels
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for PyMuPDF and other tools
# build-essential: for compiling C extensions
# curl: for healthchecks
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port
ENV PORT=2345
EXPOSE 2345

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:2345/health || exit 1

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:2345", "--workers", "2", "--timeout", "120", "app:app"]
