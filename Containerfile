# Use a slim Python base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies if needed (sqlite3 is usually built-in to python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server script
COPY mcp_server.py .

# The directory where the user's project will be mounted
# We'll expect the SQLite DB to live here to persist across container runs
RUN mkdir /workspace
WORKDIR /workspace

# Set the entrypoint to the Python script
# We point Python to the server script in /app
ENTRYPOINT ["python", "/app/mcp_server.py"]
