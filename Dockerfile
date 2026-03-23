# Stage 1: Build the React frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + built frontend
FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./static

# Create data directory for transcript logs
RUN mkdir -p /app/data

ENV DATA_DIR=/app/data
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
