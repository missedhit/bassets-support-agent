FROM python:3.12-slim

WORKDIR /app

# Install system libraries needed by compiled Python packages
# (PyMuPDF, tokenizers, numpy, Pillow, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libmupdf-dev \
        libfreetype6 \
        libjpeg62-turbo \
        libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Don't copy .env into the image — secrets come from environment variables
RUN rm -f .env

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
