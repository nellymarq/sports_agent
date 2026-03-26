FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for playwright and bs4
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from root requirements
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers (required by tools/browser_fetch.py)
RUN playwright install --with-deps chromium || true

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
