FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and ZBar
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["fastapi", "run", "src/main.py", "--port", "8000"]
