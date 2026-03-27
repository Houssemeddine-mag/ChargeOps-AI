# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if required for any Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the backend requirements file and install dependencies
# We use the CPU version of PyTorch to keep the Docker image small and compatible across machines
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt numpy
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy the entire project into the container
COPY . /app

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# We need a startup script to run both the FastAPI server and the Edge Node simulation simultaneously in the container
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Define the command to run the application
CMD ["/app/docker-entrypoint.sh"]
