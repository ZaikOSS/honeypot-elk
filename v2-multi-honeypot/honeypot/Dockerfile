# Use a lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for pyseccomp and basic tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libseccomp2 libseccomp-dev build-essential ca-certificates && \
    ldconfig && \
    rm -rf /var/lib/apt/lists/*

# Copy Python dependencies and install them
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all honeypot scripts and seccomp profile
COPY *.py ./
COPY honeypot-seccomp.json ./

# Create a non-root user and give ownership of /app
RUN useradd -m honeypot && \
    chown -R honeypot:honeypot /app

# Switch to the honeypot user
USER honeypot

# Expose ports (mapped in docker-compose)
EXPOSE 22
EXPOSE 80
EXPOSE 21

# Default command to run the main launcher
CMD ["python", "-u", "main.py"]
