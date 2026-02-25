FROM python:3.12-slim

# Force unbuffered stdout/stderr so crash logs are visible in Railway
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN rm -f .env

# Use python server.py (not uvicorn CLI) so PORT is read from env
# via os.getenv — no shell expansion issues, works in exec form
CMD ["python", "server.py"]
