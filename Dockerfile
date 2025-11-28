# Use a lightweight Python image
FROM python:3.11-slim

# Install system dependencies for Tesseract OCR
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libtesseract-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy the entire repo into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for FastAPI
EXPOSE 8000

# Start FastAPI (note: app.py is in src/, so module is src.app)
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
