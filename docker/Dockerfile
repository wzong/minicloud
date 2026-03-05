# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + frontend static files
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireguard-tools \
    openssh-client \
    iproute2 \
    iptables \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install k3sup
RUN curl -sLS https://get.k3sup.dev | sh

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy frontend build output from Stage 1
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
