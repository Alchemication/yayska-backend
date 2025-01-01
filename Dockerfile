# Use the official Python 3.11 slim image as the base
FROM python:3.11-slim

# Install necessary system dependencies
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv by copying it from its official Docker image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables for uv
ENV UV_SYSTEM_PYTHON=1

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml and uv.lock files into the container
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
RUN uv sync --frozen

# Copy the application code into the container
COPY app/ ./app

# Expose the port your application runs on
EXPOSE 8000

# Set the entry point to run your application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
