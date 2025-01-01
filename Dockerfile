FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the official installation method
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy dependency files
COPY pyproject.toml .

# Install dependencies using uv
RUN /root/.cargo/bin/uv pip install -r pyproject.toml

# Copy the rest of the application
COPY . .

# Run migrations and start the application
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT