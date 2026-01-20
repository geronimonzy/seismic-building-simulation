FROM python:3.12-slim

# Install build dependencies for ObsPy and scientific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install package with dev and data extras (includes obspy)
RUN pip install --no-cache-dir -e ".[dev,data]"

# Copy remaining files
COPY . .

# Default command
CMD ["python", "-c", "import seismic_twin; print('seismic-twin ready')"]
