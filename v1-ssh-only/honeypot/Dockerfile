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

# Copy honeypot scripts and seccomp profile
COPY honeypot.py honeypot-seccomp.json ./

# Create a non-root user and give ownership of /app
RUN useradd -m honeypot && \
    chown -R honeypot:honeypot /app

# Switch to the honeypot user
USER honeypot

# Expose SSH port (mapped in docker-compose)
EXPOSE 22

# Default command to run honeypot
CMD ["python", "-u", "honeypot.py"]
