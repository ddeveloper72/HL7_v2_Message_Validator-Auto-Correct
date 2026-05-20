# HL7 v2 Message Validator - Docker Image
# Python 3.12 with Flask, Azure SQL, and Azure AD support

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Azure SQL (FreeTDS + ODBC)
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    unixodbc-dev \
    freetds-dev \
    freetds-bin \
    tdsodbc \
    && rm -rf /var/lib/apt/lists/*

# Configure FreeTDS ODBC driver
RUN echo "[FreeTDS]\n\
Description = FreeTDS Driver for SQL Server\n\
Driver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so\n\
Setup = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so\n\
FileUsage = 1" > /etc/odbcinst.ini

# Configure FreeTDS protocol version
RUN echo "[global]\n\
tds version = 8.0\n\
client charset = UTF-8" > /etc/freetds/freetds.conf

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories for uploads and temp files
RUN mkdir -p uploads processed flask_session /tmp && \
    chmod 777 uploads processed flask_session /tmp

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)"

# Run with Gunicorn
CMD ["gunicorn", "dashboard_app:app", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--workers", "2", \
     "--worker-class", "sync", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
